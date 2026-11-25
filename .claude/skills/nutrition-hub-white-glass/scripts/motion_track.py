#!/usr/bin/env python3
"""
Head and hand motion for talking-head footage (SKILL.md §4 J). No model download: OpenCV only.

    python3 motion_track.py footage.mp4                        # summary + gesture moments
    python3 motion_track.py footage.mp4 --json motion.json     # per-frame head and hands, and the moments
    python3 motion_track.py footage.mp4 --preview check.mp4    # boxes and trails drawn on the video, to check

HEAD  A face detection every 6 frames, with optical flow (Lucas-Kanade) on points inside the face
      in between, so the box follows nods and turns at the full frame rate; smoothed with a
      one-euro filter (steady when still, quick when moving).
HANDS Skin colour taken from the speaker's own face (so it works for any skin tone), kept only
      where the speaker is (not the head or neck) and where it moves or a hand was a moment ago;
      blobs of hand size, at most two, followed frame to frame (image-left / image-right).
MOMENTS  "gesture": a peak in hand speed (at least 1 s apart); "hands_up": a hand rises above the
      chin; "head_move": the head moves fast (a nod, a turn, a lean).

Used by fx.py: the orbit and the frame escape follow this head track, and hands pass in front of
orbit spheres. Pick effect timings from the moments. Plain clothes and a plain wall work best; a
skin-coloured wall or wooden furniture can add false hands, so check with --preview.
Needs numpy, OpenCV 4.10 (opencv-python-headless==4.10.0.84) and ffmpeg.
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:
    sys.exit("motion_track.py needs OpenCV: pip install opencv-python-headless==4.10.0.84")

AW, AH = 360, 640          # analysis size (9:16)
DETECT_EVERY = 6


class OneEuro:
    """One-euro filter: little smoothing when moving fast, a lot when still."""

    def __init__(self, fps, min_cutoff=1.2, beta=0.04):
        self.fps, self.mc, self.beta = fps, min_cutoff, beta
        self.x = self.dx = None

    @staticmethod
    def _a(cutoff, fps):
        tau = 1 / (2 * math.pi * cutoff)
        return 1 / (1 + tau * fps)

    def __call__(self, x):
        x = np.asarray(x, np.float64)
        if self.x is None:
            self.x, self.dx = x, np.zeros_like(x)
            return x
        dx = (x - self.x) * self.fps
        self.dx = self.dx + self._a(1.0, self.fps) * (dx - self.dx)
        cutoff = self.mc + self.beta * np.abs(self.dx)
        a = np.array([self._a(c, self.fps) for c in np.atleast_1d(cutoff)])
        self.x = self.x + a * (x - self.x)
        return self.x


class HeadTracker:
    def __init__(self, fps):
        self.casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.prof = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
        self.box = None            # x, y, w, h in analysis pixels (float)
        self.pts = None
        self.prev = None
        self.n = 0
        self.lost = 0
        self.filt = OneEuro(fps)

    def _detect(self, gray):
        eq = cv2.equalizeHist(gray)
        faces = list(self.casc.detectMultiScale(eq, 1.1, 6, minSize=(28, 28)))
        if not faces:
            faces = list(self.prof.detectMultiScale(eq, 1.1, 6, minSize=(28, 28)))
            faces += [(AW - x - w, y, w, h) for x, y, w, h in self.prof.detectMultiScale(cv2.flip(eq, 1), 1.1, 6, minSize=(28, 28))]
        if not faces:
            return None
        if self.box is None:
            return np.array(max(faces, key=lambda f: f[2] * f[3]), np.float64)
        cx, cy = self.box[0] + self.box[2] / 2, self.box[1] + self.box[3] / 2
        return np.array(min(faces, key=lambda f: (f[0] + f[2] / 2 - cx) ** 2 + (f[1] + f[3] / 2 - cy) ** 2), np.float64)

    def _seed(self, gray):
        x, y, w, h = self.box.astype(int)
        mask = np.zeros_like(gray)
        cv2.rectangle(mask, (x + w // 6, y + h // 6), (x + 5 * w // 6, y + 5 * h // 6), 255, -1)
        self.pts = cv2.goodFeaturesToTrack(gray, 40, 0.01, 3, mask=mask)

    def update(self, gray):
        if self.box is not None and self.prev is not None and self.pts is not None and len(self.pts) >= 4:
            nxt, st, _ = cv2.calcOpticalFlowPyrLK(self.prev, gray, self.pts, None, winSize=(15, 15), maxLevel=2)
            ok = st.ravel() == 1
            if ok.sum() >= 4:
                d = np.median((nxt[ok] - self.pts[ok]).reshape(-1, 2), axis=0)
                self.box[:2] += d
                self.pts = nxt[ok].reshape(-1, 1, 2)
            else:
                self.pts = None
        if self.n % DETECT_EVERY == 0 or self.pts is None:
            det = self._detect(gray)
            if det is not None:
                if self.box is None or np.abs(det[:2] - self.box[:2]).max() > det[2]:   # far off: jump to it
                    self.box = det
                else:
                    self.box = 0.5 * self.box + 0.5 * det                            # pull the flow back on the face
                self.lost = 0
                self._seed(gray)
            else:
                self.lost += 1
        self.prev, self.n = gray, self.n + 1
        if self.box is None or self.lost * DETECT_EVERY > 45:                          # no face for 1.5 s
            return None
        return self.filt(self.box.copy())


class HandFinder:
    def __init__(self, fps):
        self.skin = None           # mean and inverse covariance of (Cr, Cb) from the face
        self.prev_gray = []
        self.hands = []            # [{"cx","cy","w","h","side","age"}]
        self.fps = fps
        self.still = None          # per pixel: frames it has been skin-coloured without moving

    def learn_skin(self, ycc, box):
        x, y, w, h = box.astype(int)
        patch = ycc[y + h // 4:y + 3 * h // 4, x + w // 4:x + 3 * w // 4, 1:].reshape(-1, 2).astype(np.float64)
        if len(patch) < 30:
            return
        mu, cov = patch.mean(0), np.cov(patch.T) + np.eye(2) * 4.0
        if self.skin is None:
            self.skin = (mu, cov)
        else:
            self.skin = (0.8 * self.skin[0] + 0.2 * mu, 0.8 * self.skin[1] + 0.2 * cov)

    def update(self, ycc, gray, box):
        if self.skin is None or box is None:
            self.prev_gray.append(gray); self.prev_gray[:] = self.prev_gray[-3:]
            return [], None
        mu, cov = self.skin
        d = ycc[..., 1:].astype(np.float64) - mu
        md = np.einsum("...i,ij,...j->...", d, np.linalg.inv(cov), d)
        skin = ((md < 6.0) & (ycc[..., 0] > 40)).astype(np.uint8)
        x, y, w, h = box
        cv2.ellipse(skin, (int(x + w / 2), int(y + h / 2)), (int(0.75 * w), int(0.85 * h)), 0, 0, 360, 0, -1)   # head
        cv2.rectangle(skin, (int(x + 0.15 * w), int(y + h)), (int(x + 0.85 * w), int(y + 1.5 * h)), 0, -1)          # neck
        moving = np.zeros_like(skin)
        if len(self.prev_gray) >= 2:
            raw_move = (cv2.absdiff(gray, self.prev_gray[-2]) > 14).astype(np.uint8)
            if raw_move.mean() > 0.35:                       # a cut or a camera move: start the hands afresh
                self.hands, self.still = [], None
                self.prev_gray.append(gray); self.prev_gray[:] = self.prev_gray[-3:]
                return [], None
            moving = cv2.dilate(raw_move, np.ones((9, 9), np.uint8))
        # skin-coloured things that never move (wooden furniture, a warm wall) become background after 2 s
        if self.still is None:
            self.still = np.zeros(skin.shape, np.int32)
        self.still = np.where(skin.astype(bool) & ~moving.astype(bool), self.still + 1, 0)
        skin &= (self.still < 2 * self.fps).astype(np.uint8)
        keep = moving.copy()
        for hd in self.hands:                                   # a hand that stops still is kept for a while
            cv2.rectangle(keep, (int(hd["cx"] - hd["w"]), int(hd["cy"] - hd["h"])), (int(hd["cx"] + hd["w"]), int(hd["cy"] + hd["h"])), 1, -1)
        cand = cv2.morphologyEx(skin & keep, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        n, lab, stats, cent = cv2.connectedComponentsWithStats(cand, 8)
        face_area = w * h
        cxh, chin = x + w / 2, y + h
        reach = lambda c: abs(c[0] - cxh) <= 2.0 * w and y - 1.0 * h <= c[1] <= chin + 3.5 * h   # within arm's reach
        blobs = [(i, stats[i], cent[i]) for i in range(1, n) if 0.12 * face_area <= stats[i, 4] <= 1.8 * face_area
                 and stats[i, 2] < 2.6 * w and stats[i, 3] < 2.6 * h and reach(cent[i])]
        zone = (cxh, chin + 1.6 * h)                       # where gesturing hands usually are: in front of the chest
        blobs = sorted(blobs, key=lambda b: math.hypot((b[2][0] - zone[0]) / w, (b[2][1] - zone[1]) / h) - 0.002 * b[1][4] / face_area)[:2]
        found = []
        for i, st, c in blobs:
            side = "left" if c[0] < x + w / 2 else "right"
            found.append({"cx": float(c[0]), "cy": float(c[1]), "w": float(st[2]), "h": float(st[3]), "side": side, "age": 0, "id": i})
        # follow: match by nearest centre; hands not seen for 1 s are dropped
        new = []
        for f in found:
            prev = min(self.hands, key=lambda p: (p["cx"] - f["cx"]) ** 2 + (p["cy"] - f["cy"]) ** 2, default=None)
            if prev is not None and math.hypot(prev["cx"] - f["cx"], prev["cy"] - f["cy"]) < 1.5 * w:
                f["vx"], f["vy"] = (f["cx"] - prev["cx"]) * self.fps, (f["cy"] - prev["cy"]) * self.fps
            else:
                f["vx"] = f["vy"] = 0.0
            new.append(f)
        for p in self.hands:
            if all(math.hypot(p["cx"] - f["cx"], p["cy"] - f["cy"]) >= 1.5 * w for f in new) and p["age"] < self.fps:
                q = dict(p); q["age"] += 1; q["vx"] = q["vy"] = 0.0
                new.append(q)
        self.hands = new[:2]
        self.prev_gray.append(gray); self.prev_gray[:] = self.prev_gray[-3:]
        mask = np.isin(lab, [f["id"] for f in found]).astype(np.float32) if found else None
        return [h for h in self.hands if h["age"] == 0], mask


class MotionTracker:
    """Feed frames in order; get the head box and hands (in shares of the frame) for each."""

    def __init__(self, fps):
        self.head = HeadTracker(fps)
        self.hands = HandFinder(fps)
        self.n = 0

    def update(self, rgb):
        small = cv2.resize(rgb, (AW, AH), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
        ycc = cv2.cvtColor(small, cv2.COLOR_RGB2YCrCb)
        box = self.head.update(gray)
        if box is not None and (self.n % DETECT_EVERY == 0 or self.hands.skin is None):
            self.hands.learn_skin(ycc, box)
        hands, mask = self.hands.update(ycc, gray, box)
        self.n += 1
        head = None
        if box is not None:
            x, y, w, h = box
            head = {"cx": (x + w / 2) / AW, "top": y / AH, "chin": (y + h) / AH, "fh": h / AH, "fw": w / AW}
        hs = [{"side": hd["side"], "cx": hd["cx"] / AW, "cy": hd["cy"] / AH, "w": hd["w"] / AW, "h": hd["h"] / AH,
               "speed": math.hypot(hd.get("vx", 0) / AW, hd.get("vy", 0) / AH)} for hd in hands]
        return head, hs, mask


def probe(path):
    if not Path(path).is_file():
        sys.exit(f"File not found: {path}")
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,width,height:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    try:
        info = json.loads(r.stdout)
        num, den = (float(x) for x in info["streams"][0]["r_frame_rate"].split("/"))
        return {"fps": num / den, "dur": float(info["format"]["duration"]), "w": info["streams"][0]["width"], "h": info["streams"][0]["height"]}
    except (json.JSONDecodeError, KeyError, IndexError, ValueError, ZeroDivisionError):
        sys.exit(f"Could not read {path}. Is it a video file?")


def track(video):
    info = probe(video)
    fps = info["fps"]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-nostdin", "-i", str(video), "-vf", f"scale={AW}:{AH}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    mt = MotionTracker(fps)
    frames, k = [], 0
    while True:
        buf = p.stdout.read(AW * AH * 3)
        if len(buf) < AW * AH * 3:
            break
        head, hands, _ = mt.update(np.frombuffer(buf, np.uint8).reshape(AH, AW, 3))
        frames.append({"t": round(k / fps, 3), "head": head, "hands": hands})
        k += 1
    p.wait()
    if not frames:
        sys.exit(f"No frames could be read from {video}.")
    return {"video": str(video), "fps": fps, "frames": frames, "moments": moments(frames, fps)}


def moments(frames, fps):
    out = []
    fh = np.median([f["head"]["fh"] for f in frames if f["head"]] or [0.1])
    hand_speed = np.array([max((h["speed"] for h in f["hands"]), default=0.0) for f in frames]) / fh   # face heights / s
    k = max(1, int(fps * 0.2))
    sm = np.convolve(hand_speed, np.ones(k) / k, "same")
    last = -1e9
    for i in range(1, len(sm) - 1):
        if sm[i] >= 2.5 and sm[i] >= sm[i - 1] and sm[i] >= sm[i + 1] and frames[i]["t"] - last >= 1.0:
            out.append({"t": frames[i]["t"], "type": "gesture", "strength": round(float(sm[i]), 2)}); last = frames[i]["t"]
    up = False
    for f in frames:
        is_up = bool(f["head"]) and any(h["cy"] < f["head"]["chin"] for h in f["hands"])
        if is_up and not up:
            out.append({"t": f["t"], "type": "hands_up"})
        up = is_up
    heads = [(f["t"], f["head"]["cx"], (f["head"]["top"] + f["head"]["chin"]) / 2) for f in frames if f["head"]]
    last = -1e9
    for (t0, x0, y0), (t1, x1, y1) in zip(heads, heads[int(fps * 0.2):]):
        v = math.hypot(x1 - x0, y1 - y0) / max(t1 - t0, 1e-3) / fh
        if v > 1.2 and t0 - last > 1.0:
            out.append({"t": round(t0, 3), "type": "head_move", "strength": round(v, 2)}); last = t0
    return sorted(out, key=lambda m: m["t"])


def preview(video, result, out):
    info = probe(video)
    W, H = 540, 960
    src = subprocess.Popen(["ffmpeg", "-v", "error", "-nostdin", "-i", str(video), "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                           stdout=subprocess.PIPE)
    dst = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(info["fps"]), "-i", "-",
                            "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    trail = {"left": [], "right": []}
    marks = {round(m["t"], 2): m["type"] for m in result["moments"]}
    shown, until = "", -1
    for f in result["frames"]:
        buf = src.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        im = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy()
        if f["head"]:
            hd = f["head"]
            cv2.rectangle(im, (int((hd["cx"] - hd["fw"] / 2) * W), int(hd["top"] * H)), (int((hd["cx"] + hd["fw"] / 2) * W), int(hd["chin"] * H)),
                          (43, 120, 240), 2, cv2.LINE_AA)
        for h in f["hands"]:
            c = (int(h["cx"] * W), int(h["cy"] * H))
            trail[h["side"]] = (trail[h["side"]] + [c])[-12:]
            cv2.rectangle(im, (int((h["cx"] - h["w"] / 2) * W), int((h["cy"] - h["h"] / 2) * H)),
                          (int((h["cx"] + h["w"] / 2) * W), int((h["cy"] + h["h"] / 2) * H)), (246, 240, 234), 2, cv2.LINE_AA)
        for pts in trail.values():
            for a, b in zip(pts, pts[1:]):
                cv2.line(im, a, b, (246, 240, 234), 2, cv2.LINE_AA)
        key = round(f["t"], 2)
        if key in marks:
            shown, until = marks[key], f["t"] + 0.7
        if f["t"] <= until:
            cv2.putText(im, shown.replace("_", " ").upper(), (24, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (43, 120, 240), 3, cv2.LINE_AA)
        dst.stdin.write(im.tobytes())
    dst.stdin.close(); dst.wait(); src.wait()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--json"); ap.add_argument("--preview")
    a = ap.parse_args()
    r = track(a.video)
    fr = r["frames"]
    head_ok = sum(1 for f in fr if f["head"]) / len(fr)
    hand_ok = sum(1 for f in fr if f["hands"]) / len(fr)
    print(f"{Path(a.video).name}: {len(fr)} frames at {r['fps']:.2f} fps; head found in {head_ok:.0%}, a hand in {hand_ok:.0%}")
    for m in r["moments"]:
        extra = f" (strength {m['strength']})" if "strength" in m else ""
        print(f"  {m['t']:6.2f} s  {m['type']}{extra}")
    if a.json:
        Path(a.json).write_text(json.dumps(r))
        print(f"wrote {a.json}")
    if a.preview:
        preview(a.video, r, a.preview)
        print(f"wrote {a.preview}")


if __name__ == "__main__":
    main()
