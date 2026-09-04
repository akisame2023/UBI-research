# -*- coding: utf-8 -*-
"""
子研究 —— 高度信息化国家的 UBI 可行性与财政问题
输入: data/raw/wdi_panel.csv (主研究) + wdi_panel2.csv (新增国家/老龄化) + owid_co2.csv
输出: data/processed/08_digital_readiness.csv, 09_ubi_scenarios_digital.csv,
      10_financing_menu.csv

外部核验常数 (sources/facts_digital_verified.md):
  - UN EGDI 2024: DNK 0.9847(#1), EST 0.9727(#2), SGP #3, KOR ~#4, GBR #7
  - eID 渗透: EST 98-99%, SGP(Singpass) 97%(15+), NOR(BankID) ~97%(成人),
    SWE(BankID) ~94%+, JPN(MyNumber) ~80%
  - OECD 税收/GDP 2023: DNK 44.0, FRA 43.9, SWE 41.7, FIN ~40.4, DEU ~38.3,
    OECD 平均 33.9, EST ~33, JPN ~34, KOR ~30.5
  - OECD 公共社会支出: FRA ~32%, ITA >30%, FIN 31.4%, DNK 26.4-30%, USA ~18-19%(毛)
"""
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(exist_ok=True)

# ------------------------------------------------------------ 数据合并
p1 = pd.read_csv(RAW / "wdi_panel.csv")
p2 = pd.read_csv(RAW / "wdi_panel2.csv")
panel = pd.concat([p1, p2], ignore_index=True)
wide = panel.pivot_table(index=["iso3", "country", "year"], columns="indicator",
                         values="value", aggfunc="first").reset_index()

def latest_cols(df, cols, max_year=2024):
    out = []
    for iso, g in df[df.year <= max_year].groupby("iso3"):
        row = {"iso3": iso, "country": g["country"].iloc[-1]}
        for c in cols:
            s = g[["year", c]].dropna()
            if len(s):
                row[c] = s[c].iloc[-1]
                row[c + "_year"] = int(s["year"].iloc[-1])
        out.append(row)
    return pd.DataFrame(out)

COHORT = ["DNK", "SWE", "NOR", "ISL", "EST", "NLD", "CHE", "FIN", "DEU", "FRA",
          "GBR", "USA", "CAN", "AUS", "JPN", "KOR", "SGP", "ARE", "ESP", "ITA",
          "AUT", "PRT", "POL", "LUX", "NZL", "ISR"]
NEED = ["population", "gdp_ppp_intdollar", "gdp_pc_ppp_constant", "internet_users",
        "account_own", "gini", "tax_rev_gdp", "gov_debt_gdp", "pop65_share",
        "gdp_per_employed", "gdp_current_usd"]
nat = latest_cols(wide[wide.iso3.isin(COHORT)], NEED)
nat = nat.set_index("iso3")

# ------------------------------------------------------------ 核验常数
OECD_TAX = {"DNK": 44.0, "FRA": 43.9, "SWE": 41.7, "FIN": 40.4, "DEU": 38.3,
            "EST": 33.0, "JPN": 34.0, "KOR": 30.5, "ITA": 42.9, "NOR": 44.3,  # NOR/ITA 为 OECD 公布值(约)
            "NLD": 38.0, "GBR": 35.3, "CAN": 33.2, "ESP": 37.5, "AUT": 43.1,
            "CHE": 26.5, "AUS": 29.6, "USA": 27.7, "PRT": 36.8, "POL": 35.2, "LUX": 39.0,
            "NZL": 32.8, "ISR": 32.4, "ISL": 38.6}
SOCX = {"FRA": 32.0, "ITA": 30.5, "FIN": 31.4, "DNK": 30.0, "AUT": 30.5,
        "DEU": 26.7, "GBR": 23.8, "USA": 18.7, "NOR": 26.0, "SWE": 25.5,
        "NLD": 22.0, "ESP": 26.0, "CAN": 19.0, "AUS": 16.7, "JPN": 22.3,
        "KOR": 14.8, "EST": 22.0, "CHE": 17.0, "PRT": 23.0, "POL": 21.3}
EGDI = {"DNK": (0.9847, 1), "EST": (0.9727, 2), "SGP": (np.nan, 3), "KOR": (np.nan, 4),
        "GBR": (np.nan, 7)}
EID = {"EST": 99, "NOR": 97, "SGP": 97, "SWE": 94, "JPN": 80, "DNK": 95,  # DNK/MITID 约95%(麦米迪ID)
       "ISL": 95, "FIN": 93, "NLD": 90, "BEL": 0}
AGING_2050 = {"JPN": 38.0, "KOR": 40.0, "ESP": 36.0, "ITA": 37.0, "DEU": 32.0,
              "FRA": 30.0, "PRT": 36.0, "FIN": 30.0, "DNK": 26.0, "CHE": 27.0,
              "NLD": 28.0, "GBR": 27.0, "CAN": 28.0, "AUS": 25.0, "USA": 24.0}
EXPERIENCE = {"FIN": "Kela 2017-18 全国实验", "USA": "阿拉斯加分红+CTC+OpenResearch",
              "CHE": "2016 公投被否(76.9%)", "JPN": "2020 公明党特别定额给付提案",
              "DNK": "无全国实验(政党提案)", "KOR": "疫情灾害给付(普惠式)"}

def k_gini(g):
    g = min(max(g, 0.20), 0.65)
    s = np.sqrt(2) * norm.ppf((1 + g) / 2)
    z = np.linspace(1e-6, 15, 400000)
    my, sy = -s**2 / 2, s
    dens = np.exp(-(np.log(z) - my) ** 2 / (2 * sy ** 2)) / (z * sy * np.sqrt(2 * np.pi))
    return np.trapezoid(np.maximum(0, 1 - z) * dens, z)

