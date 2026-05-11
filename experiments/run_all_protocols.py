import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)


import simpy
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from simulator.network import Network
from simulator.metrics import Metrics

# Протоколы
from protocols.pbft import PBFTNode
from protocols.hotstuff import HotStuffNode
from protocols.honeybadger import HBBFTNode
from protocols.ibft import IBFTNode
from protocols.tendermint import TendermintNode
from protocols.rbft import RBFTNode

# -----------------------------
# Настройки эксперимента
# -----------------------------
NUM_NODES_LIST = [4, 8, 16, 32, 64, 128, 256]  # минимум 4 узла (f=1): n=1 не имеет смысла для BFT
FRACTION_BYZANTINE = 1/3           # число допустимых злонамеренных узлов
BATCH_SIZE = 2
ROUND_DELAY = 10
SIMULATION_TIME = 1000

PROTOCOLS = {
    "PBFT": PBFTNode,
    "HotStuff": HotStuffNode,
    "HoneyBadgerBFT": HBBFTNode,
    "IBFT": IBFTNode,
    "Tendermint": TendermintNode,
    "RBFT": RBFTNode
}

# -----------------------------
# Функция запуска симуляции
# -----------------------------
def run_simulation(protocol_cls, num_nodes):
    if num_nodes < 4:
        raise ValueError(
            f"num_nodes={num_nodes} слишком мало для BFT-протокола. "
            f"Минимум 4 узла (даёт f=1 Byzantine-устойчивость). "
            f"При n=1 или n=3: f=0, консенсус вырожден и некорректен."
        )
    env = simpy.Environment()
    f = num_nodes // 3  # допустимые Byzantine узлы
    metrics = Metrics()
    network = Network(env, metrics, delay_mean=ROUND_DELAY)

    # создаём узлы
    nodes = []
    for i in range(num_nodes):
        if protocol_cls is HBBFTNode:
            node = protocol_cls(env, i, network, metrics, num_nodes, f, BATCH_SIZE)
        else:
            node = protocol_cls(env, i, network, metrics, num_nodes, f)
        network.register(node)
        nodes.append(node)
        env.process(node.run())

    # старт раундов
    for node in nodes:
        node.start_round()

    # запуск симуляции
    env.run(until=SIMULATION_TIME)

    # метрики
    summary = metrics.summary()

    # усреднённое время раунда по узлам
    avg_round_time = 0
    round_times = summary.get("round_times", {})
    if round_times:
        all_times = [t for times in round_times.values() for t in times]
        avg_round_time = sum(all_times) / len(all_times)

    return {
        "messages_sent": summary["messages_sent"],
        "messages_received": summary["messages_received"],
        "rounds_finished": summary["rounds_finished"],
        "avg_round_time": avg_round_time, 
        "simulation_time": SIMULATION_TIME
    }


def compute_throughput(metrics_result):
    """
    Throughput = число завершённых консенсусных раундов / время симуляции
    """
    total_rounds = sum(metrics_result["rounds_finished"].values())
    simulation_time = metrics_result["simulation_time"]

    if simulation_time == 0:
        return 0

    return total_rounds / simulation_time

# -----------------------------
# Основной цикл эксперимента
# -----------------------------
results = []

for num_nodes in NUM_NODES_LIST:
    for proto_name, proto_cls in PROTOCOLS.items():
        print(f"Running {proto_name} with {num_nodes} nodes...")
        metrics_result = run_simulation(proto_cls, num_nodes)
        throughput = compute_throughput(metrics_result)
        results.append({
            "protocol": proto_name,
            "num_nodes": num_nodes,
            "throughput": throughput,
            **metrics_result
        })

# -----------------------------
# Сохраняем результаты в CSV
# -----------------------------
df = pd.DataFrame(results)
df.to_csv("bft_results.csv", index=False)
print("Results saved to bft_results.csv")

# -----------------------------
# Визуализация
# -----------------------------
sns.set(style="whitegrid")
plt.figure(figsize=(18, 5))

# Среднее время раунда
plt.subplot(1, 3, 1)
sns.lineplot(data=df, x="num_nodes", y="avg_round_time", hue="protocol", marker="o")
plt.title("Среднее время раунда для разных протоколов")
plt.xlabel("Количество узлов (шт.)")
plt.ylabel("Среднее время раунда (симуляционных единиц)")

# Количество сообщений (логарифмическая шкала — протоколы отличаются на порядки)
plt.subplot(1, 3, 2)
sns.lineplot(data=df, x="num_nodes", y="messages_sent", hue="protocol", marker="o")
plt.yscale("log")
plt.title("Количество отправленных сообщений (log scale)")
plt.xlabel("Количество узлов (шт.)")
plt.ylabel("Число отправленных сообщений (шт., лог. шкала)")

# Пропускная способность
plt.subplot(1, 3, 3)
sns.lineplot(data=df, x="num_nodes", y="throughput", hue="protocol", marker="o")
plt.title("Пропускная способность протоколов")
plt.xlabel("Количество узлов (шт.)")
plt.ylabel("Пропускная способность (раундов / сим. единицу времени)")

plt.tight_layout()
plt.show()