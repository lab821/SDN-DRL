#The scheduler module
#TODO: Implementing a General Scheduling Algorithms Interface

from algorithms.dqn import DQN
from algorithms.ddqn import DDQN, models
import pandas as pd
import numpy as np

NUM_A = 5
NUM_F = 5

def scheduler(actq, cptq):
    res = {}
    return res

class DQNscheduler():
    def __init__(self):
        self.agent = DQN()
        self.last_state = np.zeros(6*NUM_A+7*NUM_F, dtype = np.int)
        self.last_action = 0
        self.last_througout = 0
        self.key = []

    def train(self, actq, cptq):
        '''
        Generating control strategy and training model based on current flow information    
        input:
            actq: the infomation of active flows
            cptq: the infomation fo completed flows     
        '''
        #state
        state = self.get_state(actq, cptq)

        #get action
        action = self.agent.egreedy_action(state) # e-greedy action for train

        #reward
        current_throughout = self.throughout(cptq)
        if self.last_througout == 0:
            if current_throughout == 0:
                reward = 0
            else:
                reward = 1 
        else:
            reward = current_throughout/self.last_througout
            if reward > 1:
                # (0, 1) U (1, +)
                reward = reward / 10
            else:
                # (-1, 0)
                reward = reward - 1

        done = False

        #train
        self.agent.perceive(self.last_state,self.last_action,reward,state,done)

        #record state action and throughout
        self.last_state = state
        self.last_action = action
        self.last_througout = current_throughout

        #analyzing the meaning of actions
        ret = self.actionparser(action)
        infostr = self.getinfo(state,action,reward)

        return ret,infostr


    def throughout(self, cptq):
        '''
        Computing the bandwidth of the completed flows
        Input:
            cptq: the infomation of completed flows
        '''
        res = 0.0
        for index, row in cptq.iterrows():
            res += row['size'] / row['duration']
        return res

    #this has been changed need to update
    def get_state(self, actq, cptq):
        '''
        Converting the active and completed flows information to a 1*136 state space
        Intput:
            actq: the infomation of active flows
            cptq: the infomation fo completed flows
        '''
        temp = actq.sort_values(by='sentsize')
        active_num = NUM_A
        finished_num = NUM_F
        state = np.zeros(active_num*6+finished_num*7, dtype = np.int)
        i = 0 
        self.key = []
        self.qindex_list = []
        for index, row in temp.iterrows():
            if i > active_num:
                break
            else:
                state[6*i] = row['src']
                state[6*i + 1] = row['dst']
                state[6*i + 2] = row['protocol']
                state[6*i + 3] = row['sp']
                state[6*i + 4] = row['dp']
                state[6*i + 5] = row['priority']
                self.key.append(index)
                self.qindex_list.append(row['qindex'])
            i += 1
        i = active_num
        for index, row in cptq.iterrows():
                state[6*active_num+7*(i-active_num)] = row['src']
                state[6*active_num+7*(i-active_num)+1] = row['dst']
                state[6*active_num+7*(i-active_num)+2] = row['protocol']
                state[6*active_num+7*(i-active_num)+3] = row['sp']
                state[6*active_num+7*(i-active_num)+4] = row['dp']
                state[6*active_num+7*(i-active_num)+5] = row['duration']
                state[6*active_num+7*(i-active_num)+6] = row['size']
                i += 1
        return state
    
    def actionparser(self, action):
        '''
        Converting 11-bit integer to control information
        Input:
            action: 11-bit integer as action
        '''
        bstr = ('{:0%sb}'%(NUM_A)).format(action)
        res = {}
        for i in range(len(self.key)):
            res[self.key[i]] = int(bstr[-1-i])
        return res

    def getinfo(self, state, action, reward):
        '''
        Generating the log info of this time training
        Input:
            state: state space
            action: action space
            reward: current reward
        '''
        infostr = ''
        line = '%50s\n'%(50*'*')
        rewardstr = 'Evaluation Reward: %f\n'%reward
        policy = 'State and action:\n'
        bstr = ('{:0%sb}'%(NUM_A)).format(action)
        for i in range(NUM_A):
            if i >= len(self.key):
                break
            else:
                policy += 'Queue index:%d, Five tuple={%d,%d,%d,%d,%d}, priority: %d, action:%s\n'%                           (self.qindex_list[i], state[6*i],state[6*i+1],state[6*i+2],state[6*i+3],
                                state[6*i+4],state[6*i+5],bstr[-1-i])
        infostr = line + rewardstr + policy + line
        return infostr 

