import pandas as pd
import numpy as np

# -----------------------------
# Загрузка данных
# -----------------------------
df = pd.read_csv("/Users/a./source/repos/bft-scaling-analysis/bft_results.csv")

# Оставляем только n=256
df_256 = df[df["num_nodes"] == 256].copy()
df_256 = df_256.set_index("protocol")

# Три метрики
# Q (messages_sent)  — минимизация (меньше = лучше)
# t (avg_round_time) — минимизация (меньше = лучше)
# τ (throughput)     — максимизация (больше = лучше)
metrics = ["messages_sent", "avg_round_time", "throughput"]
directions = ["min", "min", "max"]  # направление оптимизации

X = df_256[metrics].values.astype(float)
protocols = df_256.index.tolist()

print("=" * 55)
print("TOPSIS — сравнительная оценка масштабируемости (n=256)")
print("=" * 55)

# -----------------------------
# Шаг 1 — Нормализация
# -----------------------------
norm = np.sqrt((X ** 2).sum(axis=0))   # знаменатель: sqrt(Σ x²_pj)
R = X / norm                            # r_pj = x_pj / sqrt(Σ x²_pj)

# -----------------------------
# Шаг 2 — Взвешивание (равные веса w_j = 1/3)
# -----------------------------
w = np.array([1/3, 1/3, 1/3])
V = R * w                               # v_pj = w_j * r_pj

# -----------------------------
# Шаг 3 — Идеальное A+ и антиидеальное A-
# -----------------------------
A_plus = np.zeros(len(metrics))
A_minus = np.zeros(len(metrics))

for j, direction in enumerate(directions):
    if direction == "min":
        A_plus[j]  = V[:, j].min()     # идеал: наименьшее значение
        A_minus[j] = V[:, j].max()     # антиидеал: наибольшее значение
    else:
        A_plus[j]  = V[:, j].max()     # идеал: наибольшее значение
        A_minus[j] = V[:, j].min()     # антиидеал: наименьшее значение

# -----------------------------
# Шаг 4 — Евклидовы расстояния
# -----------------------------
D_plus  = np.sqrt(((V - A_plus)  ** 2).sum(axis=1))   # до идеала
D_minus = np.sqrt(((V - A_minus) ** 2).sum(axis=1))   # до антиидеала

# -----------------------------
# Шаг 5 — Индекс близости C_p
# -----------------------------
C = D_minus / (D_plus + D_minus)

# -----------------------------
# Вывод результатов
# -----------------------------
results = pd.DataFrame({
    "Протокол":   protocols,
    "Q (сообщ.)": df_256["messages_sent"].values.astype(int),
    "t (вр. раунда)": df_256["avg_round_time"].round(2).values,
    "τ (пропускн.)":  df_256["throughput"].round(3).values,
    "D+":  D_plus.round(4),
    "D-":  D_minus.round(4),
    "C_p": C.round(4),
}).sort_values("C_p", ascending=False).reset_index(drop=True)

results.index += 1  # нумерация с 1
print(results.to_string())

print()
print("Рейтинг масштабируемости (C_p ближе к 1 = лучше):")
for rank, row in results.iterrows():
    print(f"  {rank}. {row['Протокол']:<18} C_p = {row['C_p']:.4f}")