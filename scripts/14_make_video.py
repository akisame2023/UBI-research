# -*- coding: utf-8 -*-
"""
根据报告制作视频: 分镜(PIL 1920x1080) + edge-tts 中文旁白 + ffmpeg 合成 MP4 + SRT 字幕
输入: video/narration.md (S1-S10 场景), figures/*.png
输出: video/UBI研究报告视频.mp4, video/subtitles.srt, video/frames/*.png, video/audio/*.wav
"""
import asyncio
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

VOICE = "zh-CN-XiaoyiNeural"   # 哈基米风格: 萌系活泼女声
RATE = "+12%"
HAKIMI_PITCH = 1.28            # 升调 1.28x + 变速 -> 高音萌系"哈基米"效果
W, H = 1920, 1080
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"
BG = (16, 22, 33)
FG = (238, 242, 245)
ACC = (86, 156, 214)

# ---------------------------------------------------------------- 场景解析
narr = (VID / "narration.md").read_text(encoding="utf-8")
SCENES = []
blocks = re.split(r"\n\n(?=S\d+ \|)", narr.strip())
for b in blocks:
    lines = [l for l in b.splitlines() if l.strip()]
    if not lines or not re.match(r"S\d+ \|", lines[0]):
        continue  # 跳过文件头注释
    m = re.match(r"S(\d+)\s*\|\s*(.+?)\s*\|\s*(?:([\w/.\\-]+\.png)\s*\|)?", lines[0])
    num = int(m.group(1))
    title = m.group(2)
    fig = ROOT / m.group(3) if m.group(3) else None
    text = "".join(lines[1:]).strip()
    SCENES.append({"n": num, "title": title, "fig": fig, "text": text})
print(f"解析到 {len(SCENES)} 个场景")

# ---------------------------------------------------------------- TTS
async def tts(text, out_mp3):
    import edge_tts
    voices = ["zh-CN-XiaoyiNeural"] * 4 + ["zh-CN-XiaoxiaoNeural"]
    last = None
    for attempt in range(4):
        try:
            cm = edge_tts.Communicate(text, voices[min(attempt, 2)], rate=RATE)
            await cm.save(str(out_mp3))
            if out_mp3.stat().st_size > 2000:
                return
            raise RuntimeError("empty audio")
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  tts retry {attempt+1}: {e}", flush=True)
            await asyncio.sleep(3 + attempt * 3)
    raise last

def mp3_to_wav(mp3, wav):
    # ffmpeg mp3 -> 24k mono wav; 哈基米模式: asetrate 升调+提速(经典 chipmunk 效果)
    import subprocess
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(mp3),
                    "-af", f"asetrate=24000*{HAKIMI_PITCH},aresample=24000",
                    "-ar", "24000", "-ac", "1", str(wav)], check=True)

def wav_dur(wav):
    with wave.open(str(wav), "rb") as w:
        return w.getnframes() / w.getframerate()

async def gen_audio():
    for s in SCENES:
        mp3 = VID / "audio" / f"s{s['n']:02d}.mp3"
        wav = VID / "audio" / f"s{s['n']:02d}.wav"
        if wav.exists():
            try:  # 断点续跑: 校验已有 wav 完整性
                wav_dur(wav)
            except Exception:  # noqa: BLE001
                print(f"s{s['n']:02d}.wav 损坏, 重新生成")
                wav.unlink()
        if not wav.exists():
            await tts(s["text"], mp3)
            mp3_to_wav(mp3, wav)
        s["dur"] = wav_dur(wav) + 0.8   # 句尾留白
        print(f"S{s['n']:02d} {s['dur']:.1f}s  {s['title']}", flush=True)
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
    f_title = load_font(56, bold=True)
    f_kicker = load_font(30)
    f_sub = load_font(40, bold=True)
    # 顶部 kicker + 标题
    d.text((90, 60), "UBI 研究 · 生产力与治理", font=f_kicker, fill=(120, 140, 160))
    d.text((90, 110), f"{s['n']:02d}  {s['title']}", font=f_title, fill=ACC)
    d.line((90, 195, W - 90, 195), fill=(60, 75, 95), width=3)
    # 主体: 图或大字
    if s.get("fig") and Path(s["fig"]).exists():
        im = Image.open(s["fig"]).convert("RGB")
        im = fit_image(im, 1620, 660)
        img.paste(im, ((W - im.width) // 2, 240))
    else:
        big = load_font(88, bold=True)
        d.text((W / 2, 420), "人类的生产力足够 UBI 吗？", font=big, fill=FG, anchor="mm")
        d.text((W / 2, 560), "治理技术上有什么阻碍？", font=big, fill=ACC, anchor="mm")
        d.text((W / 2, 680), "—— 80 篇文献 · 31,656 条世界银行观测 · 26 国与中国专章 ——",
               font=load_font(34), fill=(150, 165, 185), anchor="mm")
    # 底部字幕条: 取旁白前 ~46 字
    sub = s["text"][:44] + ("…" if len(s["text"]) > 44 else "")
    d.rectangle((0, H - 150, W, H), fill=(10, 14, 21))
    d.text((W / 2, H - 78), sub, font=f_sub, fill=FG, anchor="mm")
    out = VID / "frames" / f"s{s['n']:02d}.png"
    img.save(out)
    s["frame"] = str(out)

# ---------------------------------------------------------------- SRT
def fmt_tsec(t):
    h, m, sec = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", ",")

def split_sentences(text):
    parts = re.split(r"(?<=[。；？！])", text)
    return [p for p in parts if p.strip()]

def make_srt():
    t0, idx, lines = 0.0, 1, []
    for s in SCENES:
        sents = split_sentences(s["text"])
        total_chars = sum(len(x) for x in sents)
        t = t0
        for sent in sents:
            dur = s["dur"] * len(sent) / max(total_chars, 1)
            lines.append(f"{idx}\n{fmt_tsec(t)} --> {fmt_tsec(min(t + dur, t0 + s['dur']))}\n{sent.strip()}\n")
            t += dur
            idx += 1
        t0 += s["dur"]
    (VID / "subtitles.srt").write_text("\n".join(lines), encoding="utf-8")
    print(f"SRT: {idx-1} 条字幕")

# ---------------------------------------------------------------- 合成
def run(cmd):
    import subprocess
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-1200:])

def render():
    import subprocess
    parts = []
    for s in SCENES:
        out = VID / f"part{s['n']:02d}.mp4"
        dur = s["dur"]
        fade_out = max(dur - 0.5, 0)
        run([FFMPEG, "-y", "-loglevel", "error",
             "-loop", "1", "-i", s["frame"], "-i", str(VID / "audio" / f"s{s['n']:02d}.wav"),
             "-t", f"{dur:.2f}",
             "-vf", f"scale=1920:1080,fade=t=in:st=0:d=0.45,fade=t=out:st={fade_out:.2f}:d=0.45,format=yuv420p",
             "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-r", "30",
             "-c:a", "aac", "-b:a", "128k", str(out)])
        parts.append(out)
        print(f"part{s['n']:02d}.mp4  {dur:.1f}s")
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
