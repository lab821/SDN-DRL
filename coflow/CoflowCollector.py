import sys, os
sys.path.append(os.path.abspath("."))
from info_module import FlowCollector, Logger
from info_module import iptoint, inttoip

def test_ip_format(ip):
    """
    Test whether ip is a legal ip string.
    """
    if (type(ip) == str):
        words = ip.split('.')
        if len(words) == 4:
            try:
                ints = [eval(word) for word in words]
                for e in ints:
                    if type(e) != int or e < 0 or e > 255:
                        return False
            except Exception:
                return False
            return True
    return False

class CoflowCollector:
    def __init__(self, logger):
        self.flow_collector = FlowCollector(logger)
        with open("doc/coflow_pattern.txt", "r") as f:
            line = f.readline()
            num_coflow = int(line)
            self.pattern = {}
            # print(num_coflow)
            for _ in range(num_coflow):
                line = f.readline()
                words = line.split(" ")
                self.pattern[int(words[0])] = [iptoint(ip) for ip in words[1:] if test_ip_format(ip)]
            print("Pattern: ", self.pattern)

            self.attr_coflow = {}
            for id in self.pattern:
                for ip in self.pattern[id]:
                    if ip not in self.attr_coflow:
                        self.attr_coflow[ip] = id
                    else:
                        print("Coflow Error!")
            print("Attr: ", self.attr_coflow)
    
    def CoflowsToFormat(self, coflows):
        return coflows

    def collect_coflow(self):
        ## active(list): five-tuple, priority, active_time, active_size
        ## finished(list): five-tuple, fct, size
        active, finished = self.flow_collector.flow_collect()
        coflows_id = []
        for fl_a in active:
            id1 = self.attr_coflow.get(fl_a[0], -1)
            id2 = self.attr_coflow.get(fl_a[1], -1)
            if id1 == id2 and id1 != -1:
                fl_a.append(id1)
                coflows_id.append(id1)
            else:
                fl_a.append(-1) # means it's not a coflow
        for fl_f in finished:
            id1 = self.attr_coflow.get(fl_f[0], -1)
            id2 = self.attr_coflow.get(fl_f[1], -1)
            if id1 == id2 and id1 != -1:
                fl_f.append(id1)
                coflows_id.append(id1)
            else:
                fl_f.append(-1)
        # coflows format: {id: info}, info is {"size":, "duration":, "is_active":, "priority":, "num_total":, "num_active":,
        # "active_flows":, "finished_flows":}
        coflows = {}
        for id in coflows_id:
            fl_as = [fl for fl in active if fl[-1] == id]
            fl_fs = [fl for fl in finished if fl[-1] == id]
            coflows[id] = {"size": 0, "duration": 0, "is_active": False, "priority": -1, "num_total": 0, "num_active": 0}
            coflows[id]["num_active"] = len(fl_as)
            coflows[id]["num_total"] = len(fl_as) + len(fl_fs)
            if len(fl_as) != 0:
                coflows[id]["is_active"] = True
            sizes = [fl[7] for fl in fl_as]
            sizes.extend([fl[6] for fl in fl_fs])
            coflows[id]["size"] = sum(sizes)
            durations = [fl[6] for fl in fl_as]
            durations.extend([fl[5] for fl in fl_fs])
            coflows[id]["duration"] = max(durations)
            coflows[id]["active_flows"] = [fl[:5] for fl in fl_as]
            coflows[id]["finished_flows"] = [fl[:5] for fl in fl_fs]
        return self.CoflowsToFormat(coflows)

    def apply_coflow_prio(self, coflows, actions):
        """
        The format of coflows has not been modified.
        actions: {id: priority}
        """
        fl_actions = []
        for id in actions:
            prio = actions[id]
            # print("active: ", coflows[id]["active_flows"])
            for fl in coflows[id]["active_flows"]:
                flow = []
                flow.extend(fl)
                flow.append(prio)
                fl_actions.append(flow)
        self.flow_collector.action_apply(fl_actions)


if __name__ == "__main__":
    cc = CoflowCollector(Logger("log/log.txt"))
    for _ in range(10):
        coflows = cc.collect_coflow()
        actions = {}
        for id in coflows:
            actions[id] = 1
        cc.apply_coflow_prio(coflows, actions)