#!/usr/bin/env python3
"""
Bottom blur band (R6 style): the lower part of the frame melts into a progressive blur and a
soft fade, so captions and cards above it stand out and desk clutter disappears.

    python3 bottom_blur.py in.mp4 out.mp4                       # dark fade (footage, R6 look)
    python3 bottom_blur.py in.mp4 out.mp4 --tone light          # fade to porcelain white (white-stage pieces)
    python3 bottom_blur.py in.mp4 out.mp4 --start 0.64 --full 0.76 --sigma 26 --fade 0.85

Measured on R6 (1080x1920 equivalent): sharp down to about 62% of the height, a soft ramp to
fully blurred by about 70–76%, then darkening toward the bottom edge (about 85% at 100%).
Defaults reproduce that. Run it BEFORE burning captions, so the words stay sharp.

  --start  where the blur begins (share of frame height)          default 0.64
  --full   where the blur reaches full strength                    default 0.76
  --sigma  blur strength at full (gaussian sigma, in px at 1080 wide)   default 26
  --fade   fade opacity at the bottom edge (0 = no fade)           default 0.85
  --tone   dark (fade to #0B1118) or light (fade to #FFFFFF)       default dark
  --plan   only when needed: fade the band in for the windows captions.py --plan-out wrote
  --when   extra windows, e.g. while an animation sits in the bottom band: 3.0-5.5,12-14
Needs ffmpeg, Pillow and numpy. Audio is copied unchanged.
"""
import argparse
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    try:
        w, h = (int(v) for v in out.split(",")[:2])
        return w, h
    except ValueError:
        sys.exit(f"Could not read the video size of {path}. Is it a video file?")


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        sys.exit(f"Could not read the duration of {path}. Is it a video file?")


