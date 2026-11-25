#!/usr/bin/env python3
"""
Flexible caption layout: put each caption in the best VACANT space around the person, and decide
when the bottom blur band is actually needed (SKILL.md section 6, --position auto).

Used by captions.py --position auto. On its own it prints the free space it sees:

    python3 layout_plan.py footage.mp4

Candidate slots, measured from the tracked face (person_track.py), on a 1080x1920 canvas:
  left / right   beside the head, from the safe edge to 40 px off the face, head-to-shoulder height
  top            above the head, below the 250 px top safe line
  chest          one face-height below the chin, centred on the person (R5/R6)
  bottom         the band under the person, above the 1500 px bottom safe line; the blur band is
                 switched on for a caption here only when the background there is busy
For each caption the text is fitted to each slot (wrapped, 62 px down to 46 px, at most 3 lines).
Then the slot with the lowest cost wins:
  cost = clutter behind the text block (edge energy) / 3 + slot preference
         (left/right 0, top 0.3, chest 0.8, bottom 1.0, plus 1.5 if it needs the blur band)
         + 0.35 for each line beyond two (a cramped slot that stacks single words loses to a roomy one)
The slot also has to keep clear of the face. The previous caption's slot is kept unless another
is clearly better (by 1.0), so captions don't jump around. --prefer SLOT uses that slot whenever
the caption fits there (for example bottom, to put captions in the blur band). With no person (a faceless video) it
returns None and captions use the fixed positions.
Needs ffmpeg, numpy and person_track.py (OpenCV).
"""
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from person_track import track, face_at   # noqa: E402

FW, FH = 1080, 1920                      # output canvas
AW, AH = 360, 640                        # analysis size
SAFE_L, SAFE_T, SAFE_R, SAFE_B = 72, 250, 1008, 1500
CHAR_W, LINE_H = 0.56, 1.22              # Inter Bold: average advance per em, line height per em
PREF = {"left": 0.0, "right": 0.0, "top": 0.3, "chest": 0.8, "bottom": 1.0}
BLUR_COST, CALM, KEEP, LINE_COST = 1.5, 4.0, 1.0, 0.35


def frames(video, max_samples=240):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                         capture_output=True, text=True).stdout.strip()
    dur = float(out)
    fps = min(2.0, max_samples / max(dur, 0.1))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf",
                          f"fps={fps},scale={AW}:{AH}:force_original_aspect_ratio=increase,crop={AW}:{AH}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    n = len(raw) // (AW * AH * 3)
    rgb = np.frombuffer(raw[: n * AW * AH * 3], np.uint8).reshape(n, AH, AW, 3).astype(np.float32) / 255
    g = rgb @ np.array([0.299, 0.587, 0.114], np.float32) * 255
    edge = np.zeros_like(g)
    edge[:, 1:-1, 1:-1] = np.abs(4 * g[:, 1:-1, 1:-1] - g[:, :-2, 1:-1] - g[:, 2:, 1:-1] - g[:, 1:-1, :-2] - g[:, 1:-1, 2:])
    lum = rgb.max(-1) * 0.5 + rgb.min(-1) * 0.5
    times = np.array([(k + 0.5) / fps for k in range(n)])
    return {"times": times, "edge": edge, "lum": lum}


def wrap_to(tokens, max_chars):
    lines, cur = [], []
    for t in tokens:
        if cur and len(" ".join(cur + [t])) > max_chars:
            lines.append(cur); cur = [t]
        else:
            cur.append(t)
    if cur:
        lines.append(cur)
    return lines


def fit(tokens, w, h, fs_max=62, fs_min=46, max_lines=3):
    if w <= 0 or h <= 0:
        return None
    for fs in range(fs_max, fs_min - 1, -2):
        mc = int(w / (CHAR_W * fs))
        if mc < max(len(t) for t in tokens):
            continue
        lines = wrap_to(tokens, mc)
        bh = len(lines) * fs * LINE_H
        if len(lines) <= max_lines and bh <= h:
            bw = max(len(" ".join(l)) for l in lines) * CHAR_W * fs
            return {"fs": fs, "lines": lines, "bw": bw, "bh": bh}
    return None


def slots(face):
    cx, fw, top, chin, fh = face["cx"] * FW, face["fw"] * FW, face["top"] * FH, face["chin"] * FH, face["fh"] * FH
    fx0, fx1 = cx - fw / 2, cx + fw / 2
    side_y0, side_y1 = max(SAFE_T, top - 0.2 * fh), min(SAFE_B, chin + 0.3 * fh)
    chest_c = chin + 1.0 * fh
    bottom_y0 = max(chin + 1.5 * fh, 0.62 * FH)          # just under the chest (R6 close-up: about 66%)
    return {
        "left": (SAFE_L, side_y0, fx0 - 40, side_y1),
        "right": (fx1 + 40, side_y0, SAFE_R, side_y1),
        "top": (SAFE_L, SAFE_T, SAFE_R, top - 0.25 * fh),
        "chest": (max(SAFE_L, cx - 468), chest_c - 0.45 * fh - 40, min(SAFE_R, cx + 468), chest_c + 0.45 * fh + 40),
        "bottom": (SAFE_L, bottom_y0, SAFE_R, SAFE_B),
    }


