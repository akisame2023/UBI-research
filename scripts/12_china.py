# -*- coding: utf-8 -*-
"""
中国专章分析: 方案成本、基础养老金提标对比、融资菜单、老龄化
输出: data/processed/11_china_ubi.csv + figures/fig12_china.png
核验常数见 sources/facts_china_verified.md
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import norm
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
FIG = ROOT / "figures"
plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False, "text.parse_math": False,
    "figure.dpi": 110, "savefig.dpi": 300,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "font.size": 10.5,
})
C = {"blue": "#2C6E9B", "red": "#C04A3E", "green": "#3E8E5A", "orange": "#E08A3C",
     "gray": "#7F8C99", "purple": "#7B5AA6", "lblue": "#8FB8D4", "lred": "#E0A49B"}

GDP = 134.9e12       # 2024 名义 GDP (¥)
POP = 1.409e9
GINI = 0.36          # WDI 2022 = 36.0
RECIPIENTS = 1.804e8 # 城乡居民养老保险实际领取者 (2024 末, 人社部)
FLOOR_2024, FLOOR_2025 = 123, 143   # 中央基础养老金最低标准 元/月
CO2_CHN = 12.6e9     # 吨 (OWID 中国 CO2, ~2023)

def k_gini(g):
    s = np.sqrt(2) * norm.ppf((1 + g) / 2)
    z = np.linspace(1e-6, 15, 400000)
    my, sy = -s**2 / 2, s
    dens = np.exp(-(np.log(z) - my) ** 2 / (2 * sy ** 2)) / (z * sy * np.sqrt(2 * np.pi))
    return np.trapezoid(np.maximum(0, 1 - z) * dens, z)

K = k_gini(GINI)
print(f"k(Gini={GINI}) = {K:.3f}")

rows = []
for m in [200, 500, 1000]:
    gross = m * 12 * POP
    pct = 100 * gross / GDP
    rural_share = 100 * (m * 12) / 21691   # 农村人均可支配收入 2023
    urban_share = 100 * (m * 12) / 51821
    rows.append({"方案": f"¥{m}/月", "毛成本万亿": gross / 1e12, "毛成本%GDP": pct,
                 "含行为+15%": pct * 1.15, "净转移%GDP": pct * K,
                 "占农村人均可支配%": rural_share, "占城镇人均可支配%": urban_share})
# 基础养老金提标
for target, base, yr in [(500, FLOOR_2024, "2024线"), (1000, FLOOR_2024, "2024线"), (500, FLOOR_2025, "2025线")]:
    cost = (target - base) * 12 * RECIPIENTS
    rows.append({"方案": f"基础养老金{base}→{target}(仅{RECIPIENTS/1e8:.1f}亿领取者)",
                 "毛成本万亿": cost / 1e12, "毛成本%GDP": 100 * cost / GDP,
                 "含行为+15%": np.nan, "净转移%GDP": np.nan,
                 "占农村人均可支配%": np.nan, "占城镇人均可支配%": np.nan})
# 融资菜单
menu = [
    ("碳税 ¥100/吨", 12.6e9 * 100 / GDP * 100),
    ("碳税 $75/吨(≈¥535)", 12.6e9 * 535 / GDP * 100),
    ("国企利润上缴 +10pp", 0.46e12 / GDP * 100),
    ("数据分红上界(全球)", 0.5),
]
for name, v in menu:
    rows.append({"方案": f"[融资] {name}", "毛成本万亿": np.nan, "毛成本%GDP": v,
                 "含行为+15%": np.nan, "净转移%GDP": np.nan,
                 "占农村人均可支配%": np.nan, "占城镇人均可支配%": np.nan})
df = pd.DataFrame(rows)
df.to_csv(OUT / "11_china_ubi.csv", index=False)
print(df.round(2).to_string(index=False))

# ---------------------------------------------------------------- fig12
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1.25, 1]})
labels = ["¥200/月\n全民", "¥500/月\n全民", "¥1000/月\n全民", "基础养老金\n123→500元/月", "基础养老金\n123→1000元/月"]
vals = [2.51, 6.27, 12.53, 0.60, 1.41]
cols = [C["blue"], C["orange"], C["red"], C["green"], C["green"]]
b = ax1.bar(range(5), vals, color=cols, width=0.6)
for i, v in enumerate(vals):
    ax1.text(i, v + 0.12, f"{v:.2f}%", ha="center", fontsize=10, fontweight="bold")
ax1.set_xticks(range(5))
ax1.set_xticklabels(labels, fontsize=9)
ax1.set_ylabel("毛成本, % 2024 年 GDP")
ax1.set_title("方案成本: 全民 UBI vs 提标现有\"近普惠地板\"", fontsize=10.5)
ax1.set_ylim(0, 14)

menu_l = ["碳税¥100/吨", "碳税$75/吨", "国企分红+10pp", "数据分红上界"]
menu_v = [0.93, 5.00, 0.34, 0.50]
x = np.arange(4)
ax2.bar(x - 0.19, [0.93, 5.00, 0.34, 0.50], width=0.38, color=C["purple"], label="可动员财源 %GDP")
ax2.bar(x + 0.19, [1.55, 1.55, 1.55, 1.55], width=0.38, color=C["green"], alpha=0.75,
        label="¥500/月 UBI 净转移需求 (1.55%)")
for i, v in enumerate([0.93, 5.00, 0.34, 0.50]):
    ax2.text(i - 0.19, v + 0.08, f"{v:.2f}", ha="center", fontsize=9, fontweight="bold")
ax2.text(3 + 0.19, 1.63, "1.55", ha="center", fontsize=9, color=C["green"])
ax2.set_xticks(x); ax2.set_xticklabels(menu_l, fontsize=9)
ax2.set_ylabel("% GDP")
ax2.set_ylim(0, 5.6)
ax2.set_title("融资菜单 vs ¥500 方案的净转移需求", fontsize=10.5)
ax2.legend(frameon=False, fontsize=8.5)
fig.suptitle("图 12 | 中国: \"¥500/月 全民 UBI\"毛成本 6.27% GDP、净转移 1.55%; 现实地板是提标城乡居民基础养老金(0.60%)",
             fontsize=11.5, y=1.03)
fig.tight_layout()
fig.savefig(FIG / "fig12_china.png", bbox_inches="tight")
plt.close(fig)
print("fig12 done")
