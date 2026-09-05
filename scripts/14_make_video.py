# -*- coding: utf-8 -*-
"""
视频合成 v3: 成熟男声(云野) + 逐句 TTS(字幕精确对齐) + SRT(UTF-8 BOM, 自动折行)
输入: video/narration.md (S1-S11), figures/*.png
输出: video/UBI研究报告视频.mp4, video/subtitles.srt, video/frames/, video/audio/
"""
import asyncio
import hashlib
import re
import wave
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
VID = ROOT / "video"
(VID / "frames").mkdir(parents=True, exist_ok=True)
(VID / "audio").mkdir(parents=True, exist_ok=True)
FIG = ROOT / "figures"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

VOICE = "zh-CN-YunjianNeural"  # 浑厚中年男声(与此前女声截然不同)
RATE = "+0%"
W, H = 1920, 1080
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"
BG = (16, 22, 33)
FG = (238, 242, 245)
ACC = (86, 156, 214)
GAP_SEC = 0.35                # 句间停顿
TAIL_SEC = 0.6                # 场景尾留白
SR = 24000                    # 采样率 24k 单声道 16bit

# ---------------------------------------------------------------- 场景解析
narr = (VID / "narration.md").read_text(encoding="utf-8")
SCENES = []
for b in re.split(r"\n\n(?=S\d+ \|)", narr.strip()):
    lines = [l for l in b.splitlines() if l.strip()]
    if not lines or not re.match(r"S\d+ \|", lines[0]):
        continue
    if int(re.match(r"S(\d+)", lines[0]).group(1)) >= 11:
        continue  # S11+ 由代码生成(文献分页)
    m = re.match(r"S(\d+)\s*\|\s*(.+?)\s*\|\s*(?:([\w/.\\-]+\.png)\s*\|)?", lines[0])
    SCENES.append({"n": int(m.group(1)), "title": m.group(2),
                   "fig": ROOT / m.group(3) if m.group(3) else None,
                   "text": "".join(lines[1:]).strip()})
print(f"解析到 {len(SCENES)} 个场景")

# 案例卡 (S8 荷兰 / S9 澳大利亚): 细节在画面上, 解说保持短句
CASES = {
    8: ("案例 · 荷兰育儿补贴丑闻（2005-2019）", [
        "税务署用自学习算法给申请人打「欺诈风险分」",
        "双重国籍 / 外国姓名 = 高风险信号 → 系统性歧视",
        "约 2.6 万家庭被错误追债（高估计至 3.5 万）",
        "上千名儿童进入寄养家庭，大量家庭负债破产",
        "2021 年 1 月 吕特内阁集体总辞",
        "信源：议会调查报告 · Amnesty《Xenophobic Machines》",
    ]),
    9: ("案例 · 澳大利亚 Robodebt（2016-2019）", [
        "以「收入平均化」自动计算福利债务并追缴",
        "联邦法院判定：做法违法",
        "集体诉讼和解 18 亿澳元（2020-21）",
        "皇家委员会结论（2023）：一场「可耻的失败」",
        "2025 年追加 4.75 亿澳元和解",
        "信源：Royal Commission · Services Australia",
    ]),
}
for s_ in SCENES:
    if s_["n"] in CASES:
        s_["case"] = CASES[s_["n"]]

