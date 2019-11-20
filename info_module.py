import requests
import json
import time
import socket
import numpy as np
import threading
import os
from queue import Queue

remote_url = "10.134.147.138"

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
        self.queue_id = 0
        for entry in flow['actions']:
            if entry.find("METER") is not -1:
                self.meter_id = int(entry.split(":")[1])
            if entry.find("SET_QUEUE") is not -1:
                self.queue_id = int(entry.split(":")[1])
    
    def is_empty(self):
        return self.match == {}
    
    def contain_five_tuple(self):
        return 'nw_src' in self.match and 'nw_dst' in self.match and 'nw_proto' in self.match and 'tp_src' in self.match and 'tp_dst' in self.match
    
    def get_five_tuple(self):
        if self.contain_five_tuple():
            return (self.match['nw_src'], self.match['nw_dst'], self.match['nw_proto'], self.match['tp_src'], self.match['tp_dst'])
        else:
            return "controller"

    def to_five_list(self):
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

    Flow format(discard)
    active flow: {five-tuple : {priority, active_time, active_size}}
    finished flow: {five-tuple : {fct, size}}

    Format v2: {five-tuple : {packet_count, byte_count, active_time, priority, is_active}}
    """
    # MAX_STATE_LEN = 100
    # FLOW_LEN = 7
    """ make sure that FLOW COLLECT interval is less than idle_timeout(default 60 seconds) """
    EPSILON = 3 # seconds
    # UPDATE_EPSILON = 0.001 # seconds

    SAMPLE_EPSILON = 100 # ms
    FLOW_DELIMETER = 1000 # ms

    """
    Multiple Level Feedback Queue
    num_level: number of level in MLFQ
    """
    num_level = 2

    """
    local infomation collection
    FLOW_STATS_URL: the website of flow statistics
    METER_CONFIG_URL: the website of meter configuration
    METER_STATS_URL: the website of meter statistics
    """
    URL = "localhost"
    # URL = remote_url
    FLOW_STATS_URL = "http://"+URL+":8080/stats/flow/1"
    FLOW_MODIFY_STRICT = "http://"+URL+":8080/stats/flowentry/modify_strict"
    FLOW_DELETE = "http://"+URL+":8080/stats/flowentry/delete"
    METER_CONFIG_URL = "http://"+URL+":8080/stats/meterconfig/1"
    METER_STATS_URL = "http://"+URL+":8080/stats/meter/1"
    METER_ADD = "http://"+URL+":8080/stats/meterentry/add"
    METER_MODIFY = "http://"+URL+":8080/stats/meterentry/modify"
    
    def __init__(self, logger):
        self.logger = logger
        self.clk = 0 # ms

        """
        {five_tuple : {packet_count,byte_count,duration_time,active_time, priority,is_active}}
        """
        self.flow_stats = {} # stage flow stats
        self.finished_queue = Queue(maxsize=1000)
        # self.active_flows = {}
        # self.finished_flows = {}
        """ mini_stats: {flow(five_tuple) : packet_count,byte_count,priority,active_time,is_active} """
        # self.mini_stats = {} # update flow stats

        self.thresholds = [0] # len(self.threshold) is num_level, threshold is byte_count
        self.threshold_sum = [0]
        # self.METER_ID = [1, 2] # meter id according to each queue from high prio to low
        self.QUEUES = (0, 1) # queue id according to each queue from high prio to low

        # self.lock = threading.Lock()
        # threading.Thread(target=self.while_update).start()
        # threading.Thread(target=self.mark_prio).start()
        threading.Thread(target=self.sample).start()
    
    def sum_threshold(self):
        """
        calculate the accumulation of self.thresholds, which is stored in self.threshold_sum
        """
        self.threshold_sum = []
        last = 0
        for t in self.thresholds:
            self.threshold_sum.append(t+last)
            last = self.threshold_sum[-1]
        return self.threshold_sum
    
    def judge_level(self, count):
        ## calculate the priority flow belongs to, als called meter id
        for i in range(len(self.threshold_sum)):
            if count < self.threshold_sum[i]:
                return self.QUEUES[i]
        return self.QUEUES[-1]

    def mark_prio(self):
        while True:
            actions = []
            for match in self.flow_stats:
                if match == "controller":
                    continue
                if self.flow_stats[match]["is_active"]:
                    k = self.judge_level(self.flow_stats[match]["byte_count"])
                    if self.flow_stats[match]["priority"] != k:
                        actions.append([iptoint(match[0]), iptoint(match[1]), match[2], match[3], match[4], k])
            # make flow-queue_id take effect
            if actions != []:
                self.action_apply(actions)
                print("mark_prio: ", self.clk)

    def change_threshold(self, nthreshold):
        """
        change self.threshold with new values
        With self.threshold changing, self.threshold_sum also need to change.
        """
        assert type(nthreshold) == list or type(nthreshold) == np.ndarray, "make sure the type of nthreshold is list"
        assert len(nthreshold)==len(self.thresholds), "make sure the length of nthreshold is %s"%(len(self.thresholds))
        self.thresholds = nthreshold
        self.sum_threshold()
        assert len(self.thresholds) == self.num_level-1, "Error of changing thresholds"

    # def __simplify__(self):
    #     """ 
    #     neither self.active_flows nor self.finished_flows have non-five-tuple flow
    #     active(list): five-tuple, priority, active_time, active_size
    #     finished(list): five-tuple, fct, size
    #     """
    #     active = []
    #     finished = []
    #     for flow in self.active_flows:
    #         fl = []
    #         fl.extend(flow.to_five_tuple())
    #         fl.extend((
    #             self.active_flows[flow]['priority'],
    #             self.active_flows[flow]['active_time'],
    #             self.active_flows[flow]['byte_count']
    #         ))
    #         active.append(fl)
    #     for flow in self.finished_flows:
    #         fl = []
    #         fl.extend(flow.to_five_tuple())
    #         fl.extend((
    #             self.finished_flows[flow]['active_time'],
    #             self.finished_flows[flow]['byte_count']
    #         ))
    #         finished.append(fl)
    #     active.sort(key=lambda a:a[7], reverse=True)
    #     finished.sort(key=lambda a:a[6], reverse=True)
    #     return (active, finished)
    
    # def while_update(self):
    #     while True:
    #         self.update_stats()
    #         self.clk += self.UPDATE_EPSILON

    def sample(self):
        while True:
            self.clk += self.SAMPLE_EPSILON
            try:
                response = requests.get(FlowCollector.FLOW_STATS_URL)
                data = json.loads(response.text)
                update_l = []
                for flow_ in data['1']:
                    flow = Flow(flow_)
                    match = flow.get_five_tuple()
                    if match == "controller":
                        continue
                    # print("match: ", match)
                    if match in self.flow_stats:
                        if self.flow_stats[match]["is_active"]:
                            if self.flow_stats[match]["packet_count"] != flow.packet_count:
                                self.flow_stats[match]["active_time"] = self.SAMPLE_EPSILON + self.flow_stats[match]["duration_time"]
                            self.flow_stats[match]["packet_count"] = flow.packet_count
                            self.flow_stats[match]["byte_count"] = flow.byte_count
                            self.flow_stats[match]["duration_time"] += self.SAMPLE_EPSILON
                            # print("debug: ", self.flow_stats)
                            self.flow_stats[match]["priority"] = flow.queue_id
                            if self.flow_stats[match]["duration_time"]-self.flow_stats[match]["active_time"] >= self.FLOW_DELIMETER:
                                self.flow_stats[match]["is_active"] = False
                                ## add flow into finished queue
                                self.finished_queue.put((match, self.flow_stats[match].copy()))
                                ## delete flow from flow table in ovs
                                self.delete_specified_flow(flow)
                        else:
                            self.flow_stats[match]["packet_count"] = flow.packet_count
                            self.flow_stats[match]["byte_count"] = flow.byte_count
                            self.flow_stats[match]["duration_time"] = self.SAMPLE_EPSILON
                            self.flow_stats[match]["active_time"] = self.SAMPLE_EPSILON
                            self.flow_stats[match]["priority"] = flow.queue_id
                            self.flow_stats[match]["is_active"] = True
                    else:
                        self.flow_stats[match] = {"packet_count" : flow.packet_count,
                                                "byte_count" : flow.byte_count,
                                                "duration_time" : self.SAMPLE_EPSILON,
                                                "active_time" : self.SAMPLE_EPSILON,
                                                "priority" : flow.queue_id,
                                                "is_active" : True}
                    # here match must not be "controller"
                    assert len(match) == 5, "Match may be 'controller'"
                    k = self.judge_level(self.flow_stats[match]["byte_count"])
                    if k != self.flow_stats[match]["priority"]:
                        update_l.append([iptoint(match[0]), iptoint(match[1]), match[2], match[3], match[4], k])
                if update_l != []:
                    # print(update_l)
                    self.action_apply(update_l)
                time.sleep(self.SAMPLE_EPSILON/1000)
                # print("debug: ", self.flow_stats)
            except json.decoder.JSONDecodeError as e:
                print("Get JSONDecodeError: ", e)

    # def update_stats(self):
    #     try:
    #         # flow collection
    #         response = requests.get(FlowCollector.FLOW_STATS_URL)
    #         data = json.loads(response.text)
    #         for flow_ in data['1']:
    #             flow = Flow(flow_)
    #             # match = json.dumps(flow.match)
    #             pkt_count = flow.packet_count
    #             byte_count = flow.byte_count
    #             if flow in self.mini_stats:
    #                 ## update all value in flow 
    #                 tmp = self.mini_stats[flow]
    #                 del self.mini_stats[flow]
    #                 self.mini_stats[flow] = tmp
    #                 if self.mini_stats[flow]['packet_count'] == pkt_count:
    #                     # marked by finished
    #                     self.mini_stats[flow]['active_time'] += self.UPDATE_EPSILON
    #                     self.mini_stats[flow]['priority'] = flow.queue_id
    #                     self.mini_stats[flow]['is_active'] = False
    #                 else:
    #                     # update active flow_stats
    #                     self.mini_stats[flow]['packet_count'] = pkt_count
    #                     self.mini_stats[flow]['byte_count'] = byte_count
    #                     self.mini_stats[flow]['active_time'] += self.UPDATE_EPSILON
    #                     self.mini_stats[flow]['priority'] = flow.queue_id
    #                     self.mini_stats[flow]['is_active'] = True
    #             else:
    #                 # new flows, marked by active
    #                 self.mini_stats[flow] = {'packet_count':pkt_count, 'byte_count':byte_count, 'priority':flow.queue_id, 
    #                                         'active_time':self.UPDATE_EPSILON, 'is_active':True}
    #                 pass
    #         # generate active and finished flows
    #         self.active_flows = {flow:self.mini_stats[flow] for flow in self.mini_stats if self.mini_stats[flow]['is_active'] and not flow.is_empty()}
    #         self.lock.acquire()
    #         self.finished_flows = {flow:self.mini_stats[flow] for flow in self.mini_stats if (not self.mini_stats[flow]['is_active'] and not flow.is_empty())}
    #         self.lock.release()
    #         # print("mini_stats: ", self.mini_stats)
    #         # print('active: ', self.active_flows)
    #         # print('finished: ', self.finished_flows)
    #         time.sleep(FlowCollector.UPDATE_EPSILON)
    #     except json.decoder.JSONDecodeError as e:
    #         print("JsonDecodeError: ", e)


    def delete_specified_flow(self, flow):
        assert type(flow)==Flow, "Type of flow to delete is not 'Flow'"
        fl_post = {}
        fl_post['dpid'] = 1 # dpid is default to 1
        fl_post['table_id'] = flow.table_id
        fl_post['match'] = flow.match
        requests.post(FlowCollector.FLOW_DELETE, json.dumps(fl_post))

    def convertToStandard(self, active, finished):
        """
        active(list): five-tuple, priority, active_time, active_size
        finished(list): five-tuple, fct, size
        """
        active_s = []
        finished_s = []
        for e in active:
            match = e[0]
            info = e[1]
            active_s.append([
                iptoint(match[0]), iptoint(match[1]), match[2], match[3], match[4],
                info["priority"], info["active_time"], info["byte_count"]
            ])
        for match in finished:
            # match
            m = match[1:-1].split(',')
            finished_s.append([
                iptoint(m[0][1:-1]), iptoint(m[1][2:-1]), int(m[2]), int(m[3]), 
                int(m[4]), finished[match]["active_time"], 
                finished[match]["byte_count"]
            ])
        active_s.sort(key=lambda a:a[7], reverse=True)
        finished_s.sort(key=lambda a:a[6], reverse=True)
        return (active_s, finished_s)

    def flow_collect(self):
        # print("flow_collect: ", self.flow_stats)
        active = [(match, self.flow_stats[match].copy()) for match in self.flow_stats if self.flow_stats[match]["is_active"]]
        res = {}
        while not self.finished_queue.empty():
            match, info = self.finished_queue.get()
            res[match.__str__()] = info
        self.logger.print("finished_flows/%s:"%(self.clk)+json.dumps(res))
        time.sleep(FlowCollector.EPSILON)
        return self.convertToStandard(active, res)
            
    def action_apply(self, actions):
        """
        actions:[
            [nw_src(int), nw_dst(int), nw_proto, tp_src, tp_dst, priority],
            [nw_src(int), nw_dst(int), nw_proto, tp_src, tp_dst, priority],
            ...
            [nw_src(int), nw_dst(int), nw_proto, tp_src, tp_dst, priority]
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
                    # modify actions, apply the new priority id
                    new_actions = []
                    for a in fl_d["actions"]:
                        if "SET_QUEUE" in a:
                            new_actions.append({
                                "type":"SET_QUEUE",
                                "queue_id":act.priority
                            })
                        if "OUTPUT" in a:
                            port = int(a.split(":")[-1])
                            new_actions.append({
                                "type":"OUTPUT",
                                "port": port
                            })
                    fl_d["dpid"] = 1
                    fl_d['actions'] = new_actions
                    # print("fl_d: ", type(fl_d), fl_d)
                    req = requests.post(FlowCollector.FLOW_MODIFY_STRICT, json.dumps(fl_d))
                    # print(req)

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
    
    @staticmethod
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
        self.priority = six_t[5]
    
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
        return self.match.__repr__()+" Priority: "+str(self.priority)

class Logger:
    def __init__(self, file):
        assert type(file) == str, "please given a right file of 'str'."
        if os.path.exists(file):
            os.remove(file)
        self.filename = file
    
    def print(self, info):
        assert type(info) == str, "Info into logger should be a string."
        log = open(self.filename, 'a')
        log.write(info+"\n")
        log.close()

if __name__ == "__main__":
    # response = requests.get(FlowCollector.FLOW_STATS_URL)
    # data = json.loads(response.text)
    # fl = Flow(data['1'][0])
    # a = iptoint("10.0.0.2")
    # print(inttoip(a))
    # collector = FlowCollector()
    # print(fl)
    # m = Match().from_flow(fl)
    # action = [iptoint(m.nw_src), iptoint(m.nw_dst), m.nw_proto, m.tp_src, m.tp_dst, 10]
    # collector.action_apply([action])
    fc = FlowCollector(Logger('log/log.txt'))
    for _ in range(5000):
        fc.flow_collect()
        # print(fc.flow_collect())
        # print()