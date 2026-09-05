# -*- coding: utf-8 -*-
"""
竖屏版 (1080x1920, 抖音/小红书): 复用场景与音频, 重排版面, 烧录字幕(避开平台UI区)
输出: video/UBI研究报告视频_竖屏版.mp4 (无字幕) / video/UBI研究报告视频_竖屏硬字幕版.mp4
"""
import re
import wave
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
VID = ROOT / "video"
SCRIPTS = ROOT / "scripts"
W, H = 1080, 1920
SR = 24000
BG = (16, 22, 33)
FG = (238, 242, 245)
ACC = (86, 156, 214)
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"

def load_font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)

def fit_image(img, max_w, max_h):
    r = min(max_w / img.width, max_h / img.height)
    return img.resize((int(img.width * r), int(img.height * r)), Image.LANCZOS)

def wrap_by_width(d, text, font, max_w):
    """按像素宽度折行"""
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=font) > max_w:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines

# ---------------------------------------------------------------- 场景 (复用 14 的解析与文献数据)
import importlib.util
spec = importlib.util.spec_from_file_location("v14", str(SCRIPTS / "14_make_video.py"))
m14 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m14)  # 只执行模块级解析, 不触发 main
SCENES = m14.SCENES
print(f"场景: {len(SCENES)}")

def make_vframe(s):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((54, 46), "UBI 研究 · 生产力与治理", font=load_font(26), fill=(120, 140, 160))
    d.text((W - 54, 48), "github.com/akisame2023/UBI-research",
           font=load_font(20), fill=(110, 128, 150), anchor="ra")
    d.text((54, 92), f"{s['n']:02d}  {s['title']}", font=load_font(42, bold=True), fill=ACC)
    d.line((54, 168, W - 54, 168), fill=(60, 75, 95), width=3)
    if s.get("fig") and Path(s["fig"]).exists():
        im = fit_image(Image.open(s["fig"]).convert("RGB"), 1000, 950)
        img.paste(im, ((W - im.width) // 2, 220 + (1150 - 220 - im.height) // 2))
    elif s["n"] == 1:
        for i, line in enumerate(["人类的生产力", "足够 UBI 吗？"]):
            d.text((W / 2, 520 + i * 150), line, font=load_font(84, bold=True),
                   fill=FG if i == 0 else ACC, anchor="mm")
        d.text((W / 2, 900), "治理技术上有什么阻碍？", font=load_font(48, bold=True), fill=ACC, anchor="mm")
        d.text((W / 2, 1030), "80 篇文献 · 31,656 条世界银行观测", font=load_font(30),
               fill=(150, 165, 185), anchor="mm")
    elif s["n"] == 10:
        d.text((W / 2, 240), "总结：UBI 是一道权衡题", font=load_font(50, bold=True), fill=FG, anchor="mm")
        f_h, f_b = load_font(34, bold=True), load_font(29)
        d.text((54, 340), "社会效益（实证支持）", font=f_h, fill=(110, 190, 130))
        for i, line in enumerate(["贫困与健康改善 · 议价能力更强", "福利行政简化，无算法排斥"]):
            d.text((54, 402 + i * 46), "＋ " + line, font=f_b, fill=FG)
        d.text((54, 530), "代价与风险（同样真实）", font=f_h, fill=(220, 120, 110))
        for i, line in enumerate(["财政负担与税收扭曲", "少数人工时下降", "替换定向体系或伤及最困难者", "通胀/租金与机会成本未定"]):
            d.text((54, 592 + i * 46), "− " + line, font=f_b, fill=FG)
        d.text((54, 830), "权衡判断：效益、成本、机会成本", font=load_font(38, bold=True), fill=(200, 205, 160))
        d.text((54, 890), "放在一起称，因国、因价值观而异；", font=load_font(30), fill=FG)
        d.text((54, 944), "研究负责把天平两边的量级算清楚。", font=load_font(30), fill=FG)
    else:  # 文献/数据列表
        f_h = load_font(36, bold=True)
        f_b = load_font(29)
        y = 210
        for line in s["lit"]:
            head_like = line.startswith(("报告", "数据", "文献库", "代码与数据"))
            if head_like:
                d.text((54, y), line, font=f_h, fill=ACC)
                y += 58
                continue
            for ln in wrap_by_width(d, line, f_b, W - 108):
                d.text((54, y), ln, font=f_b, fill=FG)
                y += 44
            y += 18
    out = VID / "frames" / f"v_s{s['n']:02d}.png"
    img.save(out)
    return str(out)

# ---------------------------------------------------------------- 合成
def run(cmd):
    import subprocess
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-1200:])

def render_vertical(burn):
    import subprocess
    parts = []
    for s in SCENES:
        frame = make_vframe(s)
        wav = VID / "audio" / f"s{s['n']:02d}.wav"
        with wave.open(str(wav), "rb") as w:
            dur = w.getnframes() / w.getframerate() + 0.6
        out = VID / f"vpart{s['n']:02d}.mp4"
        style = ("FontName=Microsoft YaHei,FontSize=12,PrimaryColour=&HFFFFFF&,"
                 "OutlineColour=&H80000000&,Outline=1.6,Shadow=0,MarginV=70")
        # 字幕在拼接后的整片上统一烧录(分段烧录会导致每段都从SRT的0秒开始, 时间全错)
        vf = f"scale=1080:1920,fade=t=in:st=0:d=0.45,fade=t=out:st={max(dur-0.5,0):.2f}:d=0.45,format=yuv420p"
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
               "-loop", "1", "-i", frame, "-i", str(wav), "-t", f"{dur:.2f}",
               "-vf", vf, "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium",
               "-r", "30", "-c:a", "aac", "-b:a", "128k", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(VID))
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-1000:])
        parts.append(out)
        print(f"vpart{s['n']:02d}.mp4  {dur:.1f}s", flush=True)
    lst = VID / "vconcat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    base = VID / "UBI研究报告视频_竖屏版.mp4"
    run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
         "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(base)])
    if burn:
        style = ("FontName=Microsoft YaHei,FontSize=12,PrimaryColour=&HFFFFFF&,"
                 "OutlineColour=&H80000000&,Outline=1.6,Shadow=0,MarginV=70")
        final = VID / "UBI研究报告视频_竖屏硬字幕版.mp4"
        r2 = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                             "-i", str(base), "-vf",
                             "subtitles=UBI研究报告视频.srt:force_style='" + style + "'",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                             "-c:a", "copy", str(final)], capture_output=True, text=True, cwd=str(VID))
        if r2.returncode != 0:
            raise RuntimeError(r2.stderr[-1000:])
        for p in parts:
            p.unlink(missing_ok=True)
        print("FINAL:", final, f"{final.stat().st_size/1e6:.1f} MB")
    else:
        for p in parts:
            p.unlink(missing_ok=True)
        print("FINAL:", base, f"{base.stat().st_size/1e6:.1f} MB")

if __name__ == "__main__":
    render_vertical(burn=True)
