#!/usr/bin/env python3
"""
Caption colours that follow the video: pick the caption base colour and the key-word accent
from the footage itself (SKILL.md section 6).

    python3 caption_colors.py footage.mp4                 # prints the scheme
    python3 caption_colors.py footage.mp4 --json          # machine-readable (includes the timeline)
    python3 captions.py words.json --out c.ass --match footage.mp4   # what you normally run

How it decides:
  base    Looks at the caption zone (bottom band by default) about twice a second.
          - light in 80%+ of samples: graphite ink words (soft white glow) for the whole video
          - light in 20% or fewer:    white words (soft dark shadow) for the whole video
          - mixed in between:         each caption picks white or ink from what is behind it
  accent  The video's dominant saturated hue, ignoring skin tones and greys, even when it covers
          only a small area (a minimal white video with one green accent counts). It is
          re-coloured in two readable shades: a bright one for white words and a deeper one for
          ink words. It uses Logo Red (#FC2B16 bright, #C40205 deep) instead when the video
          has no clear colour, or when its colour is already close to orange. Per caption, it also
          switches to orange when the same colour sits right behind that caption at that moment
          (a blue key word on a blue shirt would vanish).
Captions only: the logo, cards and callouts keep the brand palette.
Needs ffmpeg, ffprobe and numpy.
"""
import argparse
import colorsys
import json
import subprocess
import sys

import numpy as np

BRAND_BRIGHT, BRAND_DEEP = "#FC2B16", "#C40205"   # Logo Red (owner, 2026-11-27): bright on footage, deep on light
INK, WHITE, SHADOW = "#202B38", "#FFFFFF", "#0B1118"
W, H = 180, 320                     # analysis size (9:16)
ZONES = {"bottom": (0.655, 0.735), "mic": (0.54, 0.62), "chest": (0.47, 0.55)}  # where caption text sits, share of frame height
MAX_SAMPLES = 240


