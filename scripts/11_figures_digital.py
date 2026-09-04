# -*- coding: utf-8 -*-
"""子研究图表: fig9 就绪度×财政空间散点, fig10 老龄化挤压, fig11 记分卡热图"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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
     "gray": "#7F8C99", "purple": "#7B5AA6"}

sc = pd.read_csv(OUT / "08_digital_readiness.csv")
scen = pd.read_csv(OUT / "09_ubi_scenarios_digital.csv")
p20 = scen[scen.alpha == 0.20].set_index("iso3")
sc = sc.set_index("iso3")

LABELS = {"DNK": "丹麦", "SWE": "瑞典", "NOR": "挪威", "ISL": "冰岛", "EST": "爱沙尼亚",
          "NLD": "荷兰", "CHE": "瑞士", "FIN": "芬兰", "DEU": "德国", "FRA": "法国",
          "GBR": "英国", "USA": "美国", "CAN": "加拿大", "AUS": "澳大利亚", "JPN": "日本",
          "KOR": "韩国", "SGP": "新加坡", "ARE": "阿联酋", "ESP": "西班牙", "ITA": "意大利",
          "AUT": "奥地利", "PRT": "葡萄牙", "POL": "波兰", "LUX": "卢森堡", "NZL": "新西兰",
          "ISR": "以色列"}

# ================================================================ fig9
fig, ax = plt.subplots(figsize=(9.5, 5.8))
for iso, r in sc.iterrows():
    if iso not in p20.index:
        continue
    x = p20.loc[iso, "net_pct_gdp"]
    y = r.oecd_tax
    if pd.isna(y):
        continue
    socx = r.socx if pd.notna(r.socx) else 20
    ax.scatter(x, y, s=(socx ** 1.6) * 3, color=C["blue"], alpha=0.65,
               edgecolor="white", lw=0.8, zorder=3)
    ax.annotate(LABELS.get(iso, iso), (x, y), xytext=(5, 4),
                textcoords="offset points", fontsize=9)
ax.axvline(5.0, color=C["orange"], ls="--", lw=1.3)
ax.text(5.1, 27, "净增量 = 0\n(假设替换 5% GDP\n现有现金转移)", fontsize=8.5, color=C["orange"])
ax.axhline(33.9, color=C["gray"], ls=":", lw=1.3)
ax.text(2.6, 34.3, "OECD 平均税负 33.9%", fontsize=8.5, color=C["gray"])
ax.set_xlabel("普惠 UBI 净成本, % GDP (α=20% 人均收入; 比例税回收基准)")
ax.set_ylabel("总税收收入, % GDP (OECD 口径 2023)")
ax.set_title("图 9 | 高信息化国家: UBI 净成本 vs 税负空间\n气泡大小=公共社会支出 %GDP; 几乎全部国家位于 5% 净成本线左侧 → 财政上\"可议\"", fontsize=11.5, pad=10)
fig.tight_layout()
fig.savefig(FIG / "fig9_readiness_fiscal_space.png", bbox_inches="tight")
plt.close(fig)
print("fig9 done")

# ================================================================ fig10
sel = ["JPN", "KOR", "ITA", "ESP", "PRT", "FIN", "DEU", "FRA", "DNK", "NLD",
       "CHE", "GBR", "CAN", "AUS", "USA"]
d = sc.loc[[s for s in sel if s in sc.index]].copy()
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5), gridspec_kw={"width_ratios": [1.3, 1]})
x = np.arange(len(d))
ax1.bar(x - 0.2, d.pop65_pct, width=0.4, color=C["blue"], label="65+ 占比 2024 (WDI)")
has50 = d.pop65_2050.notna()
ax1.bar(x[has50] + 0.2, d.pop65_2050[has50], width=0.4, color=C["lred"] if "lred" in C else "#E0A49B",
        label="65+ 占比 2050 (UN/OECD 预测)")
for i, (v, f) in enumerate(zip(d.pop65_pct, d.pop65_2050)):
    if pd.notna(v):
        ax1.text(i - 0.2, v + 0.4, f"{v:.0f}", ha="center", fontsize=8)
    if pd.notna(f):
        ax1.text(i + 0.2, f + 0.4, f"{f:.0f}", ha="center", fontsize=8, color=C["red"])
ax1.set_xticks(x)
ax1.set_xticklabels([LABELS.get(i, i) for i in d.index], fontsize=8.5,
                    rotation=45, ha="right", rotation_mode="anchor")
ax1.set_ylabel("65+ 人口占比, %")
ax1.set_title("老龄化: 养老支出是 UBI 之外的刚性挤压", fontsize=10.5)
ax1.legend(frameon=False, fontsize=8.5)
p20s = p20.loc[[s for s in sel if s in p20.index]]
socxs = [sc.loc[i, "socx"] if pd.notna(sc.loc[i, "socx"]) else np.nan for i in p20s.index]
x2 = np.arange(len(p20s))
ax2.bar(x2, p20s.net_pct_gdp, width=0.55, color=C["green"], label="UBI 净成本 (α=20%)")
ax2.bar(x2, [5.0] * len(p20s), width=0.55, color="none", edgecolor=C["gray"],
        ls="--", lw=1.2, label="可替换现金转移假设 (5% GDP)")
for i, v in enumerate(p20s.net_pct_gdp):
    ax2.text(i, v + 0.08, f"{v:.1f}", ha="center", fontsize=8.5, fontweight="bold")
ax2.set_xticks(x2)
ax2.set_xticklabels([LABELS.get(i, i) for i in p20s.index], fontsize=8.5,
                    rotation=45, ha="right", rotation_mode="anchor")
ax2.set_ylabel("% GDP")
ax2.set_ylim(0, 12)
ax2.set_title("净成本 vs 替换基准: 多数国家增量≈0 或为负", fontsize=10.5)
ax2.legend(frameon=False, fontsize=8.5)
fig.suptitle("图 10 | 财政问题的真实结构: 不是 UBI 本身, 而是老龄化养老金 + 替换路径的政治选择", fontsize=11.5, y=1.02)
fig.tight_layout()
fig.savefig(FIG / "fig10_aging_squeeze.png", bbox_inches="tight")
plt.close(fig)
print("fig10 done")

# ================================================================ fig11 记分卡
dims = ["互联网", "金融账户", "电子身份", "数字政府(EGDI)", "税负空间",
        "社会支出\n替换容量", "债务空间", "实验经验"]
def norm(v, lo, hi, invert=False):
    if pd.isna(v):
        return np.nan
    s = 100 * np.clip((v - lo) / (hi - lo), 0, 1)
    return 100 - s if invert else s

rows = []
for iso, r in sc.iterrows():
    egdi_s = norm(r.egdi_rank, 1, 40, invert=True)
    taxspace = norm(44.0 - r.oecd_tax if pd.notna(r.oecd_tax) else np.nan, 0, 18)
    debt = norm(r.gov_debt, 0, 180, invert=True)
    socx_c = norm(r.socx, 10, 33)
    exp = 100 if iso in ("FIN", "USA") else (50 if r.experience else 20)
    rows.append([norm(r.internet_pct, 70, 100), norm(r.account_pct, 80, 100),
                 r.eid_pct if pd.notna(r.eid_pct) else np.nan,
                 egdi_s, taxspace, socx_c, debt, exp])
M = pd.DataFrame(rows, index=sc.index, columns=dims)
order = ["DNK", "EST", "SWE", "NOR", "NLD", "FIN", "ISL", "CHE", "DEU", "GBR",
         "FRA", "AUT", "ITA", "ESP", "JPN", "KOR", "SGP", "USA", "CAN", "AUS",
         "PRT", "POL", "NZL", "ISR", "LUX", "ARE"]
order = [o for o in order if o in M.index]
M = M.loc[order]
fig, ax = plt.subplots(figsize=(10.5, 9))
M_masked = M.mask(M.isna())
cmap = plt.get_cmap("RdYlGn").copy()
cmap.set_bad("#D9D9D9")
im = ax.imshow(M_masked.values, cmap=cmap, vmin=0, vmax=100, aspect="auto")
ax.set_xticks(range(len(dims)))
ax.set_xticklabels(dims, fontsize=9.5)
ax.set_yticks(range(len(M)))
ax.set_yticklabels([LABELS.get(i, i) for i in M.index], fontsize=9.5)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        v = M.values[i, j]
        if pd.isna(v):
            ax.text(j, i, "n/a", ha="center", va="center", fontsize=7.5, color="#555555")
        else:
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7.5,
                    color="black" if 25 < v < 85 else "white")
ax.set_title("图 11 | 高信息化国家 UBI 就绪度记分卡 (0-100, 灰色=n/a)\n绿色=就绪度高; 综合判读: 北欧/爱沙尼亚/荷兰条件最齐备, 美日韩受政治与税基结构约束", fontsize=11.5, pad=12)
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
cb.set_label("就绪度得分", fontsize=9)
ax.grid(False)
fig.tight_layout()
fig.savefig(FIG / "fig11_scorecard.png", bbox_inches="tight")
plt.close(fig)
print("fig11 done")
