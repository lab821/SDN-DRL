from algorithms.dqn import DQN
import gym
from auto_gym import AutoEnv, AutoSpace
import numpy as np
# ---------------------------------------------------------
# Hyper Parameters
ENV_NAME = 'CartPole-v0'
EPISODE = 3000 # Episode limitation
STEP = 300 # Step limitation in an episode
TEST = 10 # The number of experiment test every 100 episode

NUM_ACTIVE = AutoEnv.NUM_ACTIVE
NUM_FINISHED = AutoEnv.NUM_FINISHED

def toMeterList(n, content):
    assert (type(n) == int) or (type(n) == np.int64), "Type Assert: %s, please input type int of n!"%(type(n))
    meter_l = []
    for _ in range(NUM_ACTIVE):
        meter_l.append(content[n%2])
        n = n//2
    return meter_l

def genAction(state, meter_l):
    action = []
    for i in range(NUM_ACTIVE):
        a = state[6*i:6*(i+1)-1].tolist()
        a.append(meter_l[i])
        action.append(a)
    return action

def main():
  # initialize OpenAI Gym env and dqn agent
#   env = gym.make(ENV_NAME)
  env = AutoEnv()
  agent = DQN(env)

  for episode in range(EPISODE):
    # initialize task
    state = env.reset()
    # Train
    for step in range(STEP):
      action = agent.egreedy_action(state) # e-greedy action for train
      print(action)
      print(toMeterList(action, env.action_space.content))
      meter_l = toMeterList(action, env.action_space.content)
      n_action = genAction(state, meter_l)
      next_state,reward,done,_ = env.step(n_action)
      print("State:", state)
      print("Next State: ", next_state)
      print("Reward: ", reward)
      # Define reward for agent
      reward = -1 if done else 0.1
      agent.perceive(state,action,reward,next_state,done)
      state = next_state
      if done:
        break
    # Test every 100 episodes
    if episode % 100 == 0:
      total_reward = 0
      for i in range(TEST):
        state = env.reset()
        for j in range(STEP):
        #   env.render()
          action = agent.action(state) # direct action for test
          state,reward,done,_ = env.step(action)
          total_reward += reward
          if done:
            break
      ave_reward = total_reward/TEST
      print ('episode: ',episode,'Evaluation Average Reward:',ave_reward)

if __name__ == '__main__':
    main()