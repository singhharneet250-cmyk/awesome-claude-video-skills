#!/usr/bin/env python3
"""
Find where the person is in a video, so captions and the bottom blur band follow them
(SKILL.md section 6, "auto" position).

    python3 person_track.py footage.mp4            # prints the person's position and the derived layout
    python3 person_track.py footage.mp4 --json     # timeline for other scripts

It finds the largest face about twice a second (OpenCV Haar cascade), fills short gaps, and
smooths the track. Everything is measured in FACE HEIGHTS (fh) from the chin, so it works for
close-ups and wide shots alike. Calibrated on the owner's reference reels R5 and R6:
  caption centre   chin + 1.0 fh      (R5: chin 42% + 9% = 51%, measured 51%; R6: 40% + 18% = 58%, measured 58%)
  caption x        the face centre, kept inside the 72 px side margins
  blur band start  just under the caption block (caption centre + 5.5%; R6 about 63%), full 12% lower
All values are clamped to the safe zone (y 250–1500 on 1920). With no face in at least 30%
of the samples (a faceless video), it reports none and callers use their fixed positions.
Needs: pip install opencv-python-headless==4.10.0.84 (4.x ships the face model), numpy, ffmpeg.
"""
import argparse
import json
import subprocess
import sys

import numpy as np

try:
    import cv2
except ImportError:
    sys.exit("person_track.py needs OpenCV: pip install opencv-python-headless==4.10.0.84")

W, H = 360, 640                     # analysis size (9:16)
CAPTION_FH = 1.0                   # caption centre, in face heights below the chin (R5, R6)
BLUR_GAP = 0.055                   # blur band starts this far below the caption centre (R6)
SAFE_TOP, SAFE_BOTTOM = 250 / 1920, 1500 / 1920


def duration(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                         capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        sys.exit(f"Could not read the duration of {video}. Is it a video file?")


def track(video, max_samples=240):
    dur = duration(video)
    fps = min(2.0, max_samples / max(dur, 0.1))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf",
                          f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (W * H)
    if n == 0:
        sys.exit(f"No frames could be read from {video}.")
    frames = np.frombuffer(raw[: n * W * H], np.uint8).reshape(n, H, W)
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    pts = []
    for k, g in enumerate(frames):
        faces = casc.detectMultiScale(cv2.equalizeHist(g), scaleFactor=1.1, minNeighbors=6, minSize=(36, 36))
        t = round((k + 0.5) / fps, 2)
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            pts.append({"t": t, "cx": (x + w / 2) / W, "top": y / H, "chin": (y + h) / H, "fh": h / H, "fw": w / W})
        else:
            pts.append({"t": t, "cx": None})
    found = [p for p in pts if p["cx"] is not None]
    result = {"video": video, "samples": len(pts), "found": len(found), "timeline": []}
    if len(found) < 0.3 * len(pts):
        result["person"] = False
        return result
    result["person"] = True
    # fill gaps by nearest detection, then smooth with a 5-sample running median
    keys = ("cx", "top", "chin", "fh", "fw")
    ft = np.array([p["t"] for p in found])
    filled = []
    for p in pts:
        q = p if p["cx"] is not None else found[int(np.argmin(np.abs(ft - p["t"])))]
        filled.append({"t": p["t"], **{k: q[k] for k in keys}})
    arr = {k: np.array([f[k] for f in filled]) for k in keys}
    for k in keys:
        pad = np.pad(arr[k], 2, mode="edge")
        arr[k] = np.array([np.median(pad[i:i + 5]) for i in range(len(arr[k]))])
    result["timeline"] = [{"t": filled[i]["t"], **{k: round(float(arr[k][i]), 4) for k in keys}} for i in range(len(filled))]
    med = {k: float(np.median(arr[k])) for k in keys}
    result["median"] = {k: round(v, 4) for k, v in med.items()}
    result["layout"] = layout(med)
    return result


def layout(p):
    """Caption anchor and blur band (shares of the frame) for one face position."""
    cap_y = float(np.clip(p["chin"] + CAPTION_FH * p["fh"], SAFE_TOP + 0.08, SAFE_BOTTOM - 0.04))
    blur_start = float(np.clip(cap_y + BLUR_GAP, 0.50, 0.84))   # the band always starts just under the caption
    return {"caption_x": round(float(np.clip(p["cx"], 0.30, 0.70)), 4), "caption_y": round(cap_y, 4),
            "blur_start": round(min(blur_start, 0.88), 4), "blur_full": round(min(blur_start + 0.12, 0.98), 4),
            "free_side": "left" if p["cx"] >= 0.5 else "right"}


def at(result, start, end):
    """Layout for one caption window, from the face positions during [start, end]."""
    if not result.get("person"):
        return None
    pts = [p for p in result["timeline"] if start - 0.25 <= p["t"] <= end + 0.25]
    if not pts:
        pts = [min(result["timeline"], key=lambda p: abs(p["t"] - (start + end) / 2))]
    return layout({k: float(np.median([p[k] for p in pts])) for k in ("cx", "top", "chin", "fh", "fw")})


def face_at(result, start, end):
    """Median face box (shares of the frame) during [start, end], or None without a person."""
    if not result.get("person"):
        return None
    pts = [p for p in result["timeline"] if start - 0.25 <= p["t"] <= end + 0.25]
    if not pts:
        pts = [min(result["timeline"], key=lambda p: abs(p["t"] - (start + end) / 2))]
    return {k: float(np.median([p[k] for p in pts])) for k in ("cx", "top", "chin", "fh", "fw")}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = track(a.video)
    if a.json:
        print(json.dumps(r, indent=2)); return
    if not r["person"]:
        print(f"no person found ({r['found']} of {r['samples']} samples had a face): use the fixed positions"); return
    m, L = r["median"], r["layout"]
    print(f"person  face centre x {m['cx']:.0%}, top {m['top']:.0%}, chin {m['chin']:.0%}, face height {m['fh']:.0%} "
          f"(found in {r['found']} of {r['samples']} samples)")
    print(f"layout  captions centred at x {L['caption_x']:.0%}, y {L['caption_y']:.0%}; bottom blur {L['blur_start']:.0%} → {L['blur_full']:.0%}; "
          f"free side for lockups: {L['free_side']}")


if __name__ == "__main__":
    main()