class Planner:
    def __init__(self, video, prefer=None):
        self.prefer = prefer               # a slot to use whenever the caption fits there, e.g. 'bottom'
        self.person = track(video)
        self.fr = frames(video) if self.person.get("person") else None
        self.prev = None
        self.windows = []          # (start, end, band_top_share) for captions that need the blur band

    def _window_idx(self, s, e):
        t = self.fr["times"]
        idx = np.where((t >= s - 0.25) & (t <= e + 0.25))[0]
        return idx if len(idx) else np.array([int(np.argmin(np.abs(t - (s + e) / 2)))])

    def place(self, tokens, s, e):
        """Best slot for one caption: dict(slot, x, y, fs, lines, light, busy, blur) or None."""
        if not self.person.get("person"):
            return None
        face = face_at(self.person, s, e)
        idx = self._window_idx(s, e)
        edge = self.fr["edge"][idx].mean(0); lum = self.fr["lum"][idx].mean(0)
        best = {}
        for name, (x0, y0, x1, y1) in slots(face).items():
            f = fit(tokens, x1 - x0, y1 - y0)
            if not f:
                continue
            xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
            if name == "chest":
                xc = min(max(face["cx"] * FW, SAFE_L + f["bw"] / 2), SAFE_R - f["bw"] / 2)
            if name == "bottom":
                yc = y0 + f["bh"] / 2 + 20               # sit at the top of the band, near the person
            bx0, bx1 = (xc - f["bw"] / 2) * AW / FW, (xc + f["bw"] / 2) * AW / FW
            by0, by1 = (yc - f["bh"] / 2) * AH / FH, (yc + f["bh"] / 2) * AH / FH
            r = (slice(max(0, int(by0)), max(1, int(by1))), slice(max(0, int(bx0)), max(1, int(bx1))))
            clutter = float(edge[r].mean()); light = float(np.median(lum[r])) > 0.62
            blur = name == "bottom" and clutter > CALM
            cost = clutter / 3 + PREF[name] + (BLUR_COST if blur else 0) + LINE_COST * max(0, len(f["lines"]) - 2)
            best[name] = {"slot": name, "x": round(xc), "y": round(yc), "fs": f["fs"], "lines": f["lines"],
                          "clutter": round(clutter, 2), "light": light and not blur, "busy": clutter > 2 * CALM and not blur,
                          "blur": blur, "band_top": round((y0 - 0.02 * FH) / FH, 3), "cost": round(cost, 2)}
        if not best:
            return None
        pick = min(best.values(), key=lambda c: c["cost"])
        if self.prefer in best:
            pick = best[self.prefer]               # the editor asked for this slot and the caption fits there
        elif self.prev in best and best[self.prev]["cost"] <= pick["cost"] + KEEP:
            pick = best[self.prev]
        self.prev = pick["slot"]
        if pick["blur"]:
            self.windows.append((s, e, pick["band_top"]))
        return pick

    def band_plan(self):
        """Merged time windows (with 0.3 s pads) when the bottom blur band is needed."""
        if not self.windows:
            return {"windows": [], "band_top": None}
        ws = sorted(self.windows)
        merged = [[ws[0][0] - 0.3, ws[0][1] + 0.3]]
        for s, e, _ in ws[1:]:
            if s - 0.3 <= merged[-1][1] + 0.6:          # short gaps: keep the band on instead of flickering
                merged[-1][1] = max(merged[-1][1], e + 0.3)
            else:
                merged.append([s - 0.3, e + 0.3])
        return {"windows": [[round(max(0, a), 2), round(b, 2)] for a, b in merged],
                "band_top": min(w[2] for w in ws)}


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 layout_plan.py footage.mp4")
    pl = Planner(sys.argv[1])
    if not pl.person.get("person"):
        print("no person found: captions use the fixed positions"); return
    face = pl.person["median"]
    print(f"face centre x {face['cx']:.0%}, top {face['top']:.0%}, chin {face['chin']:.0%}, size {face['fw']:.0%} × {face['fh']:.0%}")
    t0, t1 = float(pl.fr["times"][0]), float(pl.fr["times"][-1])
    sample = ["Read", "the", "label", "before", "you", "buy."]
    edge = pl.fr["edge"].mean(0)
    for name, (x0, y0, x1, y1) in slots(face).items():
        f = fit(sample, x1 - x0, y1 - y0)
        r = (slice(int(max(0, y0) * AH / FH), max(1, int(y1 * AH / FH))), slice(int(x0 * AW / FW), max(1, int(x1 * AW / FW))))
        clutter = float(edge[r].mean()) if x1 > x0 and y1 > y0 else float("nan")
        print(f"{name:6s} {int(max(0, x1 - x0)):4d} × {int(max(0, y1 - y0)):4d} px  clutter {clutter:5.1f}  "
              + (f"fits at {f['fs']} px in {len(f['lines'])} line(s)" if f else "too small for a caption"))
    print(f"(video {t0:.1f}–{t1:.1f} s; calm below {CALM})")


if __name__ == "__main__":
    main()
