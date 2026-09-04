# -*- coding: utf-8 -*-
"""
UBI 可负担性研究 —— 数据下载脚本
来源:
  1. World Bank WDI API (v2)      -> data/raw/wdi_*.csv
  2. World Bank PIP API (贫困分布) -> data/raw/pip_*.csv
  3. Our World in Data grapher CSV -> data/raw/owid_*.csv
所有原始数据落盘,后续分析脚本只读取本地文件,保证可复现。
"""
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- helpers
def fetch_json(url: str, retries: int = 3, sleep: float = 1.0):
    """GET a URL, parse JSON, retry on failure."""
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ubi-research/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  retry {i+1}/{retries} after error: {e}")
            time.sleep(sleep)
    raise RuntimeError(f"failed: {url}")

def fetch_text(url: str, retries: int = 3, sleep: float = 1.0):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 ubi-research/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            print(f"  retry {i+1}/{retries} after error: {e}")
            time.sleep(sleep)
    raise RuntimeError(f"failed: {url}")

# ---------------------------------------------------------------- 1. WDI
# 国家/聚合体选择: 全球 + 收入组 + 主要经济体 + 治理缺口代表国
COUNTRIES = [
    "WLD", "HIC", "OED", "EUU", "LMY", "LMC", "UMC", "MIC", "LIC", "SSF",
    "USA", "CHN", "JPN", "DEU", "FRA", "GBR", "FIN", "NOR", "CAN",
    "BRA", "MEX", "ARG", "IND", "IDN", "TUR", "RUS", "ZAF",
    "KEN", "NGA", "EGY", "PAK", "BGD", "VNM", "PHL", "THA", "IRN", "UKR",
]

INDICATORS = {
    # 规模与生产率
    "NY.GDP.MKTP.CD":      "gdp_current_usd",
    "NY.GDP.MKTP.PP.CD":   "gdp_ppp_intdollar",
    "NY.GDP.MKTP.KD":      "gdp_constant",
    "NY.GDP.PCAP.KD":      "gdp_pc_constant",
    "NY.GDP.PCAP.PP.KD":   "gdp_pc_ppp_constant",
    "NY.GDP.MKTP.KD.ZG":   "gdp_growth",
    "SL.GDP.PCAP.EM.KD":   "gdp_per_employed",   # 劳均产出(生产率)
    "SP.POP.TOTL":         "population",
    "SP.POP.1564.TO.ZS":   "pop_working_age_share",
    "SL.TLF.TOTL.IN":      "labor_force",
    "SP.POP.GROW":         "pop_growth",
    # 贫困与分配 (2021 PPP 线: $3.00 / $4.20 / $8.30)
    "SI.POV.DDAY":         "pov_hc_300",
    "SI.POV.LMIC":         "pov_hc_420",
    "SI.POV.UMIC":         "pov_hc_830",
    "SI.POV.GAPS":         "pov_gap_300",
    "SI.POV.LMIC.GP":      "pov_gap_420",
    "SI.POV.UMIC.GP":      "pov_gap_830",
    "SI.POV.SOPO":         "pov_hc_spl",          # 社会贫困线
    "SI.POV.NAHC":         "pov_hc_national",
    "SI.POV.GINI":         "gini",
    "SI.DST.FRST.10":      "incshare_bottom10",
    "SI.DST.10TH.10":      "incshare_top10",
    "SI.DST.FRST.20":      "incshare_bottom20",
    "SI.DST.02ND.20":      "incshare_2nd20",
    "SI.DST.03RD.20":      "incshare_3rd20",
    "SI.DST.04TH.20":      "incshare_4th20",
    # 财政与国家能力
    "GC.TAX.TOTL.GD.ZS":   "tax_rev_gdp",
    "GC.XPN.TOTL.GD.ZS":   "gov_exp_gdp",
    "GC.REV.XGRT.GD.ZS":   "gov_rev_gdp",
    "MS.MIL.XPND.GD.ZS":   "military_gdp",
    "DT.ODA.ODAT.GD.ZS":   "aid_gni",
    "GC.DOD.TOTL.GD.ZS":   "gov_debt_gdp",
    # 治理技术/数字基础设施
    "FX.OWN.TOTL.ZS":      "account_own",        # Findex 账户拥有率
    "IT.NET.USER.ZS":      "internet_users",
    "IT.CEL.SETS.P2":      "mobile_subs_per100",
    "EG.ELC.ACCS.ZS":      "electricity_access",
}

