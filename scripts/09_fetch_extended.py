# -*- coding: utf-8 -*-
"""
子研究 —— 高信息化国家 UBI 可行性: 数据扩展下载
1) WDI 新增国家(北欧/爱沙尼亚/荷兰/韩国/新加坡等) + 老龄化指标
2) OWID 各国 CO2 排放(碳税收入测算用)
输出: data/raw/wdi_panel2.csv, data/raw/owid_co2.csv
"""
import json
import time
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

NEW_COUNTRIES = [
    "DNK", "SWE", "NOR", "ISL", "EST", "NLD", "CHE", "AUS", "KOR", "SGP",
    "ARE", "ESP", "ITA", "PRT", "AUT", "POL", "LUX", "NZL", "ISR",
    "FIN", "DEU", "FRA", "GBR", "USA", "CAN", "AUS", "JPN",
]
NEW_INDICATORS = {
    # 老龄化与人口结构
    "SP.POP.65UP.TO.ZS":  "pop65_share",      # 65+ 人口占比 (老龄化)
    "SP.POP.0014.TO.ZS":  "pop014_share",
    "SP.DYN.LE00.IN":     "life_expectancy",
    "NY.GDP.PCAP.CD":     "gdp_pc_current",
    # 基础规模与财政(与主研究面板同口径)
    "SP.POP.TOTL":        "population",
    "NY.GDP.MKTP.PP.CD":  "gdp_ppp_intdollar",
    "NY.GDP.MKTP.CD":     "gdp_current_usd",
    "NY.GDP.PCAP.PP.KD":  "gdp_pc_ppp_constant",
    "FX.OWN.TOTL.ZS":     "account_own",
    "IT.NET.USER.ZS":     "internet_users",
    "GC.TAX.TOTL.GD.ZS":  "tax_rev_gdp",
    "GC.DOD.TOTL.GD.ZS":  "gov_debt_gdp",
    "SI.POV.GINI":        "gini",
    "SL.GDP.PCAP.EM.KD":  "gdp_per_employed",
}

def fetch_json(url):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ubi-research/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  retry {i+1}: {e}")
            time.sleep(1)
    raise RuntimeError(url)

def main():
    import csv
    all_rows = []
    for code, name in NEW_INDICATORS.items():
        url = (f"https://api.worldbank.org/v2/country/{';'.join(NEW_COUNTRIES)}"
               f"/indicator/{code}?format=json&per_page=20000&date=1990:2025")
        data = fetch_json(url)
        rows = (data[1] or []) if isinstance(data, list) and len(data) > 1 else []
        for r in rows:
            if r["value"] is None:
                continue
            all_rows.append({"indicator": name, "iso3": r["countryiso3code"],
                             "country": r["country"]["value"],
                             "year": int(r["date"]), "value": r["value"]})
        print(f"WDI {code} -> {name}: {len(rows)} rows")
        time.sleep(0.3)
    with open(RAW / "wdi_panel2.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["indicator", "iso3", "country", "year", "value"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"saved data/raw/wdi_panel2.csv ({len(all_rows)} rows)")

    # OWID CO2 (各国年度 CO2 排放, Mt)
    for slug in ["co2", "annual-co2-emissions-per-country"]:
        try:
            req = urllib.request.Request(
                f"https://ourworldindata.org/grapher/{slug}.csv?csvType=full&useColumnShortNames=true",
                headers={"User-Agent": "Mozilla/5.0 ubi-research/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                txt = r.read().decode("utf-8", errors="replace")
            with open(RAW / "owid_co2.csv", "w", encoding="utf-8") as f:
                f.write(txt)
            print(f"OWID {slug} -> data/raw/owid_co2.csv ({len(txt.splitlines())} lines)")
            break
        except Exception as e:  # noqa: BLE001
            print(f"OWID {slug} failed: {e}")

if __name__ == "__main__":
    main()