# ---------------------------------------------------------------- 文献分页场景 (S11-S15, 全名列出)
LIT_SLIDES = [
    (12, "文献与出处 1/4 · 经典理论", "研究一共引用了八十篇文献，全部逐条核验过元数据。第一页是经典理论：从弗里德曼的负所得税，到范·派里斯的真实自由，再到皮凯蒂对财富积累的刻画。", [
        "Friedman（1962）《资本主义与自由》· 第 IX 章 负所得税 · U. Chicago Press",
        "Tobin, Pechman & Mieszkowski（1967）《负所得税可行吗？》· Yale Law Journal",
        "Van Parijs（1995）《给所有人以真实自由》· Oxford University Press",
        "Van Parijs & Vanderborght（2017）《基本收入：一部激进的倡议》· Harvard University Press",
        "Atkinson（1996）《参与收入的理由》· Political Quarterly；Atkinson（2015）《不平等：我们能做什么》",
        "Piketty（2014）《21 世纪资本论》· Harvard University Press；Korpi & Palme（1998）《再分配悖论》· ASR",
    ]),
    (13, "文献与出处 2/4 · 实验与实证", "第二页是实验与实证：加拿大 Mincome、阿拉斯加永久基金分红、芬兰 Kela 实验、肯尼亚 GiveDirectly 的一般均衡研究、伊朗的全国现金转移，以及美国最新的三年无条件现金实验。", [
        "Forget（2011）《没有贫困的城镇》· Canadian Public Policy —— 加拿大 Mincome",
        "Jones & Marinescu（2018/2022）阿拉斯加永久基金分红的劳动市场影响 · NBER 24312 / AEJ: Policy",
        "Kela（2020）芬兰基本收入实验 2017-2018 最终报告 · 芬兰社会保障研究所",
        "Egger, Haushofer, Miguel, Niehaus & Walker（2022）《现金转移的一般均衡效应》· Econometrica",
        "Banerjee, Hanna & Kreindler（2017）《为\"懒穷人\"正名》· WBRO；Salehi-Isfahani（2018）伊朗现金转移 · JDE",
        "OpenResearch（2024）美国三年无条件现金转移研究 · NBER w32784",
    ]),
    (14, "文献与出处 3/4 · 成本与人工智能", "第三页是成本核算与人工智能：从 Hoynes 和 Rothstein 的成本综述、Hanna 和 Olken 的普惠与定向之辩，到 Frey-Osborne 的就业未来、Acemoglu 的 AI 宏观经济学，还有发表在 Science 上的生成式 AI 生产率实验。", [
        "Hoynes & Rothstein（2019）《美国与发达国家的 UBI》· Annual Review of Economics",
        "Hanna & Olken（2018）《普惠还是定向》· JEP；Widerquist（2017）《基本收入的成本》· Basic Income Studies",
        "Frey & Osborne（2017）《就业的未来》· TFSC；Arntz, Gregory & Zierahn（2016）OECD 任务法修正",
        "Acemoglu & Restrepo（2020）《机器人与就业》· JPE；Acemoglu（2025）《AI 的简单宏观经济学》· Economic Policy",
        "Noy & Zhang（2023）生成式 AI 生产率实验 · Science；Brynjolfsson, Li & Raymond（2025）· QJE",
        "Eloundou 等（2024）《GPTs are GPTs》· Science；Briggs & Kodnani（2023）高盛 AI 增长报告",
    ]),
    (15, "文献与出处 4/4 · 治理与数据", "第四页是治理与数据：Hanna 和 Olken 的定向之比较、印度的生物识别智能卡、M-Pesa 的十年研究、Aadhaar 的排斥案例、美国审计署的欺诈报告，以及 ID4D、Findex、ILO 三大数据体系。", [
        "Hanna & Olken（2018）《UBI 与定向转移》· JEP；Muralidharan 等（2016）生物识别智能卡 · AER",
        "Suri & Jack（2016）M-Pesa 十年影响 · Science；Jean 等（2016）卫星+机器学习预测贫困 · Science",
        "Aiken 等（2022）手机数据定向人道主义援助 · Nature；Drèze, Khera & Somanchi（2019）Aadhaar 排斥研究",
        "World Bank ID4D / Global Findex 2025 / ITU Facts & Figures 2024 / ILO WSPR 2024-26",
        "美国 GAO-23-106696 疫情期失业保险欺诈报告；IMF WP/23/169 化石燃料补贴",
        "中国：人社部统计公报 · 社科院《养老金精算报告》· 生态环境部碳市场数据",
    ]),
]
SCENES.append({"n": 11, "title": "谁最可能先发", "fig": FIG / "fig11_scorecard.png",
               "text": "那哪些国家最可能先动？北欧和爱沙尼亚：数字身份覆盖率百分之九十五以上，净成本只占GDP的百分之四到六，技术上明天就能上线。真正的拦路虎是政治。瑞士公投，七成七反对；排在发钱前面的，还有躲不掉的养老金。"})
