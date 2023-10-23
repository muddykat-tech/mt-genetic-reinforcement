import copy
import gc
import random
import threading
import time
from collections import namedtuple, deque
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime
from functools import reduce
from typing import Callable

import numpy as np
import torch

import matplotlib.pyplot as plt
from environment.util import LoadingLog
from ga.components.Individuals import CNNIndividual
from ga.util.MarioGAUtil import statistics
from nn.setup import AgentParameters


def calculate_fitness_in_thread(index, p, levels, logger, render):
    p.calculate_fitness(levels, logger, render, index)



class Population:
    def __init__(self, population_settings, replay_memory):
        self.population_settings = population_settings
        self.old_population = []

        # Initialize temp population variables
        generic_population = []
        reinforcement_population = []
        seed_population = []

        # Setup all instances of a generic agent
        generic_agent_settings = population_settings['agent-generic']
        if generic_agent_settings is not None:
            generic_agent = generic_agent_settings[1]
            generic_population = [generic_agent(generic_agent_settings[2], replay_memory) for _ in
                                  range(generic_agent_settings[0])]

        reinforcement_agent_settings = population_settings['agent-reinforcement']
        if reinforcement_agent_settings is not None:
            reinforcement_agent = reinforcement_agent_settings[1]  # Keep agent default settings
            reinforcement_population = [reinforcement_agent(reinforcement_agent_settings[2], replay_memory) for _ in
                                        range(reinforcement_agent_settings[0])]

        seed_agent_names = population_settings['seed-agents']
        if seed_agent_names is not None:
            for name in seed_agent_names:
                model = CNNIndividual(AgentParameters.MarioCudaAgent().agent_parameters, replay_memory)
                model.nn.load('../../models/seed_agents/' + name + '.npy')
                seed_population.append(model)

        self.old_population = generic_population + reinforcement_population + seed_population
        self.population_size = len(self.old_population)
        self.new_population = [None for i in range(len(self.old_population))]

        # Setting hyperparameters for ga:
        self.p_mutation = population_settings['p_mutation']
        self.n_generations = population_settings['n_generations']
        self.p_crossover = population_settings['p_crossover']
        self.batch_size = reinforcement_agent_settings[2]['batch_size']

        # Section for Data Logging

        # Setting up the print logger
        self.logger = LoadingLog.PrintLoader(self.n_generations, '#')
        self.logger.reset()

        # Setting up the structure for the output graph
        self.generic_x_axis = []  # Generation No
        self.generic_y_axis = []  # Fitness No
        self.reinforcement_x_axis = []  # Generation No
        self.reinforcement_y_axis = []  # Fitness No

    def set_population(self, population: list):
        self.old_population = population

    def update_old_population(self):
        # Move tensors from GPU to CPU to release GPU memory
        self.old_population = [agent.nn.to(torch.device('cpu')) for agent in self.old_population]
        self.old_population = copy.deepcopy(self.new_population)

        # Release all unused GPU memory cache
        torch.cuda.empty_cache()

        # And manually Trigger the garbage collector
        gc.collect()

    def get_best_model_parameters(self) -> np.array:
        return sorted(self.new_population, key=lambda ind: ind.fitness, reverse=True)[0]

    def save_model_parameters(self, output_folder, iterations, save_as_pytorch=False, specific_model=None):
        best_model = self.get_best_model_parameters() if specific_model is None else specific_model
        file_name = self.get_file_name(self.now()) + f'_I={iterations}_SCORE={best_model.fitness}.npy'
        output_filename = output_folder + '-' + file_name
        if save_as_pytorch:
            torch.save(best_model.weights_biases, output_filename)
        else:
            np.save(output_filename, best_model.weights_biases)

    def get_file_name(self, date):
        return '{}_NN={}_POPSIZE={}_GEN={}_PMUTATION_{}_PCROSSOVER_{}_BATCH_SIZE={}_'.format(date,
                                                                                             self.new_population[
                                                                                                 0].__class__.__name__,
                                                                                             self.population_size,
                                                                                             self.n_generations,
                                                                                             self.p_mutation,
                                                                                             self.p_crossover,
                                                                                             self.batch_size)

    def run(self, levels, run_generation: Callable, output_folder=None, replay_memory=None):
        best_individual = sorted(self.old_population, key=lambda ind: ind.fitness, reverse=True)[0]
        logger = self.logger
        render = self.population_settings['render_mode']
        generations = self.population_settings['n_generations']
        use_multithreading = self.population_settings['use_multithreading']
        print('Population Settings: \n' + str(self.population_settings))
        print('Training Model:')
        for i in range(generations):
            logger.print_progress(i)

            self.logger.set_stage_name(f'Evaluating Fitness')
            self.new_population = [None for _ in range(self.population_size)]
            if use_multithreading:
                # rough estimate of 8 times speed improvement!
                self.test_thread_calc(levels, logger, render, self.population_settings['n_threads'])
            else:
                [p.calculate_fitness(levels, logger, render, index) for index, p in enumerate(self.old_population)]

            self.logger.set_stage_name(f'Selecting, Crossing and Mutating')

            run_generation(levels, self.old_population, self.new_population, self.population_settings, logger,
                           use_multithreading)

            self.logger.set_stage_name(f'Updating Old Population')

            self.update_old_population()

            new_best_individual = self.get_best_model_parameters()

            l_avg = reduce(lambda total, agent: total + agent.fitness, self.old_population, 0) / len(
                self.old_population)

            self.generic_x_axis.append(i)
            self.generic_y_axis.append(l_avg)

            if new_best_individual.fitness > best_individual.fitness:
                best_individual = new_best_individual

        if len(self.generic_x_axis) > 0:
            population_steps_done = sum(individual.steps_done for individual in self.old_population)
            plt.plot(self.generic_x_axis, self.generic_y_axis, color='red', marker='o')
            plt.title('Fitness of Population Over Time')
            plt.xlabel('Generation')
            plt.ylabel('Mean Fitness')
            legend_info = f'Steps Taken: {population_steps_done}\nPopulation: {len(self.old_population)}'
            plt.legend([legend_info], loc='upper left', fontsize=10)
            plt.grid(True)
            plt.savefig('../../graphs/Generic-' + self.get_file_name(self.now()) + '.png')

        print('')
        print('Saving best model in current pop')
        self.save_model_parameters(output_folder, 0, save_as_pytorch=False)
        print('Saving best model of all time - with fitness: {}'.format(best_individual.fitness))
        self.save_model_parameters(output_folder, 0, save_as_pytorch=False, specific_model=best_individual)

    def show_stats(self, n_gen):
        mean, min, max = statistics(self.new_population)
        date = self.now()
        stats = f"{date} - generation {n_gen + 1} | mean: {mean}\tmin: {min}\tmax: {max}\n"
        print('')
        print(stats)

    @staticmethod
    def now():
        return datetime.now().strftime('%m-%d-%Y_%H-%M')

    def test_thread_calc(self, levels, logger, render, num_threads):
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            [executor.submit(calculate_fitness_in_thread, index, p, levels, logger, render) for index, p in
             enumerate(self.old_population)]