def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)          # smoothstep: no visible edge where the ramp starts or ends


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input"); ap.add_argument("output")
    ap.add_argument("--start", type=float, default=0.64)
    ap.add_argument("--full", type=float, default=0.76)
    ap.add_argument("--sigma", type=float, default=26.0)
    ap.add_argument("--fade", type=float, default=0.85)
    ap.add_argument("--fade-start", type=float, default=0.72, help="where the fade begins (default 0.72)")
    ap.add_argument("--tone", choices=["dark", "light"], default="dark")
    ap.add_argument("--auto", action="store_true",
                    help="start the band just under where captions go for the person in this video (scripts/person_track.py); --start/--full are then ignored")
    ap.add_argument("--plan", metavar="PLAN.json",
                    help="blur ONLY when needed: the band fades in for the time windows in this plan (written by captions.py --plan-out)")
    ap.add_argument("--when", metavar="A-B,C-D",
                    help="extra windows in seconds when the band is on, e.g. for animations in the bottom band: 3.0-5.5,12-14")
    ap.add_argument("--crf", type=int, default=4)  # encode.WORK_CRF
    a = ap.parse_args()
    if not (0 < a.start < a.full <= 1):
        sys.exit("--start must be below --full, both between 0 and 1 (shares of the frame height).")
    if not (0 <= a.fade <= 1):
        sys.exit("--fade must be between 0 and 1.")
    w, h = probe(a.input)
    windows = None                       # None = band on for the whole video
    if a.plan or a.when:
        windows = []
        if a.plan:
            import json
            try:
                plan = json.load(open(a.plan, encoding="utf-8"))
            except (OSError, ValueError) as e:
                sys.exit(f"Could not read the plan {a.plan}: {e}")
            windows += [tuple(wi) for wi in plan.get("windows", [])]
            if plan.get("band_top"):
                a.start = float(plan["band_top"]); a.full = min(a.start + 0.10, 0.98)
                a.fade_start = min(max(a.fade_start, a.start + 0.05), 0.95)
        if a.when:
            try:
                windows += [tuple(float(v) for v in part.split("-")) for part in a.when.split(",") if part.strip()]
            except ValueError:
                sys.exit("--when must look like 3.0-5.5,12-14 (seconds).")
        if not windows:
            print("no window needs the blur band: copying the video unchanged")
            r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", a.input, "-c", "copy", a.output])
            sys.exit(r.returncode)
    if a.auto:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from person_track import track
        r = track(a.input)
        if r["person"]:
            a.start, a.full = r["layout"]["blur_start"], r["layout"]["blur_full"]
            a.fade_start = min(max(a.fade_start, a.start + 0.06), 0.95)
            print(f"auto: person found; band from {a.start:.0%} to {a.full:.0%}")
        else:
            print("auto: no person found, so the band uses the default heights")
    sigma = a.sigma * w / 1080
    y = (np.arange(h, dtype=np.float32) + .5) / h
    blur_alpha = smooth((y - a.start) / (a.full - a.start))
    fade_alpha = a.fade * smooth((y - a.fade_start) / (1 - a.fade_start)) ** 1.2
    tone = (11, 17, 24) if a.tone == "dark" else (255, 255, 255)

    with tempfile.TemporaryDirectory() as td:
        mask = os.path.join(td, "mask.png"); fade = os.path.join(td, "fade.png")
        Image.fromarray(np.repeat((blur_alpha * 255).astype(np.uint8)[:, None], w, 1), "L").save(mask)
        f = np.zeros((h, w, 4), np.uint8); f[..., :3] = tone; f[..., 3] = (fade_alpha * 255).astype(np.uint8)[:, None]
        Image.fromarray(f, "RGBA").save(fade)
        if windows is None:
            graph = (f"[0:v]split=2[base][b];[b]gblur=sigma={sigma:.1f}:steps=3,format=yuva420p[bl];"
                     f"[1:v]format=gray[m];[bl][m]alphamerge[blm];[base][blm]overlay=0:0:format=auto:shortest=1[soft];"
                     f"[soft][2:v]overlay=0:0:format=auto:shortest=1,format=yuv420p[v]")
        else:
            # time envelope: the band fades in over 0.3 s at each window start and out at its end
            cmds = os.path.join(td, "band.cmd")
            with open(cmds, "w") as fh:
                fh.write("0.000 colorchannelmixer@bl aa 0, colorchannelmixer@fd aa 0;\n")
                for s0, s1 in sorted(windows):
                    for k in range(10):
                        v = (k + 1) / 10
                        fh.write(f"{s0 + k * 0.03:.3f} colorchannelmixer@bl aa {v:.2f}, colorchannelmixer@fd aa {v:.2f};\n")
                    for k in range(10):
                        v = 1 - (k + 1) / 10
                        fh.write(f"{max(s0 + 0.3, s1 - 0.3) + k * 0.03:.3f} colorchannelmixer@bl aa {v:.2f}, colorchannelmixer@fd aa {v:.2f};\n")
            graph = (f"[0:v]split=2[base][b];[b]gblur=sigma={sigma:.1f}:steps=3,format=rgba[bl];"
                     f"[1:v]format=gray[m];[bl][m]alphamerge,sendcmd=f='{cmds}',colorchannelmixer@bl=aa=0[blm];"
                     f"[base][blm]overlay=0:0:format=auto:shortest=1[soft];"
                     f"[2:v]format=rgba,colorchannelmixer@fd=aa=0[fd];[soft][fd]overlay=0:0:format=auto:shortest=1,format=yuv420p[v]")
        # the gradient images loop, so bound them to the clip length; otherwise a clip with no audio never ends
        dur = f"{duration(a.input):.3f}"
        cmd = ["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", a.input, "-loop", "1", "-t", dur, "-i", mask,
               "-loop", "1", "-t", dur, "-i", fade,
               "-filter_complex", graph, "-map", "[v]", "-map", "0:a?", "-t", dur,
               "-c:v", "libx264", "-crf", str(a.crf), "-preset", "fast", "-pix_fmt", "yuv420p",
               "-c:a", "copy", "-movflags", "+faststart", a.output]
        r = subprocess.run(cmd)
        if r.returncode != 0:
            sys.exit("ffmpeg failed; see the message above.")
    when = "the whole video" if windows is None else ", ".join(f"{s0:.1f}–{s1:.1f} s" for s0, s1 in sorted(windows))
    print(f"bottom blur → {a.output}  (blur {a.start:.0%}→{a.full:.0%}, sigma {sigma:.0f}px, {a.tone} fade {a.fade:.0%} from {a.fade_start:.0%}; on during {when})")


if __name__ == "__main__":
    main()
