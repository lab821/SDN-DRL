import requests
import json
import time
import socket
import numpy as np

def iptoint(ip):
    ip_l = np.array([int(num) for num in ip.split('.')])
    cst = np.array([256*256*256, 256*256, 256, 1])
    return (ip_l*cst).sum()

def inttoip(n):
    return "%s.%s.%s.%s"%(n//256//256//256,(n//256//256)%256,(n//256)%256,n%256)

class Flow:
    """
    A flow is just a flow entry in Switch, including:
    match:{dl_type, nw_src, nw_dst, nw_proto, tp_src, tp_dst}
    actions: ['OUTPUT:PORT', 'METER:id']
    packet_count:
    byte_count:
    priority:
    table_id:
    length:
    idle_timeout:
    duration_nsec:
    duration_sec:
    hard_timeout:
    flags:
    cookie:
    """

    def __init__(self, flow):
        assert type(flow)==dict, "Type of flow is not 'dict'"
        self.match = flow['match']
        self.actions = flow['actions']
        self.packet_count = flow['packet_count']
        self.byte_count = flow['byte_count']
        self.priority = flow['priority']
        self.table_id = flow['table_id']
        self.length = flow['length']
        self.idle_timeout = flow['idle_timeout']
        self.duration_nsec = flow['duration_nsec']
        self.duration_sec = flow['duration_sec']
        self.hard_timeout = flow['hard_timeout']
        self.flags = flow['flags']
        self.cookie = flow['cookie']
        self.meter_id = 1
        for entry in flow['actions']:
            if entry.find("METER") is not -1:
                self.meter_id = int(entry.split(":")[1])
    
    def contain_five_tuple(self):
        return 'nw_src' in self.match and 'nw_dst' in self.match and 'nw_proto' in self.match and 'tp_src' in self.match and 'tp_dst' in self.match
    
    def to_five_tuple(self):
        return [
            iptoint(self.match['nw_src']),
            iptoint(self.match['nw_dst']),
            self.match['nw_proto'],
            self.match['tp_src'],
            self.match['tp_dst']
        ]

    def __eq__(self, other):
        if self.contain_five_tuple() and other.contain_five_tuple():
            return (self.match['nw_src'] == other.match['nw_src']) and (self.match['nw_dst'] == other.match['nw_dst']) and (self.match['nw_proto'] == other.match['nw_proto']) and (self.match['tp_src'] == other.match['tp_src']) and (self.match['tp_dst'] == other.match['tp_dst'])
        else:
            return json.dumps(self.match) == json.dumps(other.match)

    def __hash__(self):
        return hash(json.dumps(self.match))
    
    def __repr__(self):
        try:
            # return "(ip_src:%s ip_dst:%s proto:%s port_src:%s port_dst:%s)" % (self.match['nw_src'], self.match['nw_dst'], self.match['nw_proto'], self.match['tp_src'], self.match['tp_dst'])
            return "(%s, %s, %s, %s, %s)" % (self.match['nw_src'], self.match['nw_dst'], self.match['nw_proto'], self.match['tp_src'], self.match['tp_dst'])
        except Exception:
            return "("+json.dumps(self.match)+")"

class FlowCollector:
    """
    Given the interface with agent enviroment
    state: (MAX_STATE_LEN, FLOW_LEN)
    reward: float value

    Flow format
    active flow: {five-tuple : {priority, active_time, active_size}}
    finished flow: {five-tuple : {fct, size}}
    """
    MAX_STATE_LEN = 100
    FLOW_LEN = 7
    EPSILON = 3 # seconds

    """
    local infomation collection
    FLOW_STATS_URL: the website of flow statistics
    METER_CONFIG_URL: the website of meter configuration
    METER_STATS_URL: the website of meter statistics
    """
    FLOW_STATS_URL = "http://localhost:8080/stats/flow/1"
    FLOW_MODIFY_STRICT = "http://localhost:8080/stats/flowentry/modify_strict"
    METER_CONFIG_URL = "http://localhost:8080/stats/meterconfig/1"
    METER_STATS_URL = "http://localhost:8080/stats/meter/1"
    METER_ADD = "http://localhost:8080/stats/meterentry/add"
    METER_MODIFY = "http://localhost:8080/stats/meterentry/modify"
    
    def __init__(self):
        self.flow_stats = {}
        self.active_flows = {}
        self.finished_flows = {}

    def __simplify__(self):
        active = []
        finished = []
        for flow in self.active_flows:
            if flow.contain_five_tuple():
                fl = []
                fl.extend(flow.to_five_tuple())
                fl.extend((
                    self.active_flows[flow]['priority'],
                    self.active_flows[flow]['active_time'],
                    self.active_flows[flow]['active_size']
                ))
                active.append(fl)
        for flow in self.finished_flows:
            if flow.contain_five_tuple():
                fl = []
                fl.extend(flow.to_five_tuple())
                fl.extend((
                    self.finished_flows[flow]['fct'],
                    self.finished_flows[flow]['size']
                ))
                finished.append(fl)
        active.sort(key=lambda a:a[7], reverse=True)
        finished.sort(key=lambda a:a[6], reverse=True)
        return (active, finished)

    def flow_collect(self):
        # flow collection
        self.finished_flows = {}
        response = requests.get(FlowCollector.FLOW_STATS_URL)
        data = json.loads(response.text)
        for flow_ in data['1']:
            flow = Flow(flow_)
            # match = json.dumps(flow.match)
            pkt_count = flow.packet_count
            byte_count = flow.byte_count
            if flow in self.flow_stats:
                if self.flow_stats[flow]['packet_count'] == pkt_count:
                    if flow in self.active_flows:
                        # completed flows
                        # add a finished flow and delete an active flow
                        self.finished_flows[flow] = {'fct':self.active_flows[flow]['active_time'], 'size':self.active_flows[flow]['active_size']}
                        del self.active_flows[flow]
                else:
                    # active and old flows
                    if flow in self.active_flows:
                        # continue an active flow
                        self.active_flows[flow]['active_time'] += 1
                        # print(flow, self.active_flows, self.flow_stats)
                        self.active_flows[flow]['active_size'] += (byte_count - self.flow_stats[flow]['byte_count'])
                    else:
                        # start an old flow
                        self.active_flows[flow] = {'priority':flow.meter_id, 'active_time':1, 'active_size': byte_count - self.flow_stats[flow]['byte_count']}
                # update flow_stats
                self.flow_stats[flow]['packet_count'] = pkt_count
                self.flow_stats[flow]['byte_count'] = byte_count
            else:
                # active and new flows
                self.flow_stats[flow] = {'packet_count':pkt_count, 'byte_count':byte_count}
                self.active_flows[flow] = {'priority':flow.meter_id, 'active_time':1, 'active_size':byte_count}
        if False:
            print("Active: ")
            for k in self.active_flows:
                print(k, self.active_flows[k])
            print("Completed: ")
            for k in self.finished_flows:
                print(k, self.finished_flows[k])
            print('**')
        time.sleep(FlowCollector.EPSILON)

        return self.__simplify__()
        # return self.active_flows, self.finished_flows
            
    def action_apply(self, actions):
        """
        actions:[
            [nw_src(int), nw_dst(int), nw_proto, tp_src, tp_dst, meter_id],
            [nw_src(int), nw_dst(int), nw_proto, tp_src, tp_dst, meter_id],
            ...
            [nw_src(int), nw_dst(int), nw_proto, tp_src, tp_dst, meter_id]
        ]
        """
        acts = [Action(action) for action in actions]
        response = requests.get(FlowCollector.FLOW_STATS_URL)
        data = json.loads(response.text)
        # print("DATA: ",data)
        for act in acts:
            # print("Action: ", act)
            for fl_d in data['1']:
                # print(fl_d)
                if Match.is_five_tuple(fl_d['match']) and act.eq_flow_data(fl_d['match']):
                    # modify actions, apply the new meter id
                    new_actions = []
                    for a in fl_d["actions"]:
                        if "METER" in a:
                            new_actions.append({
                                "type":"METER",
                                "meter_id":act.meter_id
                            })
                        if "OUTPUT" in a:
                            port = int(a.split(":")[-1])
                            new_actions.append({
                                "type":"OUTPUT",
                                "port": port
                            })
                    fl_d["dpid"] = 1
                    fl_d['actions'] = new_actions
                    requests.post(FlowCollector.FLOW_MODIFY_STRICT, json.dumps(fl_d))

class Match:
    def __init__(self):
        self.nw_src = None
        self.nw_dst = None
        self.nw_proto = None
        self.tp_src = None
        self.tp_dst = None
    
    def from_five_t(self, five_t):
        self.nw_src = inttoip(five_t[0])
        self.nw_dst = inttoip(five_t[1])
        self.nw_proto = five_t[2]
        self.tp_src = five_t[3]
        self.tp_dst = five_t[4]
        return self
    
    def from_flow(self, flow):
        assert type(flow)==Flow, "Please input class `Flow`"
        assert flow.contain_five_tuple(), "flow doesn't contain five tuple"
        self.nw_src = flow.match['nw_src']
        self.nw_dst = flow.match['nw_dst']
        self.nw_proto = flow.match['nw_proto']
        self.tp_src = flow.match['tp_src']
        self.tp_dst = flow.match['tp_dst']
        return self
    
    def is_five_tuple(dl):
        assert type(dl) == dict, "Please input class `dict`."
        return (
            'nw_src' in dl and 'nw_dst' in dl and 'nw_proto' in dl and
            'tp_src' in dl and 'tp_dst' in dl
        )
    
    def __eq__(self, other):
        return (self.nw_src == other.nw_src) and (self.nw_dst == other.nw_dst) and (self.nw_proto == other.nw_proto) and (self.tp_src == other.tp_src) and (self.tp_dst == other.tp_dst)

    def __hash__(self):
        return hash(self.nw_src+self.nw_dst+"%s%s%s"%(self.nw_proto, self.tp_src, self.tp_dst))
    
    def __repr__(self):
        return "(%s, %s, %s, %s, %s)" % (self.nw_src, self.nw_dst, self.nw_proto, self.tp_src, self.tp_dst)

class Action:
    def __init__(self, six_t):
        self.match = Match()
        self.match.from_five_t(six_t[:5])
        self.meter_id = six_t[5]
    
    def eq_flow_data(self, df):
        assert type(df)==dict, "df should be `dict` class"
        # print(df, self.match)
        return (
            (self.match.nw_src == df['nw_src']) and
            (self.match.nw_dst == df['nw_dst']) and
            (self.match.nw_proto == df['nw_proto']) and
            (self.match.tp_src == df['tp_src']) and
            (self.match.tp_dst == df['tp_dst'])
        )
    
    def __repr__(self):
        return self.match.__repr__()+" Meter ID: "+str(self.meter_id)

if __name__ == "__main__":
    response = requests.get(FlowCollector.FLOW_STATS_URL)
    data = json.loads(response.text)
    fl = Flow(data['1'][0])
    a = iptoint("10.0.0.2")
    print(inttoip(a))
    collector = FlowCollector()
    print(fl)
    m = Match().from_flow(fl)
    action = [iptoint(m.nw_src), iptoint(m.nw_dst), m.nw_proto, m.tp_src, m.tp_dst, 10]
    collector.action_apply([action])