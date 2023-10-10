import copy
import math
import time

import gym
import numpy as np
from matplotlib import pyplot as plt

from environment import MarioEnvironment
from environment.util import LoadingLog
from ga.components.Individuals import CNNIndividual, ReinforcementCNNIndividual
from ga.components.Population import Population
from ga.util import MarioGAUtil
from ga.util.ReplayMemory import ReplayMemory
from nn.setup import AgentParameters

env = MarioEnvironment.create_mario_environment_random()

# Setup Population Settings for Genetic Algorithm Training. (Move this to a specified settings script)
population_settings = {}

population_settings['agent-reinforcement'] = [0, ReinforcementCNNIndividual,
                                              AgentParameters.MarioCudaAgent().agent_parameters]
population_settings['agent-generic'] = [98, CNNIndividual, AgentParameters.MarioCudaAgent().agent_parameters]
population_settings['seed-agents'] = ["Mario_1_1_6225000", "Mario_2_1_9925000", "Mario_3_1_10000000", "Mario_4_1_9950000"]
population_settings['p_mutation'] = 0.05
population_settings['p_crossover'] = 0.8
population_settings['n_generations'] = 50
population_settings['render_mode'] = 0

param = AgentParameters.MarioCudaAgent()
replay_memory = ReplayMemory(param.agent_parameters['memory_size'])

population = Population(population_settings, replay_memory)
population.run(env, MarioGAUtil.generation, '../../models/')

