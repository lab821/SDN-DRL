from coflow.CoflowCollector import CoflowCollector
from info_module import Logger
from coflow.scheduler import DDQNCS

cc = CoflowCollector(Logger("log/log.txt"))
agent = DDQNCS()
while (True):
    coflows = cc.collect_coflow()
    coflowinfo = []
    for id in coflows:
        coflow = {}
        coflow['index'] = id
        coflow['duration'] = coflows[id]['duration']
        coflow['sentsize'] = coflows[id]['size']
        coflow['count'] = coflows[id]['num_active']
        coflow['total_count'] = coflows[id]['num_total']
        coflowinfo.append(coflow)
    actions, info = agent.train(None, None, coflowinfo, False)
    print(info)
    cc.apply_coflow_prio(coflows, actions)