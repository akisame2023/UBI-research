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
    m = re.match(r"S(\d+)\s*\|\s*(.+?)\s*\|\s*(?:([\w/.\\-]+\.png)\s*\|)?", lines[0])
    SCENES.append({"n": int(m.group(1)), "title": m.group(2),
                   "fig": ROOT / m.group(3) if m.group(3) else None,
                   "text": "".join(lines[1:]).strip()})
print(f"解析到 {len(SCENES)} 个场景")

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
    print(f"总时长 {sum(s['dur'] for s in SCENES):.0f}s")

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
        im = fit_image(Image.open(s["fig"]).convert("RGB"), 1620, 660)
        img.paste(im, ((W - im.width) // 2, 240))
    elif s["n"] == 1:
        d.text((W / 2, 420), "人类的生产力足够 UBI 吗？", font=load_font(88, bold=True), fill=FG, anchor="mm")
        d.text((W / 2, 560), "治理技术上有什么阻碍？", font=load_font(88, bold=True), fill=ACC, anchor="mm")
        d.text((W / 2, 680), "—— 80 篇文献 · 31,656 条世界银行观测 · 26 国与中国专章 ——",
               font=load_font(34), fill=(150, 165, 185), anchor="mm")
    elif s["n"] == 10:
        d.text((W / 2, 380), "生产率：一百年前就够用了", font=load_font(80, bold=True), fill=FG, anchor="mm")
        d.text((W / 2, 530), "拦路的只有两件事：", font=load_font(56), fill=(160, 175, 195), anchor="mm")
        d.text((W / 2, 630), "钱从谁身上来（政治）", font=load_font(66, bold=True), fill=ACC, anchor="mm")
        d.text((W / 2, 730), "钱怎么准确、可持续地到人手里（治理）", font=load_font(66, bold=True), fill=ACC, anchor="mm")
    else:
        f_h, f_b = load_font(42, bold=True), load_font(33)
        y = 250
        for head, bodies in [
            ("报告", ["主报告 · 26 国高信息化子研究 · 中国专章 · 真实性校验报告"]),
            ("数据", ["世界银行 WDI 31,656 行 · Maddison 1820-2022 · OWID 劳动份额与碳排放"]),
            ("文献", ["经典: Friedman · Tobin · Van Parijs · Atkinson · Piketty",
                      "实证: Banerjee · Egger · Jones & Marinescu · Forget（Mincome）",
                      "AI: Acemoglu · Frey & Osborne · Brynjolfsson · Eloundou（Science）",
                      "治理: Hanna & Olken · Muralidharan · Suri & Jack · ID4D/Findex"]),
            ("代码与数据", ["github.com/akisame2023/UBI-research（源码/数据/图表/文献库）"]),
        ]:
            d.text((W / 2 - 740, y), head, font=f_h, fill=ACC)
            y += 58
            for line in bodies:
                d.text((W / 2 - 740, y), line, font=f_b, fill=FG)
                y += 46
            y += 22
    d.rectangle((0, H - 150, W, H), fill=(10, 14, 21))
    sub = s["text"][:44] + ("…" if len(s["text"]) > 44 else "")
    d.text((W / 2, H - 78), sub, font=load_font(40, bold=True), fill=FG, anchor="mm")
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
             "-loop", "1", "-i", s["frame"], "-i", str(VID / "audio" / f"s{s['n']:02d}.wav"),
             "-t", f"{dur:.2f}",
             "-vf", f"scale=1920:1080,fade=t=in:st=0:d=0.45,fade=t=out:st={max(dur-0.5,0):.2f}:d=0.45,format=yuv420p",
             "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-r", "30",
             "-c:a", "aac", "-b:a", "128k", str(out)])
        parts.append(out)
    lst = VID / "concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    final = VID / "UBI研究报告视频.mp4"
    run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(final)])
    print("FINAL:", final, f"{final.stat().st_size/1e6:.1f} MB")
    for p in parts:
        p.unlink()

async def main():
    await gen_audio()
    for s in SCENES:
        make_frame(s)
    make_srt()
    render()

if __name__ == "__main__":
    asyncio.run(main())
