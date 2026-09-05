# -*- coding: utf-8 -*-
"""烧录硬字幕 -> video/UBI研究报告视频_硬字幕发布版.mp4"""
import subprocess
from pathlib import Path
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
VID = ROOT / "video"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

style = ("FontName=Microsoft YaHei,FontSize=13,PrimaryColour=&HFFFFFF&,"
         "OutlineColour=&H80000000&,Outline=1.6,Shadow=0,MarginV=30")
vf = f"subtitles=UBI研究报告视频.srt:force_style='{style}'"
out = VID / "UBI研究报告视频_硬字幕发布版.mp4"
subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", "UBI研究报告视频.mp4",
                "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                "-c:a", "copy", str(out)], check=True, cwd=str(VID))
print("BURNED:", out, f"{out.stat().st_size/1e6:.1f} MB")
