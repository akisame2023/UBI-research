# -*- coding: utf-8 -*-
"""
UBI 可负担性研究 —— 核心分析脚本
输入: data/raw/wdi_panel.csv, data/raw/owid_maddison_gdppc.csv, data/raw/owid_labor_share.csv
输出: data/processed/*.csv (全部结果表)

方法学要点
----------
1. 口径: 贫困线用世界银行 2021 PPP 线 ($3.00 / $4.20 / $8.30 每人每天, 2025-06 起采用)。
   PPP 度量"真实资源成本"(国内自筹口径); 涉及国际转移支付时需换算市场汇率, 文中注明。
2. 毛成本 = B × N (普惠转移支出总额)。
3. 净成本(消除贫困的理论下限) = 贫困缺口指数 PGI × line × 365 × N
   (PGI = 平均短缺/贫困线, 把非贫困者记为 0 —— 世界银行官方定义)。
4. 净转移成本(普惠+累进回收) = B × E[(1 - Y/μ)⁺], 其中 Y~LogN(μ, σ),
   σ 由各国 Gini 校准: G = 2Φ(σ/√2) - 1 ⇒ σ = √2·Φ⁻¹((1+G)/2)。
   这对应"比例附加税 τ = B/μ 融资"下的正向净转移总额 (Widerquist 意义上的真实净成本)。
5. 人均家庭收入代理 μ = 人均GDP(PPP) × θ, θ=0.75 (劳动份额+净转移占 GDP 比例的保守近似;
   该假设只影响净成本水平的常数缩放, 不影响结论方向, 敏感性文中给出)。
"""
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

DAYS = 365.0

# ------------------------------------------------------------------ load
panel = pd.read_csv(RAW / "wdi_panel.csv")
wide = panel.pivot_table(index=["iso3", "country", "year"], columns="indicator",
                         values="value", aggfunc="first").reset_index()

def latest(df, cols, year_col="year", max_year=None):
    """每个 iso3 逐指标取最新非缺失值(各指标年份可不同, 年份另存 <col>_year 列)。"""
    d = df.copy()
    if max_year:
        d = d[d[year_col] <= max_year]
    out = []
    for iso, g in d.groupby("iso3"):
        row = {"iso3": iso, "country": g["country"].iloc[-1]}
        for c in cols:
            if c not in g.columns:
                continue
            s = g[[year_col, c]].dropna()
            if len(s):
                row[c] = s[c].iloc[-1]
                row[c + "_year"] = int(s[year_col].iloc[-1])
        out.append(row)
    return pd.DataFrame(out)

# ------------------------------------------------------------------ 1. 全球情景 (2024)
wld = wide[(wide.iso3 == "WLD")].sort_values("year")
w24 = wld[wld.year == 2024].iloc[0]
POP = w24.population                 # 8.141e9
GDP_PPP = w24.gdp_ppp_intdollar      # 1.998e14
GDP_MKT = w24.gdp_current_usd        # 1.117e14

LINES = {"300": 3.00, "420": 4.20, "830": 8.30}   # 2021 PPP $/天
# 参照系 (核验事实): 全球社保支出 12.9% GDP; 军费 %; 化石显性补贴 $1.3T; 隐性+显性 7% GDP
military_share = w24.military_gdp      # WLD 军费 %GDP
socprot_share = 12.9                   # ILO WSPR 2024-26 (2023)

rows = []
for key, line in LINES.items():
    B = line * DAYS                                   # 年转移额 (PPP $/人)
    gross = B * POP
    hc = w24[f"pov_hc_{key}"] / 100                   # 贫困发生率
    pgi = w24[f"pov_gap_{key}"] / 100                 # 贫困缺口指数
    gap_cost = pgi * line * DAYS * POP                # 消除贫困净成本
    rows.append({
        "line_ppp_per_day": line,
        "transfer_per_year": B,
        "gross_cost_T": gross / 1e12,
        "gross_pct_world_gdp_ppp": 100 * gross / GDP_PPP,
        "headcount_pct": 100 * hc,
        "headcount_M": hc * POP / 1e6,
        "gap_elim_cost_T": gap_cost / 1e12,
        "gap_elim_pct_world_gdp_ppp": 100 * gap_cost / GDP_PPP,
    })
