import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import simpy
from simulator.network import Network
from simulator.metrics import Metrics
from protocols.rbft import RBFTNode

NUM_NODES = 4
F = 1
ROUND_DELAY = 10

env = simpy.Environment()
metrics = Metrics()
network = Network(env, metrics, delay_mean=ROUND_DELAY)

nodes = []
for i in range(NUM_NODES):
    node = RBFTNode(env, i, network, metrics, NUM_NODES, F)
    network.nodes[i] = node
    nodes.append(node)
    env.process(node.run())

for node in nodes:
    node.start_round()

SIMULATION_TIME = 1000
env.run(until=SIMULATION_TIME)

print(metrics.summary())
