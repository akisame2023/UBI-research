# -*- coding: utf-8 -*-
"""
UBI 研究 —— 文献检索脚本 (OpenAlex API)
按 5 大主题做定向检索, 原始结果存 sources/openalex_searches.json,
去重目录存 sources/literature_catalog.csv。
检索日期: 2026-09-04
"""
import json
import csv
import time
import urllib.request
import urllib.parse
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "sources"
SRC.mkdir(parents=True, exist_ok=True)

THEMES = {
    # A. 经典理论
    "classic_theory": [
        "Real Freedom for All what if just pay",
        "Basic Income a radical proposal Van Parijs",
        "negative income tax Friedman capitalism freedom",
        "Inequality What Can Be Done Atkinson participation income",
        "Progress and Poverty Henry George land dividend",
        "Higher Production by a Bonus on National Output Milner 1920",
        "social dividend Meade agathotopia",
        "Capital in the Twenty-First Century Piketty",
    ],
    # B. 实验证据
    "experiments": [
        "Alaska Permanent Fund dividend employment labor supply",
        "The Town with No Poverty health Mincome Manitoba Forget",
        "Finland basic income experiment Kela results wellbeing employment",
        "general equilibrium effects of cash transfers Kenya Egger Haushofer",
        "Stockton SEED basic income economic mobility West",
        "OpenResearch unconditional cash transfers three-year US study",
        "Iran subsidy reform cash transfers labor Salehi-Isfahani",
        "Debunking stereotype lazy welfare recipient cash transfers labor supply",
        "child tax credit monthly payments poverty employment 2021",
        "GiveDirectly long-term effects large unconditional cash transfers",
        "Ontario basic income pilot cancellation",
        "Namibia basic income grant Otjivero evaluation",
        "Madhya Pradesh unconditional cash transfers SEWA pilot",
    ],
    # C. 成本与融资
    "cost_financing": [
        "cost of universal basic income Widerquist",
        "OECD basic income as a policy option can it work",
        "universal basic income developing countries IMF options illustration Coady Prady",
        "universal basic income versus targeted transfers state capacity Hanna Olken",
        "financing social protection floors ILO cost",
        "universal basic income proposals ILO standards Ortiz",
        "UBI cost net transfers microsimulation Torry",
        "Roosevelt Institute modeling macroeconomic effects universal basic income Nikiforos",
    ],
    # D. 自动化/AI/生产率
    "automation_ai": [
        "future of employment computerisation susceptible Frey Osborne",
        "Robots and Jobs Evidence from US Labor Markets Acemoglu Restrepo",
        "relative demand negative effects technology structure employment tasks",
        "risk of automation OECD jobs Arntz Gregory Zierahn",
        "GPTs are GPTs large language models labor market exposure",
        "simple macroeconomics of AI Acemoglu",
        "generative AI at work call center productivity Brynjolfsson",
        "experimental evidence GitHub Copilot productivity Peng",
        "jagged technological frontier field experimental evidence consultants generative AI",
        "Navigating jagged frontier professional tasks generative AI Noy Zhang writing",
        "generative AI and future of work IMF employment exposure Cazzaniga",
        "weaving automation skill complementary tasks global perspective Webb",
        "robots and jobs manufacturing labor share Graetz Michaels productivity",
        "fall of labor share rise of superstar firms Autor Dorn Katz",
        "global inequality of labor income share capital Karabarbounis Neiman",
        "power and productivity in era of automation under new deal",
        "AI and productivity Goldman Sachs generative raises global GDP",
    ],
    # E. 治理技术
    "governance_tech": [
        "identification development coverage World Bank ID4D people without ID",
        "Global Findex database financial inclusion unbanked adults Demirguc-Kunt",
        "Aadhaar exclusion welfare beneficiaries Khera Dreze right to die",
        "biometric smartcards leakage Muralidharan Niehaus Sukhtankar",
        "proxy means testing targeting errors Alatas Indonesia",
        "M-Pesa financial inclusion poverty Suri Jack mobile money",
        "machine learning satellite poverty targeting cash transfers Blumenstock",
        "digital payments government transfers COVID last mile evidence",
        "unemployment insurance fraud COVID improper payments GAO",
        "universal basic income inflation prices general equilibrium village",
        "mobile money cash transfer delivery costs governance developing countries",
        "state capacity fiscal capacity development Besley Persson",
    ],
}

def oa_search(search: str, per_page: int = 6):
    q = urllib.parse.quote(search)
    url = (f"https://api.openalex.org/works?search={q}&per-page={per_page}"
           f"&mailto=ubiresearch@example.com")
    req = urllib.request.Request(url, headers={"User-Agent": "ubi-research/1.0"})
    d = json.loads(urllib.request.urlopen(req, timeout=40).read())
    out = []
    for w in d.get("results", []):
        loc = w.get("primary_location") or {}
        src = (loc.get("source") or {}).get("display_name", "")
        out.append({
            "query": search,
            "year": w.get("publication_year"),
            "title": w.get("title"),
            "authors": "; ".join(a["author"]["display_name"] for a in w.get("authorships", [])[:6]),
            "venue": src,
            "citations": w.get("cited_by_count"),
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "openalex_id": (w.get("id") or "").split("/")[-1],
            "type": w.get("type"),
        })
    return out

def main():
    all_results = []
    for theme, queries in THEMES.items():
        print(f"=== {theme} ===")
        for q in queries:
            try:
                res = oa_search(q)
                print(f"  [{len(res):2d}] {q}")
                all_results.extend(res)
                time.sleep(0.25)
            except Exception as e:  # noqa: BLE001
                print(f"  FAILED: {q} -> {e}")
    # 保存原始结果
    with open(SRC / "openalex_searches.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=1)
    # 去重目录(按 openalex_id)
    seen = {}
    for r in all_results:
        if not r["title"]:
            continue
        key = r["openalex_id"]
        if key not in seen or (r["citations"] or 0) > (seen[key]["citations"] or 0):
            seen[key] = r
    catalog = sorted(seen.values(), key=lambda r: -(r["citations"] or 0))
    with open(SRC / "literature_catalog.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["theme_year", "citations", "title", "authors", "venue", "doi", "openalex_id", "type", "query"])
        w.writeheader()
        for r in catalog:
            w.writerow({**r, "theme_year": r["year"]})
    print(f"\nsaved sources/openalex_searches.json ({len(all_results)} hits, "
          f"{len(catalog)} unique works)")

if __name__ == "__main__":
    main()