glob = pd.DataFrame(rows)
glob["gross_T_vs_socprot"] = glob.gross_pct_world_gdp_ppp / socprot_share
glob["gap_T_vs_military"] = glob.gap_elim_pct_world_gdp_ppp / military_share
glob.to_csv(OUT / "01_global_scenarios_2024.csv", index=False)
print("=== 1. 全球情景 (2024, 2021 PPP) ===")
print(glob.round(2).to_string(index=False))

# ------------------------------------------------------------------ 2. 国家情景
FOCUS = ["USA", "CHN", "JPN", "DEU", "FRA", "GBR", "FIN", "BRA", "MEX", "IND",
         "IDN", "TUR", "ZAF", "KEN", "NGA", "EGY", "PAK", "BGD", "VNM", "PHL",
         "IRN", "RUS", "ARG", "CAN"]
need = ["population", "gdp_ppp_intdollar", "pov_gap_300", "pov_gap_420",
        "pov_gap_830", "pov_hc_300", "pov_hc_420", "pov_hc_830",
        "tax_rev_gdp", "gov_exp_gdp", "gini", "account_own", "internet_users",
        "electricity_access", "gdp_pc_ppp_constant", "pop_working_age_share"]
nat = latest(wide[wide.iso3.isin(FOCUS)], need, max_year=2024)
nat = nat[["iso3", "country"] + [c for c in nat.columns if c not in ("iso3", "country")]]

THETA = 0.75   # 人均家庭收入 / 人均GDP

def logn_sigma(gini):
    """LogN 参数: 由 Gini 反解 σ。"""
    return np.sqrt(2) * norm.ppf((1 + gini) / 2)

def net_transfer_share(b_over_mu, sigma):
    """普惠 B + 比例税 τ=B/μ 下的正向净转移总额 / (B·N)。
       = E[(1 - Y/μ)⁺] / 1 其中 Y/μ ~ LogN(-σ²/2, σ)。"""
    z = np.linspace(1e-6, 12, 400000)   # Y/μ 网格
    # LogN(μ_y=-σ²/2, σ) 的密度
    my, sy = -sigma**2 / 2, sigma
    dens = np.exp(-(np.log(z) - my) ** 2 / (2 * sy ** 2)) / (z * sy * np.sqrt(2 * np.pi))
    integrand = np.maximum(0.0, 1.0 - z) * dens
    return np.trapezoid(integrand, z)

rows = []
for _, r in nat.iterrows():
    mu = r.gdp_pc_ppp_constant * THETA          # 人均家庭收入 (PPP $)
    for key, line in LINES.items():
        B = line * DAYS
        gross = B * r.population
        # (a) 毛成本
        gross_pct = 100 * gross / r.gdp_ppp_intdollar
        # (b) 贫困缺口下限
        pgi = r[f"pov_gap_{key}"] / 100
        gap_pct = 100 * pgi * line * DAYS * r.population / r.gdp_ppp_intdollar
        # (c) 对数正态净转移成本
        g = r.gini if pd.notna(r.gini) else 0.38   # 缺失用全球中位近似
        sig = logn_sigma(min(max(g, 0.20), 0.65) / 100) if g > 1 else logn_sigma(min(max(g, 0.20), 0.65))
        sigma = logn_sigma(g / 100 if g > 1 else g)  # gini 存的是 0-100 或 0-1
        nts = net_transfer_share(B / mu, sigma)
        net_gross = B * r.population * nts          # 正向净转移总额
        net_pct = 100 * net_gross / r.gdp_ppp_intdollar
        rows.append({
            "iso3": r.iso3, "country": r.country,
            "year": int(r.get("gdp_ppp_intdollar_year", 2024)),
            "line_ppp": line, "B_per_year": B,
            "gdp_pc_ppp": r.gdp_pc_ppp_constant, "gini": g,
            "gross_pct_gdp": gross_pct,
            "gap_elim_pct_gdp": gap_pct,
            "net_transfer_pct_gdp": net_pct,
            "tax_rev_pct_gdp": r.tax_rev_gdp,
            "required_avg_tax_on_gdp": gross_pct,     # 需从 GDP 中动员的份额
            "B_over_mu": B / mu,
        })
nat_sc = pd.DataFrame(rows)
# 全球也加入
wrow = {"iso3": "WLD", "country": "World", "year": 2024,
        "gdp_pc_ppp": GDP_PPP / POP, "gini": 0.39}
