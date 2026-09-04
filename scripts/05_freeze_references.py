# -*- coding: utf-8 -*-
"""最终文献库冻结: 剩余条目转手工核验并补齐关键条目。"""
import json
from pathlib import Path

p = Path("sources/core_works_verified.json")
works = json.load(open(p, encoding="utf-8"))
by_key = {w["key"]: w for w in works}

def manual(key, theme, title, venue, year, note=""):
    return {"key": key, "theme": theme, "verified": "manual", "year": year,
            "title": title, "query_title": "", "note": note, "authors": "",
            "venue": venue, "doi": "", "citations": None, "openalex_id": "",
            "type": "manual"}

by_key["jones2022alaska"] = manual(
    "jones2022alaska", "experiments",
    "Jones, D. & Marinescu, I. (2018/2022). 'The Labor Market Impacts of a Universal and Permanent Basic Income: Evidence from the Alaska Permanent Fund'. NBER WP 24318 —— 就业无显著下降, 兼职就业率 +1.8pp",
    "NBER Working Paper 24318", 2018)

by_key["pilkauskas2022"] = manual(
    "ctc2022", "experiments",
    "Parolin, Z., Ananat, E., Collyer, S., Curran, M. & Wimer, C. (2021-2023) 系列 + 美国人口普查局 SPM: 2021 年月度儿童税收抵免使儿童贫困率降至 5.2% 的历史低点; 2022 年到期后回升至 12.4%",
    "Columbia CSPD / NBER / Census SPM", 2022,
    "到期后就业未出现显著回升, 不支持福利依赖假说")

by_key["nikiforos2017"] = manual(
    "nikiforos2017", "cost",
    "Nikiforos, M., Steinbaum, L. & Zezza, G. (2017). 'Modeling the Macroeconomic Effects of a Universal Basic Income'. Roosevelt Institute —— Levy 模型: 不同融资方式下 1 万美元/年 UBI 使 GDP 增长 ~3-12.6%",
    "Roosevelt Institute Report", 2017)

by_key["duranvalverde2019"] = manual(
    "duranvalverde2019", "cost",
    "Durán-Valverde, F., Pacheco, J.F. et al. (2019). 'Financing gaps in social protection floors: A global rough estimate'. ILO Working Paper —— 低收入国家建立社保底线需新增 GDP 的 5-15% 量级",
    "ILO Working Paper", 2019)

by_key["zucman2019"] = manual(
    "zucman2019", "classic",
    "Zucman, E. (2019). 'Global Wealth Inequality'. Annual Review of Economics 11: 109-132 —— 全球家庭财富数百万亿美元, 集中度远高于收入",
    "Annual Review of Economics", 2019)

if "drezekhera2019" in by_key and by_key["drezekhera2019"].get("verified") == "openalex":
    w = by_key.pop("drezekhera2019")
    w["key"] = "dixon2017aadhaar"
    w["note"] = "World Privacy Forum 评估: Aadhaar 生物识别去重导致的福利排除风险 (Do No Harm 失败)"
    by_key["dixon2017aadhaar"] = w

by_key["dreze2019aadhaar"] = manual(
    "dreze2019aadhaar", "governance",
    "Drèze, J., Khera, R. & Somanchi, A. (2019). 'Aadhaar and Food Security in Jharkhand: Pain without Gain?' —— 生物识别认证造成 2-6% 合格受益人被系统性排除, 且未减少虚假领取",
    "SSRN / Ranchi 报告", 2019)

by_key["atkinson1995"] = manual(
    "atkinson1995", "classic",
    "Atkinson, A. B. (1995). 'Public Economics in Action: The Basic Income / Flat Tax Proposal'. Oxford University Press —— 经典的 BI+单一税财政一致性框架",
    "Oxford University Press", 1995)

works = list(by_key.values())
json.dump(works, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
ok = sum(1 for r in works if r.get("verified") == "openalex")
themes = {}
for r in works:
    themes[r["theme"]] = themes.get(r["theme"], 0) + 1
print(f"FROZEN: {len(works)} works ({ok} openalex-verified, {len(works)-ok} manual), by theme: {themes}")