def duration(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                         capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        sys.exit(f"Could not read the duration of {video}. Is it a video file?")


def frames(video):
    """Sampled frames as float RGB (0..1), 180x320 crop-to-fill, plus their timestamps."""
    dur = duration(video)
    fps = min(2.0, MAX_SAMPLES / max(dur, 0.1))
    cmd = ["ffmpeg", "-v", "error", "-i", video, "-vf",
           f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    n = len(raw) // (W * H * 3)
    if n == 0:
        sys.exit(f"No frames could be read from {video}.")
    arr = np.frombuffer(raw[: n * W * H * 3], np.uint8).reshape(n, H, W, 3).astype(np.float32) / 255
    times = [round((k + 0.5) / fps, 2) for k in range(n)]
    return arr, times


def rel_lum(rgb):
    c = np.where(rgb <= 0.03928, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def hex_to_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def rgb_to_hex(rgb):
    return "#" + "".join(f"{int(round(max(0, min(1, v)) * 255)):02X}" for v in rgb)


def contrast(a, b):
    la, lb = float(rel_lum(hex_to_rgb(a))), float(rel_lum(hex_to_rgb(b)))
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def hue_dist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def shade(hue, light, step, test):
    """Walk the lightness until test(hex) passes; captions are large bold text (3:1 minimum)."""
    for _ in range(60):
        hx = rgb_to_hex(colorsys.hls_to_rgb(hue / 360, light, 0.85))
        if test(hx):
            return hx
        light = min(0.95, max(0.05, light + step))
    return hx


def analyse(video, zone="bottom"):
    fr, times = frames(video)
    y0, y1 = (int(z * H) for z in (ZONES[zone] if isinstance(zone, str) else zone))   # a name or a (top, bottom) pair
    lum = rel_lum(fr[:, y0:y1, int(.1 * W):int(.9 * W)])
    light = [bool(np.median(f) > 0.55 and np.mean(f < 0.18) < 0.08) for f in lum]
    # busy: plenty of both light and dark behind the words, so white needs a stronger shadow
    busy = [bool(np.mean(f > 0.45) >= 0.2 and np.mean(f < 0.18) >= 0.2) for f in lum]
    light_share = float(np.mean(light))
    base = "ink" if light_share >= 0.8 else "white" if light_share <= 0.2 else "mixed"

    px = fr.reshape(-1, 3)
    mx, mn = px.max(1), px.min(1)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    d = np.maximum(mx - mn, 1e-6)
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    h = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    vivid = (s >= 0.40) & (mx >= 0.35)
    skin = (h <= 50) & (s < 0.62) & (mx > 0.35)
    keep = vivid & ~skin
    share = float(keep.mean())
    scheme = {"video": video, "zone": zone, "base": base, "light_share": round(light_share, 2),
              "vivid_share": round(share, 4), "hue": None}
    dominance = 0.0
    if share >= 0.005:
        wts = (s * mx)[keep]
        hist, _ = np.histogram(h[keep], bins=36, range=(0, 360), weights=wts)
        k = int(np.argmax(hist))
        dominance = float(sum(hist[(k + j) % 36] for j in (-1, 0, 1)) / max(hist.sum(), 1e-9))
        sel = keep & (np.abs(((h - (k * 10 + 5)) + 180) % 360 - 180) <= 15)
        ang = np.deg2rad(h[sel]); w = (s * mx)[sel]
        scheme["hue"] = round(float(np.rad2deg(np.arctan2((np.sin(ang) * w).sum(), (np.cos(ang) * w).sum())) % 360), 1)
    scheme["dominance"] = round(dominance, 2)

    # hue of whatever sits directly behind the captions, per sample (a blue shirt, a green wall...)
    zhues = []
    for f in fr[:, y0:y1, int(.1 * W):int(.9 * W)]:
        zp = f.reshape(-1, 3); zmx, zmn = zp.max(1), zp.min(1)
        zs = np.where(zmx > 0, (zmx - zmn) / np.maximum(zmx, 1e-6), 0); zd = np.maximum(zmx - zmn, 1e-6)
        zh = np.where(zmx == zp[:, 0], (zp[:, 1] - zp[:, 2]) / zd % 6, np.where(zmx == zp[:, 1], (zp[:, 2] - zp[:, 0]) / zd + 2, (zp[:, 0] - zp[:, 1]) / zd + 4)) * 60
        zv = (zs >= 0.35) & (zmx >= 0.25)
        if zv.mean() >= 0.15:
            za = np.deg2rad(zh[zv]); zw = (zs * zmx)[zv]
            zhues.append(round(float(np.rad2deg(np.arctan2((np.sin(za) * zw).sum(), (np.cos(za) * zw).sum())) % 360), 1))
        else:
            zhues.append(None)

    if scheme["hue"] is None or dominance < 0.45:
        scheme.update(accent_bright=BRAND_BRIGHT, accent_deep=BRAND_DEEP, source="brand orange (no clear colour in the video)")
    elif hue_dist(scheme["hue"], 24) <= 18:
        scheme.update(accent_bright=BRAND_BRIGHT, accent_deep=BRAND_DEEP, source="brand orange (the video's own colour is orange)")
    else:
        hue = scheme["hue"]
        scheme.update(
            accent_bright=shade(hue, 0.60, +0.01, lambda x: contrast(x, SHADOW) >= 4.5),
            accent_deep=shade(hue, 0.45, -0.01, lambda x: contrast(x, WHITE) >= 3.0),
            source="the video's own colour")
    scheme["timeline"] = [{"t": t, "light": l, "busy": b, "zhue": z} for t, l, b, z in zip(times, light, busy, zhues)]
    if scheme["source"] == "the video's own colour":
        n_clash = sum(1 for z in zhues if z is not None and hue_dist(z, scheme["hue"]) <= 35)
        scheme["clash_share"] = round(n_clash / max(len(zhues), 1), 2)
    return scheme


def _window(scheme, start, end):
    pts = [p for p in scheme["timeline"] if start - 0.25 <= p["t"] <= end + 0.25]
    return pts or [min(scheme["timeline"], key=lambda p: abs(p["t"] - (start + end) / 2))]


def is_light_at(scheme, start, end):
    """Is the caption zone light for most of [start, end]?"""
    pts = _window(scheme, start, end)
    return sum(p["light"] for p in pts) / len(pts) >= 0.5


def clashes_at(scheme, start, end):
    """Is the key-word colour the same hue as what sits behind this caption (so it would vanish)?"""
    if scheme.get("source") != "the video's own colour" or scheme.get("hue") is None:
        return False
    pts = _window(scheme, start, end)
    return sum(1 for p in pts if p["zhue"] is not None and hue_dist(p["zhue"], scheme["hue"]) <= 35) / len(pts) >= 0.5


def is_busy_at(scheme, start, end):
    """Is the caption zone a mix of light and dark for most of [start, end]?"""
    pts = _window(scheme, start, end)
    return sum(p["busy"] for p in pts) / len(pts) >= 0.5


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--zone", choices=sorted(ZONES), default="bottom", help="where the captions sit")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    sc = analyse(a.video, a.zone)
    if a.json:
        print(json.dumps(sc, indent=2)); return
    base = {"ink": "ink words for the whole video", "white": "white words for the whole video",
            "mixed": "mixed: each caption picks white or ink from what is behind it"}[sc["base"]]
    print(f"base    {base} (caption zone light in {sc['light_share']*100:.0f}% of samples)")
    print(f"accent  {sc['accent_bright']} on white words, {sc['accent_deep']} on ink words, from {sc['source']}"
          + (f" (hue {sc['hue']}°, {sc['dominance']*100:.0f}% of the colour)" if sc["hue"] is not None else ""))
    if sc.get("clash_share"):
        print(f"note    the same colour sits behind the captions in {sc['clash_share']*100:.0f}% of samples; those captions switch to orange")
    print(f"use:    python3 captions.py words.json --out captions.ass --match {a.video}")


if __name__ == "__main__":
    main()