wrows = []
for key, line in LINES.items():
    B = line * DAYS
    sigma = logn_sigma(0.39)
    nts = net_transfer_share(B / (GDP_PPP / POP * THETA), sigma)
    wrows.append({"iso3": "WLD", "country": "World", "year": 2024,
                  "line_ppp": line, "B_per_year": B,
                  "gdp_pc_ppp": GDP_PPP / POP, "gini": 0.39,
                  "gross_pct_gdp": 100 * B * POP / GDP_PPP,
                  "gap_elim_pct_gdp": glob.loc[glob.line_ppp_per_day == line,
                                               "gap_elim_pct_world_gdp_ppp"].iloc[0],
                  "net_transfer_pct_gdp": 100 * B * POP * nts / GDP_PPP,
                  "tax_rev_pct_gdp": np.nan,
                  "required_avg_tax_on_gdp": 100 * B * POP / GDP_PPP,
                  "B_over_mu": B / (GDP_PPP / POP * THETA)})
nat_sc = pd.concat([nat_sc, pd.DataFrame(wrows)], ignore_index=True)
nat_sc.to_csv(OUT / "02_country_scenarios.csv", index=False)
print("\n=== 2. 国家情景 (普惠毛成本 %GDP / 贫困缺口下限 %GDP / 净转移成本 %GDP) ===")
piv = nat_sc.pivot_table(index=["country"], columns="line_ppp",
                         values=["gross_pct_gdp", "net_transfer_pct_gdp"], aggfunc="first")
print(piv.round(1).to_string())

# ------------------------------------------------------------------ 3. 动态路径: 何时可负担
mad = pd.read_csv(RAW / "owid_maddison_gdppc.csv")
mad.columns = [c.strip() for c in mad.columns]
# 列名兼容
country_col = [c for c in mad.columns if c.lower() in ("entity", "country", "countryname")][0]
year_col = [c for c in mad.columns if c.lower() in ("year", "date")][0]
val_col = [c for c in mad.columns if "gdppc" in c.lower() or "gdp_per_capita" in c.lower()][0]
world_mad = mad[mad[country_col] == "World"].sort_values(year_col)
print("\nMaddison world gdppc (2011$): 1820=%.0f, 1950=%.0f, 2000=%.0f, latest(%.0f)=%.0f" % (
    world_mad[world_mad[year_col] == 1820][val_col].iloc[0],
    world_mad[world_mad[year_col] == 1950][val_col].iloc[0],
    world_mad[world_mad[year_col] == 2000][val_col].iloc[0],
    world_mad[year_col].max(), world_mad[val_col].iloc[-1]))
world_mad.to_csv(OUT / "03_world_gdppc_maddison.csv", index=False)

# 近期增速 (WDI 人均 GDP, constant): 1990-2024 / 2000-2024 / 2010-2024 CAGR
for a, b in [(1990, 2024), (2000, 2024), (2010, 2024), (2019, 2024)]:
    wa = wld[wld.year == a].gdp_pc_ppp_constant
    wb = wld[wld.year == b].gdp_pc_ppp_constant
    if len(wa) and len(wb):
        cagr = (wb.iloc[0] / wa.iloc[0]) ** (1 / (b - a)) - 1
        print(f"  world GDP pc PPP CAGR {a}-{b}: {cagr*100:.2f}%")

# 增长情景: 2024 起以 g 增长, 求 固定 $8.30/天 线的普惠成本占比降到的年份
gdp_pc_2024 = GDP_PPP / POP
COST_SHARE_2024 = glob.loc[glob.line_ppp_per_day == 8.30, "gross_pct_world_gdp_ppp"].iloc[0]
scen = []
for g, label in [(0.010, "低 (1.0%)"), (0.015, "基准 (1.5%)"), (0.020, "中高 (2.0%)"),
                 (0.030, "AI 高情景 (3.0%)")]:
    for target in [10.0, 5.0, 2.5]:
        if COST_SHARE_2024 <= target:
            yrs = 0
        else:
            yrs = np.log(COST_SHARE_2024 / target) / np.log(1 + g)
        scen.append({"growth": label, "g": g, "target_share_pct": target,
                     "years_needed": yrs,
                     "year_reached": 2024 + yrs if yrs < 500 else np.inf})
scen = pd.DataFrame(scen)
scen.to_csv(OUT / "04_affordability_path.csv", index=False)
print("\n=== 3. $8.30/天 普惠 UBI 成本占比从 %.1f%% 降至目标的年份 ===" % COST_SHARE_2024)
print(scen.round(1).to_string(index=False))

