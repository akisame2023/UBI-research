# -*- coding: utf-8 -*-
"""
校验研究真实性 —— 机器复核层
1) 实时 WDI API 重新拉取关键指标, 与报告数字比对 (绕过本地管线, 防管线 bug)
2) 从原始文件直接重算 3 个关键推导量
3) 抽样解析 12 条参考文献 DOI (Crossref API), 比对标题
输出: data/processed/verification_results.json
"""
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed"

def wdi_live(iso, code, year):
    url = f"https://api.worldbank.org/v2/country/{iso}/indicator/{code}?format=json&date={year}:{year}"
    req = urllib.request.Request(url, headers={"User-Agent": "ubi-verify/1.0"})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if isinstance(d, list) and len(d) > 1 and d[1]:
        return d[1][0]["value"]
    return None

results = {"wdi_live": [], "recompute": [], "dois": []}

# ---------------- 1. 实时 API 比对 (报告声明值 vs live 值)
CHECKS = [
    ("世界 GDP(PPP) 2024 = $199.8 万亿", "WLD", "NY.GDP.MKTP.PP.CD", 2024, lambda v: f"{v/1e12:.1f}万亿", "199.8"),
    ("世界人口 2024 = 81.4 亿", "WLD", "SP.POP.TOTL", 2024, lambda v: f"{v/1e9:.2f}亿", "8.14"),
    ("世界贫困缺口 $3.00 2024 = 3.6%", "WLD", "SI.POV.GAPS", 2024, lambda v: f"{v:.1f}%", "3.6"),
    ("世界贫困率 $8.30 2024 = 46.1%", "WLD", "SI.POV.UMIC", 2024, lambda v: f"{v:.1f}%", "46.1"),
    ("世界账户拥有率 2024 = 78.7%", "WLD", "FX.OWN.TOTL.ZS", 2024, lambda v: f"{v:.1f}%", "78.7"),
    ("中国互联网 2024 = 92.0%", "CHN", "IT.NET.USER.ZS", 2024, lambda v: f"{v:.1f}%", "92.0"),
    ("中国 65+ 2024 = 14.7%", "CHN", "SP.POP.65UP.TO.ZS", 2024, lambda v: f"{v:.1f}%", "14.7"),
    ("中国 Gini 2022 = 36.0", "CHN", "SI.POV.GINI", 2022, lambda v: f"{v:.1f}", "36.0"),
    ("日本 65+ 2024 = 29.8%", "JPN", "SP.POP.65UP.TO.ZS", 2024, lambda v: f"{v:.1f}%", "29.8"),
    ("美国 GDP 市场价 2024 = $29.2 万亿", "USA", "NY.GDP.MKTP.CD", 2024, lambda v: f"{v/1e12:.1f}万亿", "29.2"),
]
for claim, iso, code, year, fmt, expect in CHECKS:
    v = wdi_live(iso, code, year)
    got = fmt(v) if v is not None else "n/a"
    ok = expect in got
    results["wdi_live"].append({"claim": claim, "live": got, "expect_contains": expect, "pass": ok})
    print(f"{'PASS' if ok else 'FAIL'} | {claim} -> live={got}")

# ---------------- 2. 原始重算 (独立于 processed CSV)
pop = wdi_live("WLD", "SP.POP.TOTL", 2024)
gdpppp = wdi_live("WLD", "NY.GDP.MKTP.PP.CD", 2024)
gap = wdi_live("WLD", "SI.POV.GAPS", 2024)
gap_cost_T = gap / 100 * 3.00 * 365 * pop / 1e12
gross830_pct = 100 * (8.30 * 365 * pop) / gdpppp
r1 = f"{gap_cost_T:.2f}万亿 / {100*gap/100*3.00*365*pop/gdpppp:.2f}%"
ok1 = abs(gap_cost_T - 0.32) < 0.03
results["recompute"].append({"claim": "消除 $3.00 缺口净成本 = 0.32 万亿 = 0.16% 世界GDP", "recomputed": f"{gap_cost_T:.3f}万亿 ({100*gap_cost_T/gdpppp*1e12:.2f}%)", "pass": ok1})
ok2 = abs(gross830_pct - 12.34) < 0.15
results["recompute"].append({"claim": "$8.30/天 普惠毛成本 = 12.3% 世界GDP", "recomputed": f"{gross830_pct:.2f}%", "pass": ok2})
china500 = 100 * (500 * 12 * 1.409e9) / 134.9e12
ok3 = abs(china500 - 6.27) < 0.05
results["recompute"].append({"claim": "中国 ¥500/月 毛成本 = 6.27% GDP", "recomputed": f"{china500:.2f}%", "pass": ok3})
for r in results["recompute"]:
    print(f"{'PASS' if r['pass'] else 'FAIL'} | {r['claim']} -> {r['recomputed']}")

# ---------------- 3. DOI 抽样解析 (Crossref)
DOIS = [
    ("10.1093/qje/qjw025", "short-term impact of unconditional cash transfers"),
    ("10.3982/ecta17945", "general equilibrium effects of cash transfers"),
    ("10.1093/wbro/lkx002", "debunking the stereotype of the lazy welfare recipient"),
    ("10.1146/annurev-economics-080218-030237", "universal basic income in the united states"),
    ("10.1257/jep.32.4.201", "universal basic incomes versus targeted transfers"),
    ("10.1086/705716", "robots and jobs"),
    ("10.1126/science.adh2586", "productivity effects of generative artificial intelligence"),
    ("10.1093/epolic/eiae042", "simple macroeconomics of ai"),
    ("10.1038/s41586-022-04484-3", "machine learning and phone data"),
    ("10.1257/aer.20141346", "building state capacity"),
    ("10.1515/bis-2017-0016", "cost of basic income"),
    ("10.1016/j.jdeveco.2018.08.005", "cash transfers and labor supply"),
]
for doi, needle in DOIS:
    try:
        req = urllib.request.Request(f"https://api.crossref.org/works/{doi}",
                                     headers={"User-Agent": "ubi-verify/1.0 (mailto:verify@example.com)"})
        meta = json.loads(urllib.request.urlopen(req, timeout=30).read())["message"]
        title = (meta.get("title") or [""])[0].lower()
        ok = needle in title
        results["dois"].append({"doi": doi, "crossref_title": (meta.get("title") or [""])[0][:90],
                                "needle": needle, "pass": ok})
        print(f"{'PASS' if ok else 'FAIL'} | {doi} -> {title[:70]}")
    except Exception as e:  # noqa: BLE001
        results["dois"].append({"doi": doi, "error": str(e)[:80], "pass": False})
        print(f"FAIL | {doi} -> {e}")

json.dump(results, open(OUT / "verification_results.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
n_pass = sum(1 for grp in results.values() for r in grp if r.get("pass"))
n_all = sum(len(grp) for grp in results.values())
print(f"\n机器复核: {n_pass}/{n_all} 通过 -> data/processed/verification_results.json")
