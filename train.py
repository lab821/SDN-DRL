from mlfq_gym import MLFQEnv
from algorithms.ddpg import DDPG
import numpy as np

env = MLFQEnv()
s_dim = env.observation_space.shape[0]
a_dim = env.action_space.shape[0]
low = env.action_space.low
high = env.action_space.high
## transform [low, high] to [-(high-low)/2, (high-low)/2]
## baseline is (high+low)/2
a_bound = (high-low)/2 
bl = (high+low)/2

agent = DDPG(a_dim, s_dim, a_bound)

var = 30  # control exploration
s = env.reset()

with open("log/train_log.txt", "w") as logger:
    while True:
        a = agent.choose_action(s)
        # add randomness to action
        a = np.clip(np.random.normal(a, var), -a_bound, a_bound)+bl
        aint = [int(i) for i in a.tolist()] ## to [int, int, ...]
        aint = [1e10]
        s_, r, done, info = env.step(aint)
        agent.store_transition(s, a, r, s_)
        
        if agent.pointer > agent.MEMORY_CAPACITY:
            var *= 0.9995      # decay the action randomness
            agent.learn()
        s = s_
        logger.write("reward: "+str(r)+" action: "+aint.__str__()+"\n")
        logger.flush()


# print("ok")
# print("hello")