# ------------------------------------------------------------------ 4. 融资结构
ls = pd.read_csv(RAW / "owid_labor_share.csv")
ls.columns = [c.strip() for c in ls.columns]
cc = [c for c in ls.columns if c.lower() in ("entity", "country")][0]
yc = [c for c in ls.columns if c.lower() in ("year", "date")][0]
vc = [c for c in ls.columns if c not in ("entity", "code", "year")][0]
ls_w = ls[ls[cc] == "World"].sort_values(yc)
labor_share_latest = ls_w[vc].iloc[-1]
print("\n=== 4. 融资 ===")
print(f"全球劳动份额(含自雇, {int(ls_w[yc].iloc[-1])}): {labor_share_latest:.1f}%  ⇒ 资本份额 ≈ {100-labor_share_latest:.1f}%")
for share_needed, what in [(glob.loc[2, "gap_elim_pct_world_gdp_ppp"], "消除 $8.30 贫困缺口"),
                           (glob.loc[2, "gross_pct_world_gdp_ppp"], "普惠 $8.30 UBI 毛额")]:
    cap_base = (100 - labor_share_latest) / 100
    print(f"  {what} = {share_needed:.1f}% GDP → 若全部来自资本收入税: 对资本收入征 {share_needed/cap_base:.1f}% "
          f"(资本收入基数 {cap_base*100:.0f}% GDP)")
# 亿万富翁对比
billionaire_wealth = 16.1e12   # Forbes 2025 (核验: ~16.1 万亿美元)
print(f"  Forbes 2025 亿万富翁财富 ~16.1 万亿: 2% 年度财富税 ≈ {0.02*billionaire_wealth/1e12:.2f} 万亿"
      f" vs 消除 $3 贫困缺口 {glob.loc[0,'gap_elim_cost_T']:.2f} 万亿/年")
print(f"  化石燃料显性补贴 1.3 万亿 (IMF) = 极端贫困缺口成本的 {1.3/glob.loc[0,'gap_elim_cost_T']:.1f} 倍")

# ------------------------------------------------------------------ 5. 治理缺口
gov = latest(wide[wide.iso3.isin(FOCUS + ["WLD"])],
             ["account_own", "internet_users", "electricity_access", "tax_rev_gdp", "gdp_pc_ppp_constant"],
             max_year=2024)
gov_rows = []
for _, r in gov.iterrows():
    adults = r.population * (r.pop_working_age_share / 100 + 0.10)  # 15-64 + 65+ 近似
    no_acct = adults * (1 - (r.account_own / 100 if pd.notna(r.account_own) else 0.79))
    offline = r.population * (1 - (r.internet_users / 100 if pd.notna(r.internet_users) else np.nan))
    gov_rows.append({"iso3": r.iso3, "country": r.country,
                     "year": int(r.get("population_year", 2024)),
                     "population_M": r.population / 1e6,
                     "adults_M": adults / 1e6,
                     "account_own_pct": r.account_own,
                     "no_account_M": no_acct / 1e6,
                     "internet_pct": r.internet_users,
                     "offline_M": offline / 1e6 if pd.notna(offline) else np.nan,
                     "tax_rev_pct": r.tax_rev_gdp,
                     "elec_pct": r.electricity_access})
gov_df = pd.DataFrame(gov_rows)
gov_df.to_csv(OUT / "05_governance_gaps.csv", index=False)
print("\n=== 5. 治理缺口 (覆盖缺口, 百万人) ===")
print(gov_df[gov_df.iso3.isin(["WLD", "USA", "CHN", "IND", "KEN", "NGA", "FIN"])].round(1).to_string(index=False))

# 低税收能力国家
low_tax = gov_df[gov_df.iso3 != "WLD"]
n_low_tax = (low_tax.tax_rev_pct < 15).sum()
print(f"\n样本中税收 <15% GDP 的国家: {n_low_tax}/{low_tax.tax_rev_pct.notna().sum()}")

# 多重排除 (世界): 无ID 8.5亿; 无账户成人 13亿; 离线 26亿 —— 独立 vs 相关
p_id = 0.85e9 / POP
p_acct_adults = 1.3e9 / (POP * 0.75)      # 成人口径
p_off = 2.6e9 / POP
p_none_indep = 1 - (1 - p_id) * (1 - p_acct_adults) * (1 - p_off)
print(f"三重维度至少缺一 (独立性假设, 上限): {p_none_indep*100:.0f}% ≈ {p_none_indep*POP/1e9:.1f}B")
print(f"高相关情形 (取最大缺口): ~{max(p_id, p_acct_adults, p_off)*100:.0f}% ≈ {max(p_id,p_acct_adults,p_off)*POP/1e9:.1f}B")

