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
                        fn_flows.append([timestamp/1000, fl, fls[fl]['byte_count']/(1024*1024), fls[fl]['packet_count'], fls[fl]['active_time']/1000])
            step += 1
            # if step > 1020:
            #     break
            line = f.readline()
        fn_flows = fn_flows[100:]
        print("fn_flows: ", len(fn_flows), fn_flows[-1])
        obj_flows = [e for e in fn_flows if e[2] > 0.2] # only calculate size > 0MB
        print("obj_flows(size > 0): ", len(obj_flows))
        plt.figure()
        #
        ## draw CDF about flow size distribution:MB ##
        #
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
        #
        ## draw the number of finished flows with time ##
        #
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
        x_p = 10
        plt.plot(num_f_t[x_p:, 0], num_f_t[x_p:, 1])
        plt.ylabel("number of finished flows")
        plt.xlabel("time(s)")
        #
        ## figure about average flow completion time with time ##
        #
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
        x_p = 10
        plt.plot(avg_fct[x_p:, 0], avg_fct[x_p:, 1])
        plt.xlabel("time(s)")
        plt.ylabel("average FCT(s)")

        ## throughout
        plt.subplot(224)
        batch = 10
        throughout = []
        aggre_flows = []
        old_t = 0
        tmp = []
        for e in obj_flows:
            if e[0] != old_t:
                aggre_flows.append(tmp)
                old_t = e[0]
                tmp = [e]
            else:
                tmp.append(e)
        del aggre_flows[0]
        for i in range(batch, len(aggre_flows)):
            t = 0
            for e in aggre_flows[i-batch:i]:
                t += sum([8*f[2]/f[4] for f in e])
            delta_t = aggre_flows[i-1][0][0] - aggre_flows[i-batch][0][0]
            throughout.append([aggre_flows[i-1][0][0], t/delta_t])
        plt.plot([e[0] for e in throughout], [e[1] for e in throughout])
        plt.xlabel("time(s)")
        plt.ylabel("Thoughout(Mbps)")


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
        pattern = []
        while line:
            l = line.split()
            time = int(l[1])
            send_num = int(l[2])
            recv_num = int(l[send_num+3])
            flow_size = [float(i) for i in l[-(send_num*recv_num):]]
            pattern.append(flow_size)
            fls.extend(flow_size)
            line = f.readline()
        ### plot the CDF about flow size ###
        # print(fls)
        cdf = np.array(toCDF(fls))
        plt.figure()
        plt.plot(cdf[:, 0], cdf[:, 1])
        plt.xlabel("flow size/MB")
        plt.ylabel("probability")

        ### Pattern ###
        last_l = [e[-1] for e in pattern]
        print(len(last_l))
        k = 1
        while k < len(last_l)/2:
            i = 0
            j = 0
            while i+j < k:
                if last_l[i+j] != last_l[k+j]:
                    break
                j += 1
            if i+j == k:
                print("basic flow N: ", k)
                break
            k += 1

def train_log(filename):
    with open(filename, "r") as f:
        line = f.readline()
        k = 0
        reward_l = []
        while line:
            words = line.split(":")
            # action = json.loads(words[-1])
            reward = float(words[-2].split(" ")[-2])
            reward_l.append(reward)
            # print(action, reward, type(action), type(reward))
            line = f.readline()
            k += 1
            if k > 1e3:
                break
        
        ### plot the figure about reward ###
        plt.subplot(211)
        plt.plot(range(len(reward_l)), reward_l)
        plt.ylabel("reward")

        ### plot the figure about accumulated reward ###
        plt.subplot(212)
        reward_acc = [0]
        for r in reward_l:
            reward_acc.append(reward_acc[-1] + r)
        del reward_acc[0]
        plt.plot(range(len(reward_acc)), reward_acc)
        plt.ylabel("accumulated reward")


if __name__ == "__main__":
    # analysis_new_log("log/log.txt")
    # analysis_log("log/log_test.txt")
    # analysis_trace("log/trace200.txt")

    analysis_log("log/20191112_log_1.txt")
    plt.figure()
    train_log("log/20191112_train_log_1.txt")
    plt.show()