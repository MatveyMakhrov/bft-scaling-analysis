import random
import simpy

class Network:
    def __init__(self, env, metrics, delay_mean=50):
        self.env = env
        self.metrics = metrics
        self.delay_mean = delay_mean
        self.nodes = {}

    def register(self, node):
        self.nodes[node.node_id] = node

    def send(self, src, dst, message):
        delay = random.expovariate(1 / self.delay_mean)
        yield self.env.timeout(delay)
        yield self.nodes[dst].inbox.put((src, message))
