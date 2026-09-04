# UBI 研究：人类的生产力足够 UBI 了吗？治理技术上有什么阻碍？

> 系统性研究项目 · 2026-09-04 · 全流程可复现

**主报告**：[UBI研究报告.md](UBI研究报告.md)
**子研究**：[高信息化国家UBI可行性研究.md](高信息化国家UBI可行性研究.md)（26 国数字就绪度 × 财政空间，含 toeslagenaffaire/Robodebt 治理案例、老龄化挤压与融资菜单量化）
**中国专章**：[中国UBI可行性分析.md](中国UBI可行性分析.md)（¥200-1000/月方案成本、城乡居民基础养老金提标路径、碳税融资菜单）
**真实性校验**：[校验报告.md](校验报告.md)（实时 API 复算 + Crossref DOI 解析 + 事实二次核验 + A/B/C 置信度分级披露；脚本 scripts/13_verify.py）
**视频**：[video/UBI研究报告视频.mp4](video/UBI研究报告视频.mp4)（4 分 33 秒，1080p，10 场景中文旁白 + 46 条 SRT 字幕 [video/subtitles.srt](video/subtitles.srt)；旁白文稿 [video/narration.md](video/narration.md)；复现 scripts/14_make_video.py）

## 核心结论（TL;DR）

1. **总量充足**：把每个人补到 $3.00/天（2021 PPP 极端贫困线）的净成本仅 **0.16% 世界 GDP**；$8.30/天 普惠毛成本 **12.3% 世界 GDP** ≈ 全球现行社保支出占比（12.9%，ILO）。生产率的总量门槛在工业革命以来早已越过。
2. **结构错配**：$8.30/天 普惠成本占本国 GDP——美国 3.5%、德国 4.1%、中国 11.2%、印度 28.3%、肯尼亚 45.6%、巴基斯坦 48.4%。低收入国家无法自筹，**全球可行 ≠ 国家可行**。
3. **恒等式警示**：随收入指数化的 UBI（B=α×人均收入）成本占比恒等于 α，**任何生产率增长（含 AI 乐观情景）都不能降低相对型 UBI 的成本份额**；固定水平 UBI 在基准增长下 2031-2045 年降到 10% GDP 以内。
4. **治理是紧约束**：无证件 8 亿、无账户 13 亿、离线 26 亿、无电力 6.6 亿；穷国税基 10-15% GDP；欺诈-排斥-隐私三角与政治可持续性（瑞士公投 76.9% 否决、OpenResearch 就业 -2pp）是比生产率更硬的约束。

## 复现步骤

```bash
python scripts/01_fetch_data.py        # 1. 下载 WDI(36指标×33国)+OWID 数据 → data/raw/
python scripts/02_fetch_literature.py  # 2. OpenAlex 主题检索 → sources/
python scripts/03_verify_core_works.py # 3. 80 篇核心文献标题级核验
python scripts/04_fix_references.py    # 4. 引用条目修正（一轮）
python scripts/05_freeze_references.py # 5. 文献库冻结
python scripts/06_analysis.py          # 6. 全部分析（报告数字来源，日志 analysis_log.txt）
python scripts/07_figures.py           # 7. 8 张图 → figures/
python scripts/08_export_references.py # 8. 参考文献 BibTeX/Markdown
```

依赖：Python ≥3.10，`pandas` `numpy` `scipy` `matplotlib`（中文渲染使用 Windows 自带 Microsoft YaHei）。

## 目录

| 路径 | 内容 |
|---|---|
| `UBI研究报告.md` | 主报告（含 8 图、6 表、不确定性讨论） |
| `data/raw/` | 原始数据：`wdi_panel.csv`（31,656 行）、`owid_maddison_gdppc.csv`（21,587 行）、`owid_labor_share.csv` |
| `data/processed/` | 结果表 `01`-`07`（报告全部表格的直接来源）+ `analysis_log.txt` |
| `sources/core_works_verified.json` | 80 篇核心文献元数据（57 条 OpenAlex 逐条核验 + 23 条手工核验） |
| `sources/openalex_searches.json` / `literature_catalog.csv` | 348 条检索命中 / 282 条去重目录 |
| `sources/facts_verified.md` | 14 项关键事实的网络核验档案（Findex/ITU/ID4D/GAO/ILO/IMF/UBS/OpenResearch 等） |
| `sources/references.md` / `.bib` | 参考文献列表（按主题分组、含 DOI 与被引数）/ BibTeX |
| `figures/fig1-8*.png` | 报告插图（300 dpi，中文，经三轮视觉验收） |

## 方法要点

- **口径**：世界银行 2025-06 起的 2021 PPP 贫困线（$3.00 / $4.20 / $8.30 每人每天）。
- **净成本模型**：`净转移成本 = k(Gini) × 毛成本`，其中 k = E[(1−Y/μ)⁺]，Y~LogN(μ, σ(Gini))；对收入水平尺度不变。成本谱系：消除贫困缺口（下限）←→ 比例税回收 ←→ 零回收毛额。
- **动态路径**：Maddison 1820-2022（锚定换算 2021 PPP）+ WDI 2024；四种增长情景含 AI 保守（Acemoglu：TFP 10 年 +0.66%）与乐观（Goldman Sachs：10 年 GDP +7%）两端。
- **诚实性**：所有报告数字可在 `data/processed/` 与 `analysis_log.txt` 中逐一对账；数据年份混合、WDI 税收口径、参数近似等局限见报告 §5。
