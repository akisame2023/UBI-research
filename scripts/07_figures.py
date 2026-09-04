# -*- coding: utf-8 -*-
"""UBI 研究 —— 图表脚本 (中文, 出版质量, 输出 figures/*.png, 300dpi)"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "text.parse_math": False,
    "figure.dpi": 110,
    "savefig.dpi": 300,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "font.size": 10.5,
})
C = {"blue": "#2C6E9B", "red": "#C04A3E", "green": "#3E8E5A", "orange": "#E08A3C",
     "gray": "#7F8C99", "purple": "#7B5AA6", "lblue": "#8FB8D4", "lred": "#E0A49B"}

glob = pd.read_csv(OUT / "01_global_scenarios_2024.csv")
nat = pd.read_csv(OUT / "02_country_scenarios.csv")
path = pd.read_csv(OUT / "04_affordability_path.csv")
gov = pd.read_csv(OUT / "05_governance_gaps.csv")
prop = pd.read_csv(OUT / "06_proposal_scenarios.csv")

# ================================================================ 图1: 全球情景
fig, ax = plt.subplots(figsize=(9, 4.8))
y = np.arange(3)
h = 0.36
ax.barh(y - h/2, glob.gross_pct_world_gdp_ppp, height=h, color=C["blue"], label="普惠毛成本")
ax.barh(y + h/2, glob.gap_elim_pct_world_gdp_ppp, height=h, color=C["green"],
        label="消除贫困缺口(净成本下限)")
for i, r in glob.iterrows():
    ax.text(r.gross_pct_world_gdp_ppp + 0.15, i - h/2, f"{r.gross_pct_world_gdp_ppp:.1f}%",
            va="center", fontsize=10, color=C["blue"], fontweight="bold")
    ax.text(r.gap_elim_pct_world_gdp_ppp + 0.15, i + h/2, f"{r.gap_elim_pct_world_gdp_ppp:.2f}%",
            va="center", fontsize=10, color=C["green"], fontweight="bold")
ax.axvline(12.9, color=C["purple"], ls="--", lw=1.4)
ax.text(12.9, 2.62, " 全球社保支出 12.9% GDP\n (ILO 2023)", fontsize=9, color=C["purple"], va="top")
ax.axvline(2.47, color=C["gray"], ls=":", lw=1.4)
ax.text(2.47 + 0.12, -0.42, "全球军费 2.47%", fontsize=9, color=C["gray"])
ax.set_yticks(y)
ax.set_yticklabels([f"$3.00/天\n(极端贫困线)", f"$4.20/天\n(中低收入国家线)", f"$8.30/天\n(中高收入国家线)"])
ax.set_xlabel("占 2024 年世界 GDP(PPP) 的百分比 (%)")
ax.set_title("图 1 | 全球普惠 UBI 的成本: 生产率总量已足够覆盖中高收入线以下转移 (2024 年, 2021 PPP)", fontsize=11.5, pad=12)
ax.legend(loc="lower right", frameon=False)
ax.set_xlim(0, 16.5)
fig.tight_layout()
fig.savefig(FIG / "fig1_global_affordability.png", bbox_inches="tight")
plt.close(fig)
print("fig1 done")

# ================================================================ 图2: 国家矩阵
sel = ["USA", "DEU", "FIN", "GBR", "FRA", "CAN", "JPN", "RUS", "TUR", "ARG",
       "MEX", "BRA", "ZAF", "CHN", "THA", "PHL", "VNM", "IDN", "EGY", "IND",
       "BGD", "PAK", "NGA", "KEN"]
d = nat[nat.iso3.isin(sel) & (nat.line_ppp == 8.3)].drop_duplicates("iso3").copy()
d = d[~d.iso3.isin(["FIN", "CAN", "FRA", "JPN", "IRN", "THA"])]  # 精简左下/中部过密点, 保证标签可读
fig, ax = plt.subplots(figsize=(9, 6))
for _, r in d.iterrows():
    x = r.gross_pct_gdp
    yv = r.net_transfer_pct_gdp
    col = C["red"] if x > 40 else (C["orange"] if x > 15 else C["blue"])
    ax.scatter(x, yv, s=np.sqrt(r.gdp_pc_ppp) * 6, color=col, alpha=0.75, edgecolor="white", lw=0.8, zorder=3)
ax.set_xscale("log")
ax.set_xlim(1.1, 60)
ax.set_ylim(0, 18)
ax.set_xticks([1, 2, 5, 10, 20, 50])
ax.set_xticklabels(["1", "2", "5", "10", "20", "50"])
# 手工标签偏移(按显示几何调定, 单位: points), 白色描边保证压在气泡上仍可读
import matplotlib.patheffects as pe
HOFF = {"United States": (3, 6), "Germany": (-20, -16), "United Kingdom": (6, -14),
        "Russian Federation": (6, 3), "Turkiye": (6, 4), "China": (-52, 4),
        "Brazil": (6, 3), "Egypt, Arab Rep.": (6, 3), "Indonesia": (-58, 4),
        "Viet Nam": (6, 4), "South Africa": (-64, 4), "Philippines": (6, 6),
        "India": (6, -13), "Bangladesh": (6, -14), "Nigeria": (6, 3),
        "Kenya": (-76, 4), "Pakistan": (-84, -3)}
halo = [pe.withStroke(linewidth=2.5, foreground="white")]
for _, r in d.iterrows():
    off = HOFF.get(r.country)
    if off is None:
        continue
    a = ax.annotate(r.country, (r.gross_pct_gdp, r.net_transfer_pct_gdp),
                    xytext=off, textcoords="offset points", fontsize=8.8, zorder=5)
    a.set_path_effects(halo)
ax.axvline(15, color=C["gray"], ls="--", lw=1.2)
ax.text(15.3, 16.2, "撒哈拉以南非洲典型税收\n能力上限 (~15% GDP)", fontsize=8.5, color=C["gray"])
ax.set_xlabel("普惠毛成本, 占本国 GDP(PPP) %  (对数轴) — $8.30/天线")
ax.set_ylabel("净转移成本 (比例税回收基准), % GDP")
ax.set_title("图 2 | 国家层面: 富国可负担, 低收入国家难以自筹 ($8.30/天, 2021 PPP)\n普惠毛成本占本国 GDP: 印度 28%、肯尼亚 46%、巴基斯坦 48% vs 德国 4.1%、美国 3.5%", fontsize=11, pad=10)
fig.tight_layout()
fig.savefig(FIG / "fig2_country_matrix.png", bbox_inches="tight")
plt.close(fig)
print("fig2 done")

# ================================================================ 图3: 长期生产率
mad = pd.read_csv(OUT / "03_world_gdppc_maddison.csv")
wdi = pd.read_csv(RAW / "wdi_panel.csv")
g22 = wdi[(wdi.iso3 == "WLD") & (wdi.indicator == "gdp_pc_ppp_constant") & (wdi.year == 2022)].value.iloc[0]
g24 = wdi[(wdi.iso3 == "WLD") & (wdi.indicator == "gdp_pc_ppp_constant") & (wdi.year == 2024)].value.iloc[0]
mad["gdp_pc"] = mad.gdp_per_capita / mad.gdp_per_capita.iloc[-1] * g22  # 锚定换算到 2021 PPP
mad_ext = pd.concat([mad[["year", "gdp_pc"]],
                     pd.DataFrame({"year": [2024], "gdp_pc": [g24]})], ignore_index=True)
fig, ax = plt.subplots(figsize=(9.5, 5))
ax.plot(mad_ext.year, mad_ext.gdp_pc, color=C["blue"], lw=1.8)
ax.set_yscale("log")
ax.set_yticks([500, 1000, 2000, 4000, 8000, 16000, 32000])
ax.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda v, p: f"${v:,.0f}"))
# 贫困线年度化
for line, lbl, col in [(3.00*365, "$3.00/天 = $1,095/年 (2021 PPP)", C["green"]),
                       (8.30*365, "$8.30/天 = $3,030/年 (2021 PPP)", C["orange"])]:
    ax.axhline(line, color=col, ls="--", lw=1.2)
    ax.text(1998, line * 1.10, lbl, fontsize=9, color=col)
ax.axhline(g24, color=C["red"], ls=":", lw=1.4)
ax.text(1860, g24 * 1.10, f"2024 世界人均 GDP(PPP, 2021$) ≈ ${g24/1000:.1f}k", fontsize=9, color=C["red"])
ax.annotate("工业革命前:\n世界人均仅略高于\n$3.00/天贫困线", xy=(1820, mad.gdp_pc.iloc[0]), xytext=(1838, 640),
            fontsize=8.5, color=C["gray"],
            arrowprops=dict(arrowstyle="->", color=C["gray"], lw=0.9))
ax.set_xlim(1820, 2026)
ax.set_xlabel("年份")
ax.set_ylabel("世界人均 GDP (2021 国际元 PPP, 对数轴)")
ax.set_title(f"图 3 | 1820-2024 世界生产率: 人均产出已达 $8.30/天贫困线的 {g24/(8.30*365):.1f} 倍\n(Maddison Project 2023, 以 2022 年锚定换算为 2021 PPP, 2024 年取 WDI; 长期年增 ~1.4%)", fontsize=11.5, pad=10)
fig.tight_layout()
fig.savefig(FIG / "fig3_longrun_productivity.png", bbox_inches="tight")
plt.close(fig)
print("fig3 done")

# ================================================================ 图4: 动态路径
fig, ax = plt.subplots(figsize=(9, 5))
colors = {"低 (1.0%)": C["red"], "基准 (1.5%)": C["orange"], "中高 (2.0%)": C["blue"], "AI 高情景 (3.0%)": C["green"]}
years = np.arange(2024, 2101)
share0 = glob.loc[glob.line_ppp_per_day == 8.3, "gross_pct_world_gdp_ppp"].iloc[0]
for g, label in [(0.010, "低 (1.0%)"), (0.015, "基准 (1.5%)"), (0.020, "中高 (2.0%)"), (0.030, "AI 高情景 (3.0%)")]:
    ax.plot(years, share0 / (1 + g) ** (years - 2024), color=colors[label], lw=1.8, label=f"增长 {label}")
ax.axhline(10, color=C["gray"], ls="--", lw=1)
ax.axhline(5, color=C["gray"], ls=":", lw=1)
ax.text(2024.8, 10.35, "10% GDP", fontsize=9, color=C["gray"], ha="left")
ax.text(2024.8, 5.35, "5% GDP", fontsize=9, color=C["gray"], ha="left")
ax.set_ylim(0, 14)
ax.set_xlim(2024, 2100)
ax.set_xlabel("年份")
ax.set_ylabel("普惠 $8.30/天 UBI 的毛成本, 占世界 GDP(PPP) %")
ax.set_title("图 4 | 固定真实水平的 UBI 何时变得\"便宜\": 仅靠既有增长趋势, 2035 年前后降至 10% GDP 以内\n(注: 若转移水平随收入指数化, 成本占比永不下降 — 见报告 §4.2)", fontsize=11, pad=10)
ax.legend(frameon=False, loc="upper right")
fig.tight_layout()
fig.savefig(FIG / "fig4_affordability_path.png", bbox_inches="tight")
plt.close(fig)
print("fig4 done")

# ================================================================ 图5: 融资
ls = pd.read_csv(RAW / "owid_labor_share.csv")
ls_w = ls[ls.entity == "World"].sort_values("year")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.6), gridspec_kw={"width_ratios": [1.25, 1]})
ax1.plot(ls_w.year, ls_w.iloc[:, 3], color=C["blue"], lw=1.8)
ax1.set_xlabel("年份")
ax1.set_ylabel("全球劳动份额 (含自雇收入, % GDP)")
ax1.set_title("全球劳动份额缓慢下滑 (ILO/OWID)", fontsize=10.5)
ax1.set_ylim(48, 60)
# 右: $8.30 情景成本谱系 + 可比融资来源
items = [
    ("消除贫困缺口\n(净成本下限)", 2.48, C["green"]),
    ("比例税回收基准\n(k=0.28)", 3.48, C["lblue"]),
    ("普惠毛成本", 12.34, C["blue"]),
]
ax2.barh([0, 1, 2], [i[1] for i in items], color=[i[2] for i in items], height=0.55)
for i, (_, v, _) in enumerate(items):
    ax2.text(v + 0.15, i, f"{v:.1f}%", va="center", fontsize=10, fontweight="bold")
comp = [("亿万富翁 2% 财富税\n(~$0.32 万亿)", 0.16, C["purple"]),
        ("化石燃料显性补贴\n($1.3 万亿, 市场价)", 1.16, C["orange"]),
        ("全球军费", 2.47, C["gray"])]
ax2.barh([3.6, 4.6, 5.6], [i[1] for i in comp], color=[i[2] for i in comp], height=0.55, alpha=0.85)
for i, (_, v, _) in enumerate(comp):
    ax2.text(v + 0.15, 3.6 + 1.0 * i, f"{v:.2f}%", va="center", fontsize=10, fontweight="bold")
ax2.axvline(0, color="black", lw=0.8)
ax2.set_yticks([0, 1, 2, 3.6, 4.6, 5.6])
ax2.set_yticklabels([i[0] for i in items + comp], fontsize=9)
ax2.set_xlabel("% 世界 GDP")
ax2.set_title("$8.30 UBI 的成本谱系 vs 可比融资来源", fontsize=10.5)
fig.suptitle("图 5 | 融资: 资本份额提供税基; 针对性的小额全球财源即可覆盖净成本", fontsize=11.5, y=1.02)
fig.tight_layout()
fig.savefig(FIG / "fig5_financing.png", bbox_inches="tight")
plt.close(fig)
print("fig5 done")

# ================================================================ 图6: 治理缺口
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.8), gridspec_kw={"width_ratios": [1, 1.15]})
dims = ["无官方证件\n(ID4D 2025)", "无金融账户(成人)\n(Findex 2025)", "离线人口\n(ITU 2024)", "无电力接入\n(WDI 2024)"]
vals = [0.80, 1.30, 2.60, 0.66]
cols = [C["red"], C["orange"], C["blue"], C["gray"]]
b = ax1.barh(range(4), vals, color=cols, height=0.6)
for i, v in enumerate(vals):
    ax1.text(v + 0.04, i, f"{v:.2f}B", va="center", fontsize=10, fontweight="bold")
ax1.set_yticks(range(4)); ax1.set_yticklabels(dims, fontsize=9)
ax1.set_xlabel("全球人数 (十亿)")
ax1.set_xlim(0, 3.1)
ax1.set_title("数字触达的四重缺口", fontsize=10.5)
ax1.invert_yaxis()
d2 = nat.dropna(subset=["tax_rev_pct_gdp"]).drop_duplicates("iso3").copy()
wld_gov = gov[gov.iso3 == "WLD"].iloc[0]
d3 = d2.merge(gov[["iso3", "account_own_pct", "internet_pct"]], on="iso3", how="left")
sc = ax2.scatter(d3.tax_rev_pct_gdp, d3.account_own_pct, s=40 + np.sqrt(d3.gdp_pc_ppp) * 3,
                 c=d3.internet_pct, cmap="viridis", alpha=0.85, edgecolor="white")
GOV_OFF = {"DEU": (6, 8), "USA": (6, -13), "CAN": (6, 6), "IND": (5, -13), "KEN": (5, 7),
           "CHN": (-32, 4), "BGD": (5, 4), "PAK": (5, 6), "NGA": (5, 4), "FIN": (-8, -15), "BRA": (5, 4)}
for _, r in d3.iterrows():
    if r.iso3 in GOV_OFF:
        ax2.annotate(r.country, (r.tax_rev_pct_gdp, r.account_own_pct), xytext=GOV_OFF[r.iso3],
                     textcoords="offset points", fontsize=8.5)
ax2.set_xlabel("税收收入 (% GDP, WDI 口径, 不含社保缴款)")
ax2.set_ylabel("成人账户拥有率 (Findex, %)")
cb = fig.colorbar(sc, ax=ax2, fraction=0.046, pad=0.03)
cb.set_label("互联网普及率 (%)", fontsize=9)
ax2.set_title("国家能力 × 数字就绪度\n(左下角=治理技术最难区)", fontsize=10.5)
fig.suptitle("图 6 | 治理技术: 缺口不在\"钱\"而在\"最后一公里\" — 证件/账户/网络/电力各有 7-26 亿人未覆盖", fontsize=11.5, y=1.03)
fig.tight_layout()
fig.savefig(FIG / "fig6_governance.png", bbox_inches="tight")
plt.close(fig)
print("fig6 done")

# ================================================================ 图7: 方案对比
fig, ax = plt.subplots(figsize=(9, 4.2))
pr = prop.copy()
labels = ["美国\n$12k/年·全民", "美国\n$12k/年·成人", "芬兰\n€560/月·全民", "中国\n¥500/月·全民"]
x = np.arange(len(pr))
ax.bar(x - 0.19, pr.pct_gdp, width=0.38, color=C["blue"], label="毛成本 %GDP")
ax.bar(x + 0.19, pr.with_behavioral_15pct, width=0.38, color=C["lblue"], label="含劳动供给行为反应 (+15%)")
for i, (v1, v2) in enumerate(zip(pr.pct_gdp, pr.with_behavioral_15pct)):
    ax.text(i - 0.19, v1 + 0.15, f"{v1:.1f}%", ha="center", fontsize=9.5, fontweight="bold")
    ax.text(i + 0.19, v2 + 0.15, f"{v2:.1f}%", ha="center", fontsize=9.5)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9.5)
ax.set_ylabel("% 本国 GDP (2024)")
ax.set_title("图 7 | 现实方案的财政量级: 高收入国家 11-14% GDP, 中国 6.3% — 均属\"可动员\"区间\n(对比: 美国联邦现行个人转移支付 ~10% GDP; 中国一般公共预算支出 ~21% GDP)", fontsize=11, pad=10)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG / "fig7_proposals.png", bbox_inches="tight")
plt.close(fig)
print("fig7 done")

# ================================================================ 图8: 方法流程 (schematic)
fig, ax = plt.subplots(figsize=(11, 5.2))
ax.axis("off")
def box(x, y, w, h, text, fc, ec="none", fs=9.5, tc="white"):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012", fc=fc, ec=ec, lw=1.2)
    ax.add_patch(b)
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs, color=tc, linespacing=1.5)
def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16, color=C["gray"], lw=1.4))
box(0.01, 0.62, 0.17, 0.30, "研究问题\n\n① 生产力够不够 UBI?\n② 治理技术障碍?", C["purple"])
box(0.21, 0.62, 0.24, 0.30, "文献层 (80 篇)\n经典 15 · 实验 15 · 成本 13\nAI/生产率 21 · 治理 15 · 数据 1", C["blue"], fs=9)
box(0.48, 0.62, 0.24, 0.30, "数据层\nWDI 36 指标 × 33 国 (31,656 行)\nMaddison 1820-2022\nOWID 劳动份额\n14 项事实网络核验", C["green"], fs=9)
box(0.75, 0.62, 0.24, 0.30, "分析层 (5 模块)\n情景矩阵 · 净成本模型\n(LogN-Gini 校准)\n动态路径 · 融资 · 治理", C["orange"], fs=9)
box(0.21, 0.12, 0.24, 0.34, "核心结论 ①\n总 量 充 足:\n消除极端贫困缺口\n= 0.16% 世界 GDP;\n普惠 $8.30/天 = 12.3%\n≈ 现行全球社保(12.9%)", C["red"], fs=9)
box(0.48, 0.12, 0.24, 0.34, "核心结论 ②\n结构错配:\n穷国成本占 GDP 28-48%,\n富国 3.5-5.6%;\n全球总量可行,\n国家层面难行", C["red"], fs=9)
box(0.75, 0.12, 0.24, 0.34, "核心结论 ③\n治理是紧约束:\n无证件 8 亿 · 无账户 13 亿\n离线 26 亿 · 税基 10-15% GDP\n(LIC, OECD 口径 25-40%)\n→ 技术已解决\"可支付\",\n未解决\"可触达/可信\"", C["red"], fs=9)
arrow(0.18, 0.77, 0.21, 0.77); arrow(0.45, 0.77, 0.48, 0.77); arrow(0.72, 0.77, 0.75, 0.77)
arrow(0.33, 0.62, 0.33, 0.46); arrow(0.60, 0.62, 0.60, 0.46); arrow(0.87, 0.62, 0.87, 0.46)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_title("图 8 | 研究设计与证据流 (文献 → 数据 → 分析 → 结论)", fontsize=12, pad=14)
fig.tight_layout()
fig.savefig(FIG / "fig8_method.png", bbox_inches="tight")
plt.close(fig)
print("fig8 done")

print("ALL FIGURES DONE ->", FIG)
