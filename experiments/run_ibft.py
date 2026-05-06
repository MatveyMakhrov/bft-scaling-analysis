import sys
import os

# Добавляем корень проекта в PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import simpy
from simulator.network import Network
from simulator.metrics import Metrics
from protocols.ibft import IBFTNode

# Параметры эксперимента
NUM_NODES = 4
F = 1
ROUND_DELAY = 10

# Инициализация симулятора
env = simpy.Environment()
metrics = Metrics()
network = Network(env, metrics, delay_mean=ROUND_DELAY)

# Создание узлов
nodes = []
for i in range(NUM_NODES):
    node = IBFTNode(env, i, network, metrics, NUM_NODES, F)
    network.nodes[i] = node
    nodes.append(node)
    env.process(node.run())

# Запуск раундов
for node in nodes:
    node.start_round()

# Симуляция
SIMULATION_TIME = 1000
env.run(until=SIMULATION_TIME)

# Вывод метрик
print(metrics.summary())