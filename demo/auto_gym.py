from __future__ import print_function
from __future__ import division
# from dumbbell_topo import DumbbellTopo

# from mininet.net import Mininet
# from mininet.node import RemoteController, CPULimitedHost, OVSKernelSwitch
# from mininet.link import TCLink
# from mininet.util import dumpNodeConnections
from gym import Env, spaces
import numpy as np
import random
import pdb
from time import sleep
import socket

from info_module import FlowCollector

MAX_STATE_LEN = 100
FLOW_LEN = 7

class AutoSpace(spaces.Space):
    def __init__(self):
        self.content = [1, 10]
        self.n = len(self.content)
        super(AutoSpace, self).__init__((), np.int64)
    
    def sample(self):
        return random.choice(self.content)

    def contains(self, x):
        if isinstance(x, int):
            as_int = x
        elif isinstance(x, (np.generic, np.ndarray)) and (x.dtype.kind in np.typecodes['AllInteger'] and x.shape == ()):
            as_int = int(x)
        else:
            return False
        return as_int in self.content

    def __repr__(self):
        return "AutoSpace(%s)" % self.content

    def __eq__(self, other):
        return  isinstance(other, AutoSpace)

class AutoEnv(Env):
    """
    NUM_ACTIVE: when the number of active flows is more than NUM_ACTIVE, select the top NUM_ACTIVE of active flows as the state, sorted by the byte that have been sent.
    NUM_FINISHED: when the number of finished flows is more than NUM_FINISHED, select the top NUM_FINISHED of finished flows as the state, sorted by the size of finished flow.
    """
    NUM_ACTIVE = 11
    NUM_FINISHED = 10

    # MAX_F = float('inf')
    # MAX_F = float(10**10)
    MAX_F = 10

    def __init__(self):
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, dtype=np.int, shape=(AutoEnv.NUM_ACTIVE*6+AutoEnv.NUM_FINISHED*7,))
        self.action_space = AutoSpace()

        self.collector = FlowCollector()
        self._start_env()

    def _start_env(self):
        self.old_throughout = 0
        print("Done with initializing myself.")

    def reset(self):
        self.close()
        print("Stopping environment...")
        self._start_env()
        print("Start environment...")
        return np.zeros(self.observation_space.shape)

    def step(self, action):
        """
        State:
        Reward: Supposed throughout = flow size / flow finished time(fct),
        reward is defined as sum up the radio between throughout in time t and throughout in time t-1 every finished flow.

        Action: [[five_tuple, meter_id], ...]
        """
        # *********** Apply Action ***************
        # print("step-action: ", action)
        self.collector.action_apply(action)
        """
        Flow format
        active flow: {flow : {priority, active_time, active_size}}
        finished flow: {flow : {fct, size}}
        """
        active_flows, finished_flows = self.collector.flow_collect()
        # *********** State ***************
        observation = []
        for attr in active_flows[:AutoEnv.NUM_ACTIVE]:
            observation.extend(attr[:5])
            observation.extend((attr[5],))
        for _ in range(AutoEnv.NUM_ACTIVE-len(active_flows)):
            # padding
            observation.extend([0]*6)
        
        for attr in finished_flows[:AutoEnv.NUM_FINISHED]:
            observation.extend(attr)
        for _ in range(AutoEnv.NUM_FINISHED-len(finished_flows)):
            # padding
            observation.extend([0]*7)
        # print(observation, len(observation))
        # *********** Reward **************
        throughout = 0
        for attr in finished_flows:
            fct = attr[5]
            size = attr[6]
            throughout += (size / fct)
        if self.old_throughout == 0:
            if throughout == 0:
                reward = 1
            else:
                reward = AutoEnv.MAX_F
        else:
            reward = throughout / self.old_throughout
        if reward > AutoEnv.MAX_F:
            reward = AutoEnv.MAX_F
        self.old_throughout = throughout
        done = False
        return np.array(observation), reward, done, {}

    def render(self, mode='human'):
        raiseNotImplementedError("Method render not implemented!")

    def close(self):
        # self.net.stop()
        # self.net.stopXterms()
        print("Done with destroying myself.")

def gen_action(state, meter_l):
    assert (
        (type(meter_l) == list or type(meter_l) == tuple) and
        len(meter_l) == (AutoEnv.NUM_ACTIVE)
    ), "Please input `meter_l` with right format."
    assert (
        (type(state) == np.ndarray) and 
        (state.shape == (AutoEnv.NUM_ACTIVE*6+AutoEnv.NUM_FINISHED*7,))
    ), "Please input `state` with right format."
    actions = []
    for i in range(AutoEnv.NUM_ACTIVE):
        action = []
        action.extend(state[i*6:(i+1)*6-1])
        action.extend((meter_l[i],))
        actions.append(action)
    # pre = AutoEnv.NUM_ACTIVE*6
    # for j in range(AutoEnv.NUM_FINISHED):
    #     action = []
    #     action.extend(state[j*7+pre:(j+1)*7-2+pre])
    #     action.extend((meter_l[j+AutoEnv.NUM_ACTIVE],))
    #     actions.append(action)
    print("Action: ")
    for a in actions:
        print(a)
    return actions

def print_state(state):
    print("State: ")
    for s in state:
        print(s)

def print_observation(obs):
    print("Observation: ")
    for i in range(AutoEnv.NUM_ACTIVE):
        print(obs[6*i:6*(i+1)])
    bl = AutoEnv.NUM_ACTIVE*6
    for i in range(AutoEnv.NUM_FINISHED):
        print(obs[bl+7*i:bl+7*(i+1)])

if __name__ == '__main__':
    env = AutoEnv()
    obs = env.reset()
    for i in range(15):
        # meter_l = [random.choice([1, 10]) for _ in range(AutoEnv.NUM_ACTIVE)]
        meter_l = [1 for _ in range(AutoEnv.NUM_ACTIVE)]
        action = gen_action(obs, meter_l)
        obs, reward, done, _ = env.step(action)
        # print("Observation: ", obs)
        print_observation(obs)
        sleep(1)
        # env.step([])