#!/usr/bin/env python3
"""
White Glass delivery QA: checks a finished video against SKILL.md sections 2, 7 and 9.7.

    python3 qa.py final.mp4                      # footage reel (stray hues are warnings)
    python3 qa.py final.mp4 --graphics           # all-graphics piece (stray hues fail)
    python3 qa.py final.mp4 --expect 18.5        # also check the length (±0.25 s)
    python3 qa.py final.mp4 --sheet sheet.png    # where to write the contact sheet

Prints one PASS / WARN / FAIL line per check and exits 1 if anything FAILs.
It checks the numbers. It does not replace looking at the contact sheet and a full-size still.

Checks:
  format      size is 1080x1920, 1920x1080 or 1080x1350; 30 fps
  video       H.264 High, yuv420p
  audio       AAC, 48 kHz (a silent piece with no audio track is a WARN)
  rhythm      no frozen stretch over 1.6 s (graphics) or 2.5 s (footage), end card left out (WARN)
  faststart   moov atom before mdat
  loudness    integrated -14 LUFS ±1, true peak <= -1.5 dBTP (ffmpeg ebur128)
  logo        assets/logo/nutrition-hub-logo.png matches its sha256
  hues        share of saturated green/blue/purple pixels per sampled frame (needs numpy)
  black       no near-black frames (the system has no black backgrounds)
  sheet       a 2 fps contact sheet to look at
"""
import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
LOGO = SKILL / "assets" / "logo" / "nutrition-hub-logo.png"
LOGO_SHA256 = "1ceaeb7a9ca284fa859de4009237dc52d1827656518150a81f4de6922c20e28d"
SIZES = {(1080, 1920): "9:16", (1920, 1080): "16:9", (1080, 1350): "4:5"}

results = []


def report(status, name, detail):
    results.append(status)
    print(f"{status:<4}  {name:<10} {detail}")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    if r.returncode != 0:
        sys.exit(f"ffprobe could not read {path}: {r.stderr.strip()}")
    return json.loads(r.stdout)


def fps_of(stream):
    num, den = (stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/1").split("/")
    return float(num) / float(den or 1) if float(den or 1) else 0.0


def check_streams(info, expect):
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        report("FAIL", "video", "no video stream")
        return None
    w, h = v["width"], v["height"]
    fmt = SIZES.get((w, h))
    fps = fps_of(v)
    if fmt and abs(fps - 30) < 0.01:
        report("PASS", "format", f"{w}x{h} ({fmt}) at {fps:g} fps")
    elif fmt:
        report("FAIL", "format", f"{w}x{h} ({fmt}) but {fps:.3f} fps; deliver at 30 fps")
    else:
        report("FAIL", "format", f"{w}x{h} at {fps:.3f} fps; expected 1080x1920, 1920x1080 or 1080x1350 at 30 fps")

    codec, profile, pix = v.get("codec_name"), v.get("profile", ""), v.get("pix_fmt")
    if codec == "h264" and profile == "High" and pix == "yuv420p":
        report("PASS", "video", "H.264 High, yuv420p")
    else:
        report("FAIL", "video", f"{codec} {profile} {pix}; export H.264 High, yuv420p (-profile:v high -pix_fmt yuv420p)")

    if a is None:
        report("WARN", "audio", "no audio track (fine only if the piece is meant to be silent)")
    elif a.get("codec_name") == "aac" and a.get("sample_rate") == "48000":
        kbps = int(a.get("bit_rate", 0)) // 1000
        report("PASS", "audio", f"AAC 48 kHz, {a.get('channels')} ch" + (f", {kbps} kb/s" if kbps else ""))
    else:
        report("FAIL", "audio", f"{a.get('codec_name')} {a.get('sample_rate')} Hz; export AAC 256 kb/s at 48 kHz")

    # high quality (owner, 2026-11-26): a clean master the platforms re-encode from, not a thin file
    vbr = int(v.get("bit_rate") or info["format"].get("bit_rate") or 0) / 1e6
    need = 8.0 * (w * h) / (1080 * 1920)
    if vbr >= need:
        report("PASS", "quality", f"{vbr:.1f} Mbit/s video (high quality: {need:.0f}+ at this size)")
    else:
        report("WARN", "quality", f"{vbr:.1f} Mbit/s video, below {need:.0f}: deliver with encode.py deliver (CRF 14, slow)")

    dur = float(info["format"].get("duration", 0))
    if expect is not None:
        ok = abs(dur - expect) <= 0.25
        report("PASS" if ok else "FAIL", "length", f"{dur:.2f} s (expected {expect:.2f} s)")
    return {"w": w, "h": h, "dur": dur, "audio": a is not None}


def check_faststart(path):
    order = []
    with open(path, "rb") as f:
        while len(order) < 32:
            head = f.read(8)
            if len(head) < 8:
                break
            size, kind = struct.unpack(">I4s", head)
            kind = kind.decode("latin-1")
            if size == 1:
                size = struct.unpack(">Q", f.read(8))[0]
                f.seek(size - 16, 1)
            elif size == 0:
                order.append(kind)
                break
            else:
                f.seek(size - 8, 1)
            order.append(kind)
    if "moov" in order and "mdat" in order:
        ok = order.index("moov") < order.index("mdat")
        report("PASS" if ok else "FAIL", "faststart", "moov before mdat" if ok else "moov after mdat; add -movflags +faststart")
    else:
        report("WARN", "faststart", f"could not find moov/mdat (top-level boxes: {', '.join(order[:8])})")


def check_loudness(path):
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
             "-af", "ebur128=peak=true", "-f", "null", "-"])
    summary = r.stderr.split("Summary:")[-1]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summary)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    if not i:
        report("WARN", "loudness", "could not measure (no audio?)")
        return
    lufs = float(i.group(1)) if i.group(1) != "-inf" else float("-inf")
    peak = float(tp.group(1)) if tp and tp.group(1) != "-inf" else float("-inf")
    lufs_ok = abs(lufs + 14) <= 1.0
    peak_ok = peak <= -1.5 + 0.05
    status = "PASS" if lufs_ok and peak_ok else "FAIL"
    hint = "" if status == "PASS" else "; finish with loudnorm=I=-14:TP=-1.5:LRA=11"
    report(status, "loudness", f"{lufs:.1f} LUFS integrated, true peak {peak:.1f} dBTP (target -14 ±1, <= -1.5){hint}")