# ------------------------------------------------------------ 记分卡
rows = []
for iso in COHORT:
    if iso not in nat.index:
        continue
    r = nat.loc[iso]
    rows.append({
        "iso3": iso, "country": r.country,
        "internet_pct": r.get("internet_users", np.nan),
        "account_pct": r.get("account_own", np.nan),
        "egdi_score": EGDI.get(iso, (np.nan, np.nan))[0],
        "egdi_rank": EGDI.get(iso, (np.nan, np.nan))[1],
        "eid_pct": EID.get(iso, np.nan),
        "oecd_tax": OECD_TAX.get(iso, np.nan),
        "wdi_tax": r.get("tax_rev_gdp", np.nan),
        "socx": SOCX.get(iso, np.nan),
        "pop65_pct": r.get("pop65_share", np.nan),
        "pop65_2050": AGING_2050.get(iso, np.nan),
        "gov_debt": r.get("gov_debt_gdp", np.nan),
        "gdp_pc_ppp": r.get("gdp_pc_ppp_constant", np.nan),
        "population_M": r.get("population", np.nan) / 1e6 if pd.notna(r.get("population")) else np.nan,
        "gini": r.get("gini", np.nan),
        "experience": EXPERIENCE.get(iso, ""),
    })
sc = pd.DataFrame(rows)
# 缺 Gini 的高收入国用典型值
sc["gini_used"] = sc.gini.apply(lambda v: v/100 if pd.notna(v) and v > 1 else (0.29 if pd.isna(v) else v))
sc["k_net"] = sc.gini_used.map(k_gini)
sc.to_csv(OUT / "08_digital_readiness.csv", index=False)
print("=== 数字就绪度记分卡 ===")
print(sc[["iso3", "internet_pct", "account_pct", "eid_pct", "egdi_rank", "oecd_tax",
          "socx", "pop65_pct", "gov_debt"]].round(1).to_string(index=False))

# ------------------------------------------------------------ UBI 情景 (α = 20% 人均GDP 为主)
rows = []
for _, r in sc.iterrows():
    for a in [0.10, 0.20, 0.30]:
        gross = 100 * a
        net = r.k_net * gross
        inc5 = net - 5.0    # 假设替换 5% GDP 的现有现金转移
        inc10 = net - 10.0
        tax_gap = (44.0 - r.oecd_tax) if pd.notna(r.oecd_tax) else np.nan
        rows.append({"iso3": r.iso3, "country": r.country, "alpha": a,
                     "gross_pct_gdp": gross, "net_pct_gdp": net,
                     "incremental_R5": inc5, "incremental_R10": inc10,
                     "tax_headroom_to_DK_pp": tax_gap,
                     "gini_used": r.gini_used, "k_net": r.k_net})
scen = pd.DataFrame(rows)
scen.to_csv(OUT / "09_ubi_scenarios_digital.csv", index=False)
print("\n=== UBI 情景 (α=20% 人均GDP) ===")
p = scen[scen.alpha == 0.20]
print(p[["iso3", "gross_pct_gdp", "net_pct_gdp", "incremental_R5", "incremental_R10",
         "tax_headroom_to_DK_pp"]].round(1).to_string(index=False))

# ------------------------------------------------------------ 融资菜单 (α=20%)
co2 = pd.read_csv(RAW / "owid_co2.csv")
co2.columns = [c.strip().lower() for c in co2.columns]
c_col = [c for c in co2.columns if c in ("entity", "country")][0]
y_col = "year"
num_cols = [c for c in co2.columns if c not in (c_col, y_col, "code", "iso3") and not c.endswith("annotations")]
v_col = num_cols[0]
co2["iso3"] = co2.get("code", "")
co2_latest = co2[(co2[y_col] >= 2022) & (co2.iso3.isin(COHORT))].sort_values(y_col).groupby("iso3").tail(1)

rows = []
for _, r in sc.iterrows():
    p20 = scen[(scen.iso3 == r.iso3) & (scen.alpha == 0.20)].iloc[0]
    inc = p20.incremental_R5
    co2mt = co2_latest[co2_latest.iso3 == r.iso3][v_col]
    co2mt = co2mt.iloc[0] if len(co2mt) else np.nan
    carbon_rev_pct = (co2mt * 75 / 1e6) / (r.gdp_pc_ppp * r.population_M) * 100 \
        if pd.notna(co2mt) and pd.notna(r.population_M) else np.nan
    rows.append({"iso3": r.iso3, "country": r.country,
                 "incremental_pct_gdp": inc,
                 "carbon_rev_75usd_pct_gdp": carbon_rev_pct,
                 "income_tax_uplift_pp": inc,
                 "tax_increase_pct_of_current": 100 * inc / r.oecd_tax if pd.notna(r.oecd_tax) else np.nan})
fin = pd.DataFrame(rows)
fin.to_csv(OUT / "10_financing_menu.csv", index=False)
print("\n=== 融资菜单 (α=20%, 替换 5% GDP 现金转移后) ===")
print(fin.round(2).to_string(index=False))

# 数据分红上界 (全球): 数字广告总盘 ~4430-7400 亿 USD (2024, dentsu/Oberlo)
print("\n数据分红上界: 全球数字广告 2024 ≈ $443-740B = 0.4-0.65% 世界 GDP (100% 征收的上界)")
print("挪威 GPFG: NOK 21.3T ≈ $2.1T (2025末), 财政规则 3% 提款率 ≈ 10%+ 挪威 GDP 的年度预算支撑")
