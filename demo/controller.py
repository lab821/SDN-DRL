# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet import udp
import random
import pdb
import time
import threading

from auto_gym import AutoEnv

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        
        # format: {(srcip,dstip,srcport,dstport,proto):[active,priority,fct,flow size]}
        self.flow_set = {}
        self.flow_old = {}
        # format: {(srcip, dstip, srcport, dstport, proto) : n}
        # n added by 1 when packet not coming,
        # if n > N, then flow finished.
        self.timeout = {}
        self.TIMEOUT_COUNT = 10
        conf = {"flow": self.flow_set,
                "old_flow": self.flow_old,
                "index_len": 5,
                "val_len": 4
                }
        # self.env = AutoEnv(conf)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        self.hard_coding_routing(ev.msg.datapath)
        stat_t = threading.Thread(target=self.period_flow_stats_send, args=(ev,))
        stat_t.start()
        print("INFO1:", datapath,parser, ofproto)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, meter_id=0, idle_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        if meter_id:
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions), parser.OFPInstructionMeter(1, ofproto.OFPIT_METER)]
        else:
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id, command=ofproto.OFPFC_ADD, flags=ofproto.OFPFF_SEND_FLOW_REM,
                                    priority=priority, match=match,
                                    instructions=inst, idle_timeout=idle_timeout)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, command=ofproto.OFPFC_ADD, flags=ofproto.OFPFF_SEND_FLOW_REM,
                                    match=match, instructions=inst, idle_timeout=idle_timeout)
        datapath.send_msg(mod)

    def add_meter(self, datapath):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        bands = [parser.OFPMeterBandDrop(type_=ofproto.OFPMBT_DROP, len_=0, rate=1000, burst_size=100)]
        req = parser.OFPMeterMod(datapath=datapath, command=ofproto.OFPMC_ADD, flags=ofproto.OFPMF_KBPS, meter_id=1, bands=bands)
        datapath.send_msg(req)
        pass

    def period_flow_stats_send(self, ev):
        print("Sending periodically")
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        while True:
            req = parser.OFPFlowStatsRequest(datapath, 0, ofproto.OFPTT_ALL,
                ofproto.OFPP_ANY, ofproto.OFPG_ANY, match=match)
            datapath.send_msg(req)
            time.sleep(10)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def period_flow_stats_reply(self, ev):
        flows = []
        for stat in ev.msg.body:
            flows.append(stat)
        print("Flows: ", flows)

    def interact_with_agent(self):
        pass

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)

        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        print(ether_types.ETH_TYPE_IP, "Come a packet: ", pkt.get_protocols(ethernet.ethernet))
        return 

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        out_queue = 1
        # if pkt.get_protocols(ipv4.ipv4):
        #     # count the statistics of flow
        #     ip = pkt.get_protocols(ipv4.ipv4)[0]
        #     if ip.proto == 6 or ip.proto == 17:
        #         if ip.proto == 6:
        #             tcpudp = pkt.get_protocols(tcp.tcp)[0]
        #         if ip.proto == 17:
        #             tcpudp = pkt.get_protocols(udp.udp)[0]
        #         index = (ip.src, ip.dst, tcpudp.src_port, tcpudp.dst_port, ip.proto)
        #         print(index)
        #         # update timeout count
        #         self.timeout[index] = 0
        #         if index in self.flow_set:
        #             out_queue = self.flow_set[index][1]
        #             self.flow_set[index][2] += 1
        #             self.flow_set[index][3] += ip.total_length
        #         else:
        #             self.flow_set[index] = [True, random.randint(0,3), 1, ip.total_length]
        #     for idx in self.timeout:
        #         self.timeout[idx] += 1
        #         if self.timeout[idx] > self.TIMEOUT_COUNT:
        #             del self.timeout[idx]
        #             self.flow_set[idx][0] = False
        #     print(pkt.protocols)
        # print(self.flow_set)
        # print(self.timeout)


        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # log infomation
        # self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        queue_id = out_queue
        actions = []
        actions.append(parser.OFPActionSetQueue(queue_id))
        actions.append(parser.OFPActionOutput(out_port))

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id, idle_timeout=60)
                print("I am here")
                return
            else:
                self.add_flow(datapath, 1, match, actions, idle_timeout=60)
                print("I am here2")
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def hard_coding_routing(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # bands = [parser.OFPMeterBandDrop(type_=ofproto.OFPMBT_DROP, len_=0, rate=1000, burst_size=100)]
        # bands = [parser.OFPMeterBandDrop(rate=1000, burst_size=100)]
        # req = parser.OFPMeterMod(datapath=datapath, command=ofproto.OFPMC_ADD, flags=ofproto.OFPMF_KBPS, meter_id=1, bands=bands)
        # print("REQ: ", req)
        # datapath.send_msg(req)

        buffer_id = None
        meter_id = 0
        priority = 1
        # actions = [parser.OFPActionSetQueue(queue_id),parser.OFPActionOutput(2)]
        actions = [parser.OFPActionOutput(2)]
        match = parser.OFPMatch(in_port=1)

        # print(match, actions)
        if meter_id:
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions), parser.OFPInstructionMeter(1)]
        else:
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

        meter_id = 0
        actions = [parser.OFPActionOutput(1)]
        match = parser.OFPMatch(in_port=2)
        # print(match, actions)
        if meter_id:
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions), parser.OFPInstructionMeter(1)]
        else:
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)