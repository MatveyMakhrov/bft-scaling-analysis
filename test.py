import matplotlib.pyplot as plt

# Количество узлов
nodes = [1, 4, 8, 16]

# Среднее время раунда (из второго графика)
avg_round_time = {
    "PBFT": [30, 24, 28, 35],
    "HotStuff": [27, 36, 30, 31],
    "HoneyBadgerBFT": [0, 60, 30, 30],
    "IBFT": [10, 39, 29, 32],
    "Tendermint": [90, 40, 28, 41],
    "RBFT": [36, 46, 37, 52],
}

# Цвета (те же, что использует matplotlib по умолчанию)
colors = {
    "PBFT": "tab:blue",
    "HotStuff": "tab:orange",
    "HoneyBadgerBFT": "tab:green",
    "IBFT": "tab:red",
    "Tendermint": "tab:purple",
    "RBFT": "tab:brown",
}

# Пропускная способность T = 1 / avg_round_time
throughput = {
    protocol: [1 / t if t > 0 else 0 for t in times]
    for protocol, times in avg_round_time.items()
}

# Построение графика
plt.figure(figsize=(8, 5))

for protocol, values in throughput.items():
    plt.plot(
        nodes,
        values,
        marker="o",
        label=protocol,
        color=colors[protocol]
    )

plt.title("Пропускная способность протоколов")
plt.xlabel("Количество узлов")
plt.ylabel("Пропускная способность (раундов / единицу времени)")
plt.grid(True)
plt.legend(title="protocol")
plt.tight_layout()
plt.show()
