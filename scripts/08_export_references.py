# -*- coding: utf-8 -*-
"""从 core_works_verified.json 导出 sources/references.md (按主题分组) 与 sources/references.bib"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
works = json.load(open(ROOT / "sources" / "core_works_verified.json", encoding="utf-8"))

THEME_NAMES = {
    "classic": "A. 经典理论",
    "experiments": "B. 实验与实证证据",
    "cost": "C. 成本核算与融资",
    "ai": "D. 自动化、AI 与生产率",
    "governance": "E. 治理技术与国家能力",
    "data": "F. 数据来源",
}

def fmt_authors(a):
    if not a:
        return ""
    parts = [x.strip() for x in a.split(";") if x.strip()]
    if len(parts) > 3:
        return f"{parts[0]} et al."
    return ", ".join(parts)

lines = ["# 参考文献（核心文献库，共 80 条）", "",
         "检索与核验：OpenAlex API 标题级匹配（2026-09-04），57 条经 API 核验，23 条为手工核验条目"
         "（图书/机构报告/工作论文，OpenAlex 无独立记录）。引用数 = OpenAlex 收录的 cited_by_count。", ""]
bib = []
n = 0
for theme in ["classic", "experiments", "cost", "ai", "governance", "data"]:
    grp = [w for w in works if w["theme"] == theme]
    grp.sort(key=lambda w: -(w.get("citations") or 0))
    lines.append(f"## {THEME_NAMES[theme]}")
    lines.append("")
    for w in grp:
        n += 1
        a = fmt_authors(w.get("authors", ""))
        y = w.get("year") or "n.d."
        v = w.get("venue") or ""
        c = w.get("citations")
        doi = w.get("doi") or ""
        flag = "" if w.get("verified") == "openalex" else "〔手工核验〕"
        if a:
            cite = f"{a} ({y}). *{w['title']}*. {v}." if v else f"{a} ({y}). *{w['title']}*."
        else:
            # 手工条目标题已含作者与年份
            cite = f"*{w['title']}*."
        if doi:
            cite += f" https://doi.org/{doi}"
        if c:
            cite += f" 〔被引 {c}〕"
        cite += flag
        lines.append(f"{n}. {cite}")
        bib.append((w["key"], w["title"], a, y, v, doi))
    lines.append("")

(ROOT / "sources" / "references.md").write_text("\n".join(lines), encoding="utf-8")

with open(ROOT / "sources" / "references.bib", "w", encoding="utf-8") as f:
    for key, title, authors, year, venue, doi in bib:
        clean = authors.replace("; ", " and ")
        f.write(f"@misc{{{key},\n  title = {{{title}}},\n  author = {{{clean}}},\n  year = {{{year}}},\n")
        if venue:
            f.write(f"  howpublished = {{{venue}}},\n")
        if doi:
            f.write(f"  doi = {{{doi}}},\n")
        f.write("}\n")

print(f"exported {n} references -> sources/references.md, sources/references.bib")