def fetch_wdi(indicator: str, countries, date="1990:2024"):
    cs = ";".join(countries)
    url = (f"https://api.worldbank.org/v2/country/{cs}/indicator/{indicator}"
           f"?format=json&per_page=20000&date={date}")
    data = fetch_json(url)
    # API 出错时返回 {"message": [...]} 而非 [meta, rows]
    rows = (data[1] or []) if isinstance(data, list) and len(data) > 1 else []
    out = []
    for r in rows:
        if r["value"] is None:
            continue
        out.append({
            "iso3": r["countryiso3code"],
            "country": r["country"]["value"],
            "year": int(r["date"]),
            "value": r["value"],
        })
    return out

def run_wdi():
    all_rows = []
    for code, name in INDICATORS.items():
        print(f"WDI {code} -> {name}")
        rows = fetch_wdi(code, COUNTRIES)
        print(f"  {len(rows)} observations")
        for r in rows:
            r["indicator"] = name
            all_rows.append(r)
        time.sleep(0.3)
    import csv
    with open(RAW / "wdi_panel.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["indicator", "iso3", "country", "year", "value"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"saved data/raw/wdi_panel.csv ({len(all_rows)} rows)")

# ---------------------------------------------------------------- 2. PIP (distribution deciles / rural)
def run_pip():
    """PIP API: 按十分位的人口与收入分布,用于净成本再分配测算。"""
    base = "https://api.worldbank.org/pip/v1"
    try:
        url = base + "/pip-grp?country=all&year=2022&group_by=decile&welfare_type=all&format=json"
        data = fetch_json(url)
        import csv
        if isinstance(data, list) and data:
            keys = list(data[0].keys())
            with open(RAW / "pip_deciles_2022.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=keys)
                w.writeheader()
                for row in data:
                    w.writerow(row)
            print(f"saved data/raw/pip_deciles_2022.csv ({len(data)} rows)")
        else:
            print("PIP deciles: unexpected payload", str(data)[:200])
    except Exception as e:  # noqa: BLE001
        print("PIP API unavailable:", e)

# ---------------------------------------------------------------- 3. OWID
OWID_FILES = {
    # 长期生产率 (Maddison 2023): 1820-2022 人均GDP
    "gdp-per-capita-maddison-project-database": "owid_maddison_gdppc.csv",
    # 劳动份额 (ILO/PWT 含自雇)
    "labor-share-of-gdp": "owid_labor_share.csv",
    # 世界极端贫困长期 (1820-)
    "world-population-living-in-extreme-poverty": "owid_extreme_poverty_longrun.csv",
    # 机器人密度 (IFR, 每千工人)
    "robot-density": "owid_robot_density.csv",
}

def run_owid():
    import csv, io
    for slug, fname in OWID_FILES.items():
        url = f"https://ourworldindata.org/grapher/{slug}.csv?csvType=full&useColumnShortNames=true"
        try:
            txt = fetch_text(url)
            rows = list(csv.reader(io.StringIO(txt)))
            with open(RAW / fname, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(rows)
            print(f"OWID {slug} -> data/raw/{fname} ({len(rows)} lines)")
        except Exception as e:  # noqa: BLE001
            print(f"OWID {slug} FAILED: {e}")
        time.sleep(0.5)

if __name__ == "__main__":
    print("=== 1. World Bank WDI ===")
    run_wdi()
    print("=== 2. World Bank PIP deciles ===")
    run_pip()
    print("=== 3. Our World in Data ===")
    run_owid()
    print("DONE")
