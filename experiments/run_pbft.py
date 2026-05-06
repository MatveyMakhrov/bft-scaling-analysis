import sys
import os

# Добавляем корень проекта в PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import simpy
from simulator.network import Network
from simulator.metrics import Metrics
from protocols.pbft import PBFTNode

# ===========================
# Настройки эксперимента
# ===========================
N = 4        # количество узлов
F = 1        # число Byzantine узлов
SIM_TIME = 1000  # симуляция в "тайм-единицах"

# ===========================
# Инициализация среды и объектов
# ===========================
env = simpy.Environment()
metrics = Metrics()
network = Network(env, metrics, delay_mean=10)  # задержка сообщений

# Создание узлов PBFT
nodes = []
for i in range(N):
    node = PBFTNode(env, i, network, metrics, N, F)
    network.register(node)
    env.process(node.run())
    nodes.append(node)

# Запуск раунда
for node in nodes:
    node.start_round()

# ===========================
# Запуск симуляции
# ===========================
env.run(until=SIM_TIME)

# ===========================
# Вывод результатов
# ===========================
print(metrics.summary())
