from gym import Env, spaces
import numpy as np
import random
import pdb
from time import sleep
from info_module import FlowCollector, Logger

logger = Logger('log/log.txt')

class MLFQEnv(Env):
    """
    NUM_ACTIVE: when the number of active flows is more than NUM_ACTIVE, select the top NUM_ACTIVE of active flows as the state, sorted by the byte that have been sent.
    NUM_FINISHED: when the number of finished flows is more than NUM_FINISHED, select the top NUM_FINISHED of finished flows as the state, sorted by the size of finished flow.
    """
    # NUM_ACTIVE = 11
    # NUM_FINISHED = 10
    NUM_ACTIVE = 5
    NUM_FINISHED = 5
    NUM_THRESHOLD = FlowCollector.num_level-1

    # MAX_F = float('inf')
    # MAX_F = float(10**10)
    MAX_F = 10

    def __init__(self):
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, dtype=np.int, shape=(self.NUM_ACTIVE*6+self.NUM_FINISHED*7,))
        # self.action_space = AutoSpace()
        self.action_space = spaces.Box(0, 1e10, shape=(self.NUM_THRESHOLD,), dtype=np.int)

        self.collector = FlowCollector(logger)
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

        Action: [thresholds], length is NUM_LEVEL-1
        """
        # *********** Apply Action ***************
        # print("step-action: ", action)
        # self.collector.action_apply(action)
        assert type(action)==list and len(action)==self.NUM_THRESHOLD, "action is not legal!"
        self.collector.change_threshold(action)
        """
        Flow format
        active flow: {flow : {priority, active_time, active_size}}
        finished flow: {flow : {fct, size}}
        """
        active_flows, finished_flows = self.collector.flow_collect()
        # *********** State ***************
        observation = []
        for attr in active_flows[:self.NUM_ACTIVE]:
            observation.extend(attr[:5])
            observation.extend((attr[5],))
        for _ in range(self.NUM_ACTIVE-len(active_flows)):
            # padding
            observation.extend([0]*6)
        
        for attr in finished_flows[:self.NUM_FINISHED]:
            observation.extend(attr)
        for _ in range(self.NUM_FINISHED-len(finished_flows)):
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
                reward = self.MAX_F
        else:
            reward = throughout / self.old_throughout
        if reward > self.MAX_F:
            reward = self.MAX_F
        self.old_throughout = throughout
        done = False
        return np.array(observation), reward, done, {}

    def render(self, mode='human'):
        pass
        raiseNotImplementedError("Method render not implemented!")

    def close(self):
        # self.net.stop()
        # self.net.stopXterms()
        print("Done with destroying myself.")

if __name__ == "__main__":
    env = MLFQEnv()
    obs = env.reset()
    while True:
        action = env.action_space.sample().tolist()
        print(action)
        obs, reward, done, _ = env.step(action)
        print(obs)