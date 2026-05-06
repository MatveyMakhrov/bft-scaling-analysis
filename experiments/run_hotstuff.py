import sys
import os

# Добавляем корень проекта в PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import simpy
from simulator.network import Network
from simulator.metrics import Metrics
from protocols.hotstuff import HotStuffNode

# ===========================
# Параметры симуляции
# ===========================
NUM_NODES = 4        # Общее число узлов
F = 1                # Число Byzantine узлов (n >= 3f + 1)
DELAY_MEAN = 10      # Средняя задержка сообщений

# ===========================
# Настройка среды и компонентов
# ===========================
env = simpy.Environment()
metrics = Metrics()
network = Network(env, metrics, delay_mean=DELAY_MEAN)

# Создаём узлы
nodes = []
for i in range(NUM_NODES):
    node = HotStuffNode(env, i, network, metrics, NUM_NODES, F)
    nodes.append(node)
    network.register(node)
    env.process(node.run())

# ===========================
# Запуск раунда
# ===========================
for node in nodes:
    node.start_round()

# ===========================
# Запуск симуляции
# ===========================
SIM_TIME = 1000
env.run(until=SIM_TIME)

# ===========================
# Вывод результатов
# ===========================
print(metrics.summary())
