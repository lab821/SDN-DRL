import numpy as np 
import matplotlib.pyplot as plt
import json

def analysis_log(filename="log/log.txt", save_path="log/"):
    with open(filename, "r") as f:
        line = f.readline()
        fn_flows = []
        step = 0
        while line:
            if line.startswith("finished_flows"):
                sep = line.find(":")
                timestamp = int(line[:sep].split("/")[-1])
                data = line[sep+1:]
                fls = json.loads(data)
                if fls != {}:
                    # print(type(data), type(fls), fls)
                    for fl in fls:
                        fn_flows.append([timestamp, fl, fls[fl]['byte_count']/(1024*1024), fls[fl]['packet_count'], fls[fl]['active_time']])
            step += 1
            # if step > 2000:
            #     break
            line = f.readline()
        print("fn_flows: ", len(fn_flows), fn_flows[-1])
        obj_flows = [e for e in fn_flows if e[2] > 0.2] # only calculate size > 0MB
        print("obj_flows(size > 0): ", len(obj_flows))
        plt.figure()
        ## draw CDF about flow size distribution:MB ##
        plt.subplot(221)
        bcs = sorted([e[2] for e in obj_flows if e[2] > 0.2])      # byte_count list
        print("len(bcs): ", len(bcs), " max: ", bcs[-1])
        bcs_p = toCDF(bcs)
        bcs_p = np.array(bcs_p)
        x_1mb = 0
        for i, e in enumerate(bcs_p[:, 0]):
            if e < 1:
                x_1mb = i
        # print(x_1mb, bcs_p.shape[0])
        x_1mb = 0
        plt.plot(bcs_p[x_1mb:, 0], bcs_p[x_1mb:, 1])
        plt.xlabel("size(MB)")
        plt.ylabel("probability")
        ## draw the number of finished flows with time ##
        plt.subplot(222)
        t = 0
        flows_t = [] # format: [[fl1_1, fl1_2, ...], ...]
        # obj_flows = [[1], [1], [2], [3]]
        for fl in obj_flows:
            if fl[0] == t:
                flows_t[-1].append(fl)
            else:
                flows_t.append([fl])
                t = fl[0]
        # print(flows_t)
        num_f_t = np.array([[e[0][0], len(e)] for e in flows_t])
        x_p = 0
        plt.plot(num_f_t[x_p:, 0], num_f_t[x_p:, 1])
        plt.ylabel("number of finished flows")
        plt.xlabel("time(s)")
        ## figure about average flow completion time with time ##
        plt.subplot(223)
        avg_fct = []
        cnt_f_s = [0, 0] # number of flows, accumulation of fct
        for fls in flows_t:
            cnt_f_s[0] += len(fls)
            fls_sum_t = sum([fl[-1] for fl in fls])
            cnt_f_s[1] += fls_sum_t
            avg_fct.append([fls[0][0], cnt_f_s[1]/cnt_f_s[0]])
        # print("average fct: ", avg_fct)
        avg_fct = np.array(avg_fct)
        plt.plot(avg_fct[:, 0], avg_fct[:, 1])
        plt.xlabel("time(s)")
        plt.ylabel("average FCT")

        # plt.show()

def toCDF(data_l):
    """ 
    data is discrete.
    example:
    [1,1,2,3] -> [[1, 0.5], [2, 0.5], [2, 0.75], [3, 0.75], [3, 1.0]]
    """
    l_dict = {}
    for e in sorted(data_l):
        if e in l_dict:
            l_dict[e] += 1
        else:
            l_dict[e] = 1
    l_sum = 0
    res = [[0, 0]]
    for e in sorted(l_dict):
        l_sum += l_dict[e]/len(data_l)
        res.append([e, res[-1][1]])
        res.append([e, l_sum])
    del res[:2]
    return res

def analysis_trace(filename):
    # 1 14285 2 3 1 1 1 51.68 6.39
    # number, start time(ms), number of sending hosts:3/1, receive...
    # flow size: 51.68MB 6.39MB
    with open(filename, "r") as f:
        line = f.readline() # read the summary
        n = int(line.split()[-1])
        line = f.readline()
        fls = [] # unit is MB
        while line:
            l = line.split()
            time = int(l[1])
            send_num = int(l[2])
            recv_num = int(l[send_num+3])
            flow_size = [float(i) for i in l[-(send_num*recv_num):]]
            fls.extend(flow_size)
            line = f.readline()
        # print(fls)
        cdf = np.array(toCDF(fls))
        plt.figure()
        plt.plot(cdf[:, 0], cdf[:, 1])


if __name__ == "__main__":
    # analysis_log("log/no_schedule_log.txt")
    analysis_trace("log/trace200.txt")
    plt.show()