print("\nsaved: 01..05 CSV -> data/processed/")

# ------------------------------------------------------------------ 6. 现实方案情景 + 敏感性
print("\n=== 6. 现实政策方案 (按方案自身货币/口径) ===")
# 各国 2024 市场价 GDP
nat_mkt = latest(wide[wide.iso3.isin(["USA", "CHN", "FIN"])], ["population", "gdp_current_usd"], max_year=2024)
proposals = [
    # (国, 描述, 年转移额(本币/美元), 人数, GDP(市场价, 本币或美元), 备注)
    ("美国", "$12,000/人/年 · 全部人口", 12000, 340.0e6, nat_mkt.loc[nat_mkt.iso3 == "USA", "gdp_current_usd"].iloc[0],
     "标准美国提案 (Hoynes & Rothstein 2019 口径)"),
    ("美国", "$12,000/人/年 · 仅成年人", 12000, 262e6, nat_mkt.loc[nat_mkt.iso3 == "USA", "gdp_current_usd"].iloc[0], ""),
    ("中国", "¥500/人/月 · 全部人口", 6000, 1409e6, 1349081e8, "2024 GDP ¥134.9 万亿 (国家统计局口径近似)"),
    ("芬兰", "€560/人/月 · 全部人口", 6720, 5.6e6, 283e9, "Kela 实验金额外推 (GDP €283B, 2024)"),
]
prop_rows = []
for ctry, desc, B, N, gdp, note in proposals:
    pct = 100 * B * N / gdp
    prop_rows.append({"country": ctry, "scenario": desc, "annual_cost_B": B * N / 1e9,
                      "pct_gdp": pct, "note": note,
                      "with_behavioral_15pct": pct * 1.15})
prop_df = pd.DataFrame(prop_rows)
prop_df.to_csv(OUT / "06_proposal_scenarios.csv", index=False)
print(prop_df.round(1).to_string(index=False))

# 相对型 UBI 的恒定性: B = α × GDPpc ⇒ 成本占比 = α (与增长无关)
print("\n相对型 UBI 恒定性: 若 B = α·人均GDP, 则毛成本/GDP = α, 与增长率无关")
for a in [0.10, 0.25]:
    print(f"  α={a:.0%} → 永远占 GDP 的 {a*100:.0f}% (生产率增长不能降低相对型 UBI 的成本占比)")

# 敏感性: 净转移系数 E[(1-Y/mu)+] 随 Gini 变化 (比例税融资基准; 对 mu 尺度不变)
print("\n敏感性: 净转移成本 = k(Gini) x 毛成本, k 为尺度不变系数 (比例税融资基准)")
for g in [0.25, 0.32, 0.39, 0.48, 0.55]:
    sig_g = logn_sigma(g)
    k = net_transfer_share(np.nan, sig_g)
    print(f"  Gini={g:.2f}: k={k:.3f} → 世界 $8.30 普惠的净转移成本 = {k*100*8.30*DAYS*POP/GDP_PPP:.1f}% GDP")
print("  成本谱系 (回收设计决定实际财政负担):")
print("   理论下限=消除贫困缺口(完全定向回收) ←→ 比例税基准 k×毛额 ←→ 普惠毛额(零回收)")

print(f"\n世界军费占 GDP ({int(w24.year)}): {military_share:.2f}%  ≈ {military_share*GDP_PPP/100/1e12:.1f} 万亿(PPP)")
print(f"全球社保支出 12.9% GDP ≈ {12.9*GDP_PPP/100/1e12:.1f} 万亿(PPP) vs 普惠 $8.30 UBI 毛额 {glob.loc[2,'gross_cost_T']:.1f} 万亿")
ls_tail = ls_w.tail(3)[[yc, vc]].to_string(index=False)
print(f"\n劳动份额序列尾部:\n{ls_tail}")

# 贫困人数表 (报告用)
povtab = glob[["line_ppp_per_day", "headcount_pct", "headcount_M", "gap_elim_cost_T"]].copy()
povtab.to_csv(OUT / "07_poverty_headcounts.csv", index=False)
print("\n贫困人数 (2024):")
print(povtab.round(1).to_string(index=False))