class DDQNCS():
    M = 5       #max coflow number to scheduler
    size_per_line = 4   #the size of each state line
    s_dim = size_per_line*M #size of state space  
    a_dim = M   #size of action space
    def __init__(self):
        self.agent = DDQN(self.s_dim, self.a_dim)   #DDQN network
        self.last_state = np.zeros(self.s_dim, dtype = np.float)  #the state of last train
        self.last_action = 0        #the action of last train
        self.last_reward = 0        #the reward of last train
        self.scheduler_list = []    #the list of coflows' index wating for scheduling of this train
        self.cycle_count = 0             #Episode continuous cycles
        self.counter = 0            #Episode counter
        self.corrector_count = 0    #count the wrong action for correcting

        ##additional arguments for reward
        self.last_avg_duration = 1  #the average coflow duration in last cycle
    
    def train(self, actq, cptq, coflowinfo, done):
        #if one episode completed
        if done:
            info = 'Episode %d completed: total cycles : %d\n'%(self.counter, self.cycle_count)
            self.counter += 1
            self.cycle_count = 0
            return {}, info

        #get state
        state, coflow_list = self.get_state(coflowinfo)
        #if there are no coflows in this cycle, return
        if len(self.scheduler_list) == 0 :
            return {},''

        #generate action
        action = self.agent.act(state)
        if action >= len(self.scheduler_list):
            choice_index = -1
        else:
            choice_index = self.scheduler_list[action]

        # #reward according to scheduler list length
        # reward = 0 - len(self.scheduler_list)

        #according to duration
        avg_duration = self.get_avg_duration(state)
        if avg_duration == 0:
            reward = 1 + self.last_reward
        else:
            reward = self.get_reward(avg_duration) + self.last_reward

        #fix reward 
        #punishment
        if choice_index == -1:
            self.last_reward = -10
            self.corrector_count += 1
            #correct the action if it is always wrong for ten times
            if self.corrector_count > 10:
                action = np.random.choice(len(self.scheduler_list))
                choice_index = self.scheduler_list[action]
                self.corrector_count = 0
        else:
            self.last_reward = 0
            self.corrector_count = 0

        #train model
        self.agent.remember(self.last_state, self.last_action, state, reward)
        self.agent.train()

        #update saved parmeter
        self.last_state = state
        self.last_action = action
        self.cycle_count += 1
        self.last_avg_duration = avg_duration

        
        #make return parmeter
        ret = self.get_action(coflow_list, choice_index)
        info = 'Cycle: %d , reward: %.2f , choice_index : %d\n'%(self.cycle_count, reward, choice_index)
        #info = ''
        #info = self.get_info(state, choice_index, reward, info)
        return ret, info


    def get_state(self, coflowinfo):
        self.scheduler_list = []
        coflow_list = []
        state = np.zeros(self.s_dim, dtype = np.float)
        for i in range(len(coflowinfo)):
            row = coflowinfo[i]
            if i < self.M:
                state[self.size_per_line*i] = row['duration']/1000          #unit: s
                state[self.size_per_line*i + 1] = row['sentsize']/1000000   #unit: Mb
                state[self.size_per_line*i + 2] = row['count']
                state[self.size_per_line*i + 3] = row['total_count']
                self.scheduler_list.append(row['index'])
            coflow_list.append(row['index'])
        return state, coflow_list

    def get_reward(self, avg_duration):
        difference = self.last_avg_duration - avg_duration + 1.1
        if difference <= 0:
            # print(difference)
            reward = -1
        else:
            reward = np.log10(difference)
        return reward

    def get_action(self, coflow_list, choice_index):
        value = [0]*len(coflow_list)
        res = dict(zip(coflow_list,value))
        if choice_index != -1:
            res[choice_index] = 1
        return res 

    def get_info(self, state, choice_index, reward, info):
        '''
        Generating the log info of this time training
        Input:
            state: state space
            choice_index: the choice coflow index
            reward: current reward
            info: extra input info 
        '''
        infostr = ''
        line = '%50s\n'%(50*'*')
        rewardstr = 'Evaluation Reward: %f\n'%reward
        policy = 'State:\n'
        for i in range(len(self.scheduler_list)):
            policy += 'Coflow_index:%d, coflow_duration: %.0f s, sent_size: %.2f Mb, active_flow_count: %.0f , total_flow_count: %d\n'%(self.scheduler_list[i], state[self.size_per_line*i], state[self.size_per_line*i+1], state[self.size_per_line*i+2], state[self.size_per_line*i+3])
        policy += 'Action:\nChoice coflow index: %d\n'%choice_index
            
        infostr = line + rewardstr + policy + info + line
        return infostr 
    
    def get_avg_duration(self,state):
        """
        A way to calculate the average duration of coflows in scheduler list
        Parameters
        -----------------
            state : array
                the state of this cycle
        Returns
        -----------------
            ret : float

        """
        total_duration = 0
        for i in range(len(self.scheduler_list)):
            duration = state[self.size_per_line*i]
            total_duration += duration
        ret = total_duration / self.M
        return ret