for n, title, text, _ in LIT_SLIDES:
    SCENES.append({"n": n, "title": title, "fig": None, "text": text, "lit": LIT_SLIDES[[x[0] for x in LIT_SLIDES].index(n)][3]})
SCENES.append({"n": 16, "title": "研究出处 · 数据与代码", "fig": None, "text":
    "最后交代研究出处。本视频的每一句话，都有依据摆在网络上。数据用的是世界银行公开数据、Maddison 两千年经济史，以及公开数据平台。文献方面，弗里德曼、阿西莫格鲁、班纳吉、Hanna 和 Olken 等八十篇论文，逐条核验清单也在仓库里。三份完整报告、全部源码、数据表格和图表，都在 GitHub 仓库，网址就在屏幕右上角，链接也放在视频简介里。欢迎复算。",
    "lit": [
        "报告：主报告 · 26 国高信息化子研究 · 中国专章 · 真实性校验报告",
        "数据：世界银行 WDI 31,656 行 · Maddison 1820-2022 · OWID 劳动份额与碳排放",
        "文献库：sources/core_works_verified.json（80 篇，57 条 OpenAlex 核验）· references.bib",
        "代码与数据：github.com/akisame2023/UBI-research（源码/数据/图表/文献库）",
    ]})
print(f"加入文献分页后共 {len(SCENES)} 个场景")

def split_sentences(text):
    return [p for p in re.split(r"(?<=[。；？！])", text) if p.strip()]

for s in SCENES:
    s["sents"] = split_sentences(s["text"])

