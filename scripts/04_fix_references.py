# -*- coding: utf-8 -*-
"""二轮修复: 补齐/纠正 core_works_verified.json 中的问题条目。"""
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "sources"
p = SRC / "core_works_verified.json"
works = json.load(open(p, encoding="utf-8"))
by_key = {w["key"]: w for w in works}

def oa(filter_str, per_page=5, search=None):
    base = "https://api.openalex.org/works?per-page=%d&mailto=ubiresearch@example.com" % per_page
    if search:
        base += "&search=" + urllib.parse.quote(search)
    url = base + "&filter=" + urllib.parse.quote(filter_str)
    req = urllib.request.Request(url, headers={"User-Agent": "ubi-research/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=40).read()).get("results", [])

def make_rec(key, theme, w, note=""):
    loc = w.get("primary_location") or {}
    return {"key": key, "theme": theme, "query_title": w.get("title"), "note": note,
            "verified": "openalex", "year": w.get("publication_year"),
            "title": w.get("title"),
            "authors": "; ".join(a["author"]["display_name"] for a in w.get("authorships", [])[:8]),
            "venue": (loc.get("source") or {}).get("display_name", ""),
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "citations": w.get("cited_by_count"),
            "openalex_id": (w.get("id") or "").split("/")[-1], "type": w.get("type")}

def manual(key, theme, title, venue, year=None):
    return {"key": key, "theme": theme, "query_title": title, "note": "",
            "verified": "manual", "year": year, "title": title, "authors": "",
            "venue": venue, "doi": "", "citations": None, "openalex_id": "", "type": "report"}

FIX = {}
queries = [
    ("tobin1967", "classic", "raw_author_name.search:tobin,title.search:negative income tax practical", None),
    ("atkinson2015", "classic", "title.search:Inequality What Can Be Done Atkinson", None),
    ("frey2017", "ai", "raw_author_name.search:frey,title.search:future of employment computerisation", None),
    ("autor2015", "ai", "raw_author_name.search:autor,title.search:why are there still so many jobs", None),
    ("jones2022alaska", "experiments", "title.search:labor market impacts universal permanent basic income Alaska", None),
    ("pilkauskas2022", "experiments", "search:child tax credit 2021 monthly effects poverty employment", None),
    ("nikiforos2017", "cost", "search:modeling the macroeconomic effects of a universal basic income", None),
    ("duranvalverde2019", "cost", "search:financing gaps social protection floors ILO", None),
    ("drezekhera2019", "governance", "search:Aadhaar food security Jharkhand exclusion", None),
    ("zucman2019", "classic", "raw_author_name.search:zucman,title.search:global wealth inequality", None),
    ("korpi1998", "classic", "raw_author_name.search:korpi,title.search:paradox of redistribution", None),
]
for key, theme, filt, _ in queries:
    try:
        res = oa(filt)
        if res:
            best = max(res, key=lambda w: w.get("cited_by_count", 0))
            FIX[key] = make_rec(key, theme, best)
            r = FIX[key]
            print(f"{key:22s} OK {r['year']} c={r['citations']:>6} {r['title'][:65]} | {r['venue'][:25]}")
        else:
            print(f"{key:22s} NO HITS")
    except Exception as e:  # noqa: BLE001
        print(f"{key:22s} ERROR {e}")
    time.sleep(0.2)

# 无法核验的 -> manual
FIX["george1879"] = manual("george1879", "classic",
    "George, H. (1879). Progress and Poverty: An Inquiry into the Cause of Industrial Depressions and of Increase of Want with Increase of Wealth", "D. Appleton & Co.", 1879)
FIX["meade1972"] = manual("meade1972", "classic",
    "Meade, J. E. (1972). 'Poverty in the Welfare State'. Oxford Economic Papers 24(3) — 社会分红(social dividend)方案", "Oxford Economic Papers", 1972)
FIX["oecd2017"] = manual("oecd2017", "cost",
    "OECD (2017). 'Basic income as a policy option: Can it work?' — 静态微观模拟: 净成本达 GDP 的 8-12% 量级且减贫效率低于现有体系", "OECD Policy Brief / Immervoll & Pearson background", 2017)
FIX["briggs2023"] = manual("briggs2023", "ai",
    "Briggs, J. & Kodnani, D. (2023). 'The Potentially Large Effects of Artificial Intelligence on Economic Growth' — 10 年内全球 GDP +7% (~7 万亿美元), 劳动生产率 +1.5pp/年", "Goldman Sachs Global Economics Analyst", 2023)
FIX["west2021stockton"] = manual("west2021stockton", "experiments",
    "West, S., Castro Baker, A., Samra, S. & Colton, C. (2021). 'Stockton SEED: Preliminary Analysis, First Twelve Months' — 全职就业 +12pp, 受助者福祉改善", "Stockton SEED / University of Tennessee", 2021)

# 年份/字段纠正
if "vanparijs2017" in by_key:
    by_key["vanparijs2017"]["year"] = 2017
    by_key["vanparijs2017"]["note"] = "Harvard University Press, 2017 (平装 2019)"
if "friedman1962" in by_key:
    by_key["friedman1962"]["year"] = 1962
    by_key["friedman1962"]["note"] = "University of Chicago Press 1962 初版; 第IX章 负所得税"
if "cazzaniga2024" in by_key:
    by_key["cazzaniga2024"]["year"] = 2024
    by_key["cazzaniga2024"]["venue"] = "IMF Staff Discussion Note SDN/2024/001"
if "webb2020" in by_key:
    by_key["webb2020"]["key"] = "webb2019jep"
    by_key["webb2020"]["note"] = "JEP 33(2) 'Artificial Intelligence: The Ambiguous Labor Market Impact of Automating Prediction'"
if "vanparijs1995" in by_key:
    by_key["vanparijs1995"]["year"] = 1995
    by_key["vanparijs1995"]["note"] = "Oxford University Press, 1995"

for k, v in FIX.items():
    by_key[k] = v
merged = list(by_key.values())
json.dump(merged, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
ok = sum(1 for r in merged if r.get("verified") == "openalex")
print(f"\nfinal: {len(merged)} works ({ok} openalex-verified, {len(merged)-ok} manual)")