def check_logo():
    if not LOGO.exists():
        report("FAIL", "logo", f"original logo missing at {LOGO.relative_to(SKILL)}; ask the owner for it")
        return
    digest = hashlib.sha256(LOGO.read_bytes()).hexdigest()
    if digest == LOGO_SHA256:
        report("PASS", "logo", "original file intact (sha256 matches)")
    else:
        report("FAIL", "logo", "logo file changed (sha256 mismatch); restore the original")


def sample_frames(path, meta, every=0.5, width=180):
    h = round(meta["h"] * width / meta["w"] / 2) * 2
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps=1/{every},scale={width}:{h}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    frame_bytes = width * h * 3
    n = len(r.stdout) // frame_bytes
    return [(i * every, r.stdout[i * frame_bytes:(i + 1) * frame_bytes]) for i in range(n)], width, h


def check_pixels(path, meta, graphics):
    try:
        import numpy as np
    except ImportError:
        report("WARN", "hues", "numpy not installed, so the stray-hue and black-frame scans were skipped")
        return
    frames, w, h = sample_frames(path, meta)
    if not frames:
        report("WARN", "hues", "no frames decoded")
        return
    worst, flagged, dark = 0.0, [], []
    for t, buf in frames:
        rgb = np.frombuffer(buf, np.uint8).reshape(h, w, 3).astype(np.float32) / 255
        mx, mn = rgb.max(2), rgb.min(2)
        sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
        d = np.maximum(mx - mn, 1e-6)
        r_, g_, b_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        hue = np.where(mx == r_, ((g_ - b_) / d) % 6, np.where(mx == g_, (b_ - r_) / d + 2, (r_ - g_) / d + 4)) * 60
        # allowed: the orange/red/gold/skin band (330°-60°). Stray: green, cyan, blue, purple.
        stray = (sat >= 0.35) & (mx >= 0.25) & (hue > 60) & (hue < 330)
        share = float(stray.mean() * 100)
        worst = max(worst, share)
        if share > (1.0 if graphics else 3.0):
            flagged.append(f"{t:.1f}s ({share:.1f}%)")
        if float((0.2126 * r_ + 0.7152 * g_ + 0.0722 * b_).mean()) < 0.12:
            dark.append(f"{t:.1f}s")
    limit = 1.0 if graphics else 3.0
    if not flagged:
        report("PASS", "hues", f"no stray green/blue/purple above {limit:g}% of a frame (worst {worst:.1f}%)")
    else:
        status = "FAIL" if graphics else "WARN"
        why = "graphics must stay white, ice, ink and orange" if graphics else "check whether it is footage (fine) or a graphic (fix)"
        report(status, "hues", f"stray hues at {', '.join(flagged[:6])}{' …' if len(flagged) > 6 else ''}; {why}")
    if dark:
        report("WARN", "black", f"near-black frames at {', '.join(dark[:6])}; the system has no black backgrounds or dips to black")
    else:
        report("PASS", "black", f"no near-black frames in {len(frames)} samples")