# ---------------------------------------------------------------- 音频
async def tts(text, out_mp3):
    import edge_tts
    voices = ["zh-CN-YunjianNeural", "zh-CN-YunjianNeural", "zh-CN-YunyeNeural", "zh-CN-YunyangNeural"]
    last = None
    for attempt in range(4):
        try:
            cm = edge_tts.Communicate(text, voices[min(attempt // 2, 2)], rate=RATE)
            await cm.save(str(out_mp3))
            if out_mp3.stat().st_size > 1500:
                return
            raise RuntimeError("empty audio")
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  tts retry {attempt+1}: {e}", flush=True)
            await asyncio.sleep(2 + attempt * 2)
    raise last

def mp3_to_wav(mp3, wav):
    import subprocess
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(mp3),
                    "-ar", str(SR), "-ac", "1", str(wav)], check=True)

def wav_dur(wav):
    with wave.open(str(wav), "rb") as w:
        return w.getnframes() / w.getframerate()

def silence(sec):
    f = bytearray(int(SR * sec) * 2)
    return bytes(f)

def concat_wavs(wavs, out, tail=TAIL_SEC):
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        for i, p in enumerate(wavs):
            if i:
                w.writeframes(silence(GAP_SEC))
            with wave.open(str(p), "rb") as r:
                w.writeframes(r.readframes(r.getnframes()))
        w.writeframes(silence(tail))

async def gen_audio():
    for s in SCENES:
        s["sent_wavs"], offsets, t = [], [], 0.0
        for j, sent in enumerate(s["sents"]):
            h = hashlib.md5((VOICE + RATE + sent).encode()).hexdigest()[:10]
            mp3 = VID / "audio" / f"s{s['n']:02d}_{j:02d}_{h}.mp3"
            wav = VID / "audio" / f"s{s['n']:02d}_{j:02d}_{h}.wav"
            if wav.exists():
                try:
                    wav_dur(wav)
                except Exception:  # noqa: BLE001
                    wav.unlink()
            if not wav.exists():
                await tts(sent, mp3)
                mp3_to_wav(mp3, wav)
            d = wav_dur(wav)
            offsets.append((t, t + d))
            t += d + GAP_SEC
            s["sent_wavs"].append(str(wav))
        s["offsets"] = offsets
        concat_wavs(s["sent_wavs"], VID / "audio" / f"s{s['n']:02d}.wav")
        s["dur"] = wav_dur(VID / "audio" / f"s{s['n']:02d}.wav")
        print(f"S{s['n']:02d} {s['dur']:.1f}s  {s['title']}  ({len(s['sents'])}句)", flush=True)
    # 全片单条连续音轨: 保证任意时刻音画同步(分段独立编码会累积 AAC 填充漂移)
    with wave.open(str(VID / "audio" / "full.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        for s in SCENES:
            with wave.open(str(VID / "audio" / f"s{s['n']:02d}.wav"), "rb") as r:
                w.writeframes(r.readframes(r.getnframes()))
    print(f"总时长 {sum(s['dur'] for s in SCENES):.0f}s  (full.wav)")

# ---------------------------------------------------------------- 画面
def load_font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)

def fit_image(img, max_w, max_h):
    r = min(max_w / img.width, max_h / img.height)
    return img.resize((int(img.width * r), int(img.height * r)), Image.LANCZOS)

def make_frame(s):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((90, 60), "UBI 研究 · 生产力与治理", font=load_font(30), fill=(120, 140, 160))
    d.text((90, 110), f"{s['n']:02d}  {s['title']}", font=load_font(56, bold=True), fill=ACC)
    d.line((90, 195, W - 90, 195), fill=(60, 75, 95), width=3)
    if s.get("fig") and Path(s["fig"]).exists():
        im = fit_image(Image.open(s["fig"]).convert("RGB"), 1560, 570)
        img.paste(im, ((W - im.width) // 2, 225))
    elif s["n"] == 1:
        d.text((W / 2, 420), "人类的生产力足够 UBI 吗？", font=load_font(88, bold=True), fill=FG, anchor="mm")
        d.text((W / 2, 560), "治理技术上有什么阻碍？", font=load_font(88, bold=True), fill=ACC, anchor="mm")
        d.text((W / 2, 680), "—— 80 篇文献 · 31,656 条世界银行观测 · 26 国与中国专章 ——",
               font=load_font(34), fill=(150, 165, 185), anchor="mm")
    elif s.get("case"):
        title, lines = s["case"]
        d.text((W / 2 - 830, 250), title, font=load_font(44, bold=True), fill=(220, 170, 110))
        y = 370
        for line in lines:
            fb = load_font(33)
            while d.textlength("· " + line, font=fb) > 1680 and fb.size > 24:
                fb = load_font(fb.size - 2)
            d.text((W / 2 - 830, y), "· " + line, font=fb, fill=FG)
            y += 58
    elif s.get("lit"):
        f_h = load_font(40, bold=True)
        y = 250
        for line in s["lit"]:
            fb = load_font(33)
            head_like = line.startswith(("报告", "数据", "文献库", "代码与数据"))
            fnt = load_font(36, bold=True) if head_like else fb
            while d.textlength(line, font=fnt) > 1660 and fnt.size > 23:
                fnt = load_font(fnt.size - 2)
            d.text((W / 2 - 830, y), line, font=fnt, fill=ACC if head_like else FG)
            y += 52
    elif s["n"] == 1:
        d.text((W / 2, 420), "人类的生产力足够 UBI 吗？", font=load_font(88, bold=True), fill=FG, anchor="mm")
        d.text((W / 2, 560), "治理技术上有什么阻碍？", font=load_font(88, bold=True), fill=ACC, anchor="mm")
        d.text((W / 2, 680), "—— 80 篇文献 · 31,656 条世界银行观测 · 26 国与中国专章 ——",
               font=load_font(34), fill=(150, 165, 185), anchor="mm")
    elif s["n"] == 10:
        d.text((W / 2, 260), "总结：UBI 是一道权衡题", font=load_font(56, bold=True), fill=FG, anchor="mm")
        d.text((W / 2, 340), "不是送分题，也不是一票否决题", font=load_font(38), fill=(160, 175, 195), anchor="mm")
        f_h, f_b = load_font(38, bold=True), load_font(31)
        d.text((W / 2 - 720, 420), "社会效益（实证支持）", font=f_h, fill=(110, 190, 130))
        for i, line in enumerate(["贫困与健康显著改善（Mincome/Kela）",
                                   "穷人议价能力更强，可拒绝恶性雇佣",
                                   "福利行政简化，无算法排斥",
                                   "危机时期的自动稳定器"]):
            d.text((W / 2 - 720, 486 + i * 52), "＋ " + line, font=f_b, fill=FG)
        d.text((W / 2 + 60, 420), "代价与风险（同样真实）", font=f_h, fill=(220, 120, 110))
        for i, line in enumerate(["财政负担与税收扭曲",
                                   "少数人工时下降（OpenResearch -5%）",
                                   "替换定向体系可能伤及最困难者",
                                   "通胀/租金效应与机会成本未定"]):
            d.text((W / 2 + 60, 486 + i * 52), "− " + line, font=f_b, fill=FG)
        d.text((W / 2, 760), "效益、成本、机会成本放在一起称 ——", font=load_font(38), fill=FG, anchor="mm")
        d.text((W / 2, 830), "每个社会根据自己的财政空间和价值观做判断；研究负责把两边的量级算清楚",
               font=load_font(33), fill=(200, 205, 160), anchor="mm")
    d.text((W - 90, 30), "代码与数据 · github.com/akisame2023/UBI-research",
           font=load_font(24), fill=(110, 128, 150), anchor="rm")
    out = VID / "frames" / f"s{s['n']:02d}.png"
    img.save(out)
    s["frame"] = str(out)

# ---------------------------------------------------------------- SRT (精确逐句 + BOM + 折行)
def fmt_tsec(t):
    h, m, sec = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", ",")

def wrap2(sent, limit=24):
    if len(sent) <= limit:
        return sent
    cut = sent.rfind("，", 0, len(sent) // 2 + 6)
    if cut <= 0:
        cut = len(sent) // 2
    return sent[:cut + 1] + "\n" + sent[cut + 1:]

def make_srt():
    t0, idx, lines = 0.0, 1, []
    for s in SCENES:
        for (a, b), sent in zip(s["offsets"], s["sents"]):
            lines.append(f"{idx}\n{fmt_tsec(t0+a)} --> {fmt_tsec(t0+b)}\n{wrap2(sent.strip())}\n")
            idx += 1
        t0 += s["dur"]
    (VID / "UBI研究报告视频.srt").write_text("\n".join(lines), encoding="utf-8-sig")  # BOM: 防 Windows 播放器乱码
    print(f"SRT: {idx-1} 条字幕 (UTF-8 BOM, 逐句精确对齐)")

# ---------------------------------------------------------------- 合成
def run(cmd):
    import subprocess
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-1200:])

def render():
    parts = []
    for s in SCENES:
        out = VID / f"part{s['n']:02d}.mp4"
        dur = s["dur"]
        run([FFMPEG, "-y", "-loglevel", "error",
             "-loop", "1", "-i", s["frame"], "-t", f"{dur:.2f}",
             "-vf", f"scale=1920:1080,fade=t=in:st=0:d=0.45,fade=t=out:st={max(dur-0.5,0):.2f}:d=0.45,format=yuv420p",
             "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-r", "30",
             "-an", str(out)])
        parts.append(out)
    lst = VID / "concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    silent = VID / "silent.mp4"
    run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(silent)])
    final = VID / "UBI研究报告视频.mp4"
    run([FFMPEG, "-y", "-loglevel", "error", "-i", str(silent),
         "-i", str(VID / "audio" / "full.wav"),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(final)])
    print("FINAL:", final, f"{final.stat().st_size/1e6:.1f} MB")
    for p in parts:
        p.unlink(missing_ok=True)

async def main():
    await gen_audio()
    for s in SCENES:
        make_frame(s)
    make_srt()
    render()

if __name__ == "__main__":
    asyncio.run(main())
