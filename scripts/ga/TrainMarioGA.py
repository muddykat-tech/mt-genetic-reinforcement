import copy
import math
import time

from matplotlib import pyplot as plt

from environment import MarioEnvironment
from environment.util import LoadingLog
from ga.components.Individuals import CNNIndividual, ReinforcementCNNIndividual
from ga.components.Population import Population
from ga.util import MarioGAUtil
from nn.setup import AgentParameters

env = MarioEnvironment.create_mario_environment()

# Setup Population Settings for Genetic Algorithm Training. (Move this to a specified settings script)
population_settings = {}

population_settings['agent-reinforcement'] = [10, ReinforcementCNNIndividual,
                                              AgentParameters.MarioCudaAgent().agent_parameters]
population_settings['agent-generic'] = [0, CNNIndividual, AgentParameters.MarioCudaAgent().agent_parameters]
population_settings['p_mutation'] = 0.05
population_settings['p_crossover'] = 0.8
population_settings['n_generations'] = 5
population_settings['render_mode'] = 1

# population = Population(population_settings)
# population.run(env, MarioGAUtil.generation, '../../models/')

# Run an agent directly, change it's settings in Agent Parameters.MarioCudaAgent()
# TODO make a separate param for agents
param = AgentParameters.MarioCudaAgent().agent_parameters
logger = LoadingLog.PrintLoader(param.get('experience_episodes'), 'x')
agent = ReinforcementCNNIndividual(AgentParameters.MarioCudaAgent().agent_parameters)
# Ignore 'generation' in the print logger, it's just the same agent running multiple times
agent_x = []  # Timestep
agent_y = []  # Fitness
agent.run_single(env, logger, True, agent_x, agent_y)
plt.plot(agent_x, agent_y, color='blue', marker='o')
plt.title('Fitness of RL over time')
plt.xlabel('time-step')
plt.ylabel('Fitness')
plt.grid(True)
plt.savefig('../../graphs-rl-single/Generic-' + str(time.time()) + '.png')