def check_rhythm(path, meta, graphics):
    """Frozen stretches: the owner's references hold a fully still frame 0.5-0.9 s (median), rarely over 1.5 s
    (style-references.md, R8-R16). The last 3 s (end card) are left out."""
    try:
        import numpy as np
    except ImportError:
        return
    fps, w = 10, 96
    h = round(meta["h"] * w / meta["w"] / 2) * 2
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={fps},scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                       capture_output=True)
    n = len(r.stdout) // (w * h)
    if n < 3:
        return
    f = np.frombuffer(r.stdout[:n * w * h], np.uint8).reshape(n, h, w).astype(np.float32)
    still = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2)) < 0.2
    stop = max(0, n - 1 - 3 * fps)
    best, run, at = 0, 0, 0
    for i in range(stop):
        run = run + 1 if still[i] else 0
        if run > best:
            best, at = run, (i - run + 1) / fps
    limit = 1.6 if graphics else 2.5
    secs = best / fps
    if secs > limit:
        report("WARN", "rhythm", f"the picture is frozen for {secs:.1f} s from {at:.1f} s; the references hold a still frame "
                                 "0.5-0.9 s: keep something moving (a float, a drift, the next beat)")
    else:
        report("PASS", "rhythm", f"longest frozen stretch {secs:.1f} s (limit {limit:g} s, end card left out)")


def contact_sheet(path, meta, out):
    cols = 10
    n = max(1, int(meta["dur"] * 2))
    rows = max(1, -(-n // cols))
    r = run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf", f"fps=2,scale=180:-2,tile={cols}x{rows}:color=white",
             "-frames:v", "1", "-update", "1", str(out)])
    if r.returncode == 0:
        report("INFO", "sheet", f"{out} ({n} frames at 2 fps): look at it before you deliver")
    else:
        report("WARN", "sheet", f"could not write the contact sheet: {r.stderr.strip()[:120]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--graphics", action="store_true", help="all-graphics piece: stray hues fail instead of warn")
    ap.add_argument("--expect", type=float, help="expected length in seconds")
    ap.add_argument("--sheet", type=Path, help="contact sheet path (default: <video>.sheet.png)")
    ap.add_argument("--source", type=Path, help="the camera file: warns when it had to be enlarged (low detail)")
    args = ap.parse_args()
    if not args.video.exists():
        sys.exit(f"{args.video} not found")

    print(f"White Glass QA · {args.video}")
    meta = check_streams(probe(args.video), args.expect)
    check_faststart(args.video)
    if args.source and args.source.exists():
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import encode
        note = encode.source_note(args.source, meta["w"], meta["h"]) if meta else None
        report("WARN" if note else "PASS", "source", note or "source is full HD or larger: no enlarging")
    if meta and meta["audio"]:
        check_loudness(args.video)
    check_logo()
    if meta:
        check_pixels(args.video, meta, args.graphics)
        check_rhythm(args.video, meta, args.graphics)
        contact_sheet(args.video, meta, args.sheet or args.video.with_suffix(".sheet.png"))

    fails, warns = results.count("FAIL"), results.count("WARN")
    print(f"\n{'FAIL' if fails else 'PASS'}: {fails} failed, {warns} to look at. "
          "Then run through the by-eye checks in SKILL.md §9.7 (logo clear space, one orange focal point, "
          "text inside safe zones, no overshoot, every number has a unit and a source).")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
