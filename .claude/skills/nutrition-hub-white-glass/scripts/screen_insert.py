#!/usr/bin/env python3
"""
Screen Insert (R11, R15, R16): put a White Glass graphic or clip onto a real screen in footage (the store's TV,
a laptop, a phone, a monitor), so it looks like it is playing on that screen. The plate (the footage of the
screen) keeps its own light: a little of the screen's original glare stays on top, and a soft glow spills
past the bezel in dark rooms.

    # find the screen by itself (the brightest four-sided shape in the first frame), locked-off shot
    python3 screen_insert.py store-tv.mp4 beat.mp4 out.mp4

    # handheld: follow the screen as the camera moves (optical flow around the screen, one homography a frame)
    python3 screen_insert.py laptop-handheld.mp4 beat.mp4 out.mp4 --track

    # give the corners yourself: top-left, top-right, bottom-right, bottom-left, in plate pixels
    python3 screen_insert.py plate.jpg beat.mp4 out.mp4 --corners 412,388,1490,402,1482,1010,405,1001

    # the screen is off (black) in the plate
    python3 screen_insert.py tv-off.mp4 beat.mp4 out.mp4 --detect dark

Render the content for the screen's shape: a TV or laptop is 16:9, so render the beat with --size 1920x1080
(templates/motion-kit.html lays itself out for landscape). Content can be a video or a still (.png .jpg).

Options:
  --at 1.5          start the content this many seconds into the plate (before that the plate plays as filmed)
  --fit cover       cover (fill the screen, crop) or contain (fit inside on porcelain white)
  --glare 0.08      how much of the screen's original light stays on top (reflections), 0-0.3
  --glow 0.15       light spill past the screen edge, 0 for none (bright rooms)
  --preview f.png   write the first composited frame and the detected corners drawn on the plate, then stop
Audio: the plate's own sound is kept (add SFX with sfx.py afterwards). Needs ffmpeg, numpy and OpenCV.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:
    sys.exit("screen_insert.py needs OpenCV: pip install opencv-python-headless")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motion_track import OneEuro  # noqa: E402
import encode  # noqa: E402

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
PORCELAIN = (255, 255, 255)


def probe(path):
    if not Path(path).is_file():
        sys.exit(f"File not found: {path}")
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        s = d["streams"][0]
    except (json.JSONDecodeError, KeyError, IndexError):
        sys.exit(f"Could not read {path}. Is it a video or an image?")
    n, k = s.get("r_frame_rate", "30/1").split("/")
    has_a = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True).stdout.strip() != ""
    return {"w": int(s["width"]), "h": int(s["height"]), "rate": s.get("r_frame_rate", "30/1"),
            "fps": float(n) / float(k or 1), "dur": float(d.get("format", {}).get("duration", 0) or 0), "audio": has_a}


def reader(path, w, h, rate=None):
    vf = f"scale={w}:{h}" + (f",fps={rate}" if rate else "")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    size = w * h * 3
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.stdout.close()
    p.wait()


def order_quad(q):
    """Sort four points to top-left, top-right, bottom-right, bottom-left."""
    q = np.asarray(q, np.float32).reshape(4, 2)
    s, d = q.sum(1), np.diff(q, axis=1).ravel()
    return np.array([q[np.argmin(s)], q[np.argmin(d)], q[np.argmax(s)], q[np.argmax(d)]], np.float32)


def detect(rgb, mode="bright"):
    """Find the screen: four-sided shapes from edges (the bezel) and from brightness (a lit display), kept only if
    they are near-rectangular and screen-shaped (16:9-ish landscape or a phone in portrait); the largest one wins."""
    g = cv2.GaussianBlur(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), (5, 5), 0)
    H, W = g.shape
    masks = []
    gi = 255 - g if mode == "dark" else g
    for pct in (92, 85, 75, 65, 55):
        m = (gi >= np.percentile(gi, pct)).astype(np.uint8) * 255
        masks.append(cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))))
    for lo, hi in ((30, 90), (50, 150)):
        e = cv2.dilate(cv2.Canny(g, lo, hi), cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
        filled = np.zeros_like(e)
        cs, _ = cv2.findContours(e, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(filled, cs, -1, 255, -1)
        masks.append(filled)
    best, best_score = None, 0.0
    for m in masks:
        cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in cs:
            a = cv2.contourArea(c)
            if a < 0.03 * W * H or a > 0.92 * W * H:
                continue
            hull = cv2.convexHull(c)
            ap = None
            for eps in (0.015, 0.025, 0.04, 0.06):
                q = cv2.approxPolyDP(hull, eps * cv2.arcLength(hull, True), True)
                if len(q) == 4:
                    ap = q
                    break
            if ap is None:
                continue
            q = order_quad(ap)
            qa = cv2.contourArea(q.reshape(-1, 1, 2))
            fill = a / max(1.0, qa)
            w = (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2
            h = (np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2
            ar = w / max(1.0, h)
            if fill < 0.82 or not (1.15 <= ar <= 2.6 or 0.38 <= ar <= 0.9):
                continue
            edge = ((q[:, 0] <= 2) | (q[:, 0] >= W - 3) | (q[:, 1] <= 2) | (q[:, 1] >= H - 3)).sum()
            score = qa * (0.3 if edge >= 2 else 1.0)     # cut off by the frame: more likely a desk or a wall
            if score > best_score:
                best, best_score = q, score
    if best is None:
        sys.exit("Could not find the screen. Give its corners with --corners x1,y1,...,x4,y4 (top-left, top-right, "
                 "bottom-right, bottom-left), or try --detect dark if it is switched off.")
    return best


class Tracker:
    """Follow a planar screen through a moving shot: features around the screen (its bezel, the desk, the wall),
    optical flow frame to frame, one RANSAC homography a frame, corners smoothed with a one-euro filter."""

    def __init__(self, rgb, quad, fps):
        self.prev = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        self.quad = quad.copy()
        self.filt = OneEuro(fps, min_cutoff=2.0, beta=0.08)
        self.pts = self._features(self.prev, quad)

    @staticmethod
    def _features(g, quad):
        H, W = g.shape
        ring = np.zeros_like(g)
        c = quad.mean(0)
        outer = (quad - c) * 1.35 + c
        inner = (quad - c) * 0.9 + c
        cv2.fillConvexPoly(ring, outer.astype(np.int32), 255)
        cv2.fillConvexPoly(ring, inner.astype(np.int32), 0)     # skip what the screen itself shows: it moves on its own
        p = cv2.goodFeaturesToTrack(g, 400, 0.01, 7, mask=ring)
        return p if p is not None else np.empty((0, 1, 2), np.float32)

    def update(self, rgb):
        g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        if len(self.pts) >= 12:
            nxt, st, _ = cv2.calcOpticalFlowPyrLK(self.prev, g, self.pts, None, winSize=(21, 21), maxLevel=3)
            a, b = self.pts[st.ravel() == 1], nxt[st.ravel() == 1]
            if len(a) >= 12:
                Hm, inl = cv2.findHomography(a, b, cv2.RANSAC, 3.0)
                if Hm is not None:
                    self.quad = cv2.perspectiveTransform(self.quad.reshape(-1, 1, 2), Hm).reshape(4, 2)
                    b = b[inl.ravel() == 1] if inl is not None else b
            self.pts = b.reshape(-1, 1, 2)
        if len(self.pts) < 150:                                  # top up features as the shot moves
            self.pts = np.concatenate([self.pts.reshape(-1, 1, 2), self._features(g, self.quad)]).astype(np.float32)[:400]
        self.prev = g
        return self.filt(self.quad.ravel()).reshape(4, 2).astype(np.float32)


def fit_content(c, qw, qh, mode):
    """Fill (cover) or fit (contain, on porcelain) the content to the screen's aspect."""
    h, w = c.shape[:2]
    ar = qw / max(1.0, qh)
    if mode == "cover":
        if w / h > ar:
            nw = int(round(h * ar)); x = (w - nw) // 2; return c[:, x:x + nw]
        nh = int(round(w / ar)); y = (h - nh) // 2; return c[y:y + nh]
    if w / h > ar:
        nh = int(round(w / ar)); out = np.full((nh, w, 3), PORCELAIN, np.uint8); y = (nh - h) // 2; out[y:y + h] = c; return out
    nw = int(round(h * ar)); out = np.full((h, nw, 3), PORCELAIN, np.uint8); x = (nw - w) // 2; out[:, x:x + w] = c; return out


def soft_blur(img, sigma):
    """A wide Gaussian blur done at quarter size (16x cheaper, the same look for light and glow)."""
    h, w = img.shape[:2]
    small = cv2.resize(img, (max(1, w // 4), max(1, h // 4)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), max(0.5, sigma / 4))
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR).reshape(img.shape)


def composite(plate, content, quad, glare, glow, mode):
    H, W = plate.shape[:2]
    qw = (np.linalg.norm(quad[1] - quad[0]) + np.linalg.norm(quad[2] - quad[3])) / 2
    qh = (np.linalg.norm(quad[3] - quad[0]) + np.linalg.norm(quad[2] - quad[1])) / 2
    c = fit_content(content, qw, qh, mode)
    ch, cw = c.shape[:2]
    src = np.array([[0, 0], [cw, 0], [cw, ch], [0, ch]], np.float32)
    M = cv2.getPerspectiveTransform(src, quad)
    warped = cv2.warpPerspective(c, M, (W, H), flags=cv2.INTER_AREA if cw > qw * 1.5 else cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT).astype(np.float32)
    ones = np.zeros((ch + 2, cw + 2), np.float32)
    ones[1:-1, 1:-1] = 1.0                                       # a zero border gives anti-aliased edges after the warp
    M1 = cv2.getPerspectiveTransform(src + 1, quad)
    alpha = cv2.warpPerspective(ones, M1, (W, H), flags=cv2.INTER_LINEAR)[..., None]
    p = plate.astype(np.float32)
    lum = cv2.cvtColor(plate, cv2.COLOR_RGB2GRAY).astype(np.float32)
    lum = soft_blur(lum, max(2.0, qw * 0.06))[..., None]        # soft room light only, never the old picture
    screen = warped * (1 - glare) + lum * glare                  # the screen's own reflections stay faintly on top
    out = p * (1 - alpha) + screen * alpha
    if glow > 0:
        k = max(3, int(qw * 0.06) | 1)
        halo = soft_blur(warped * alpha, k / 2.5)
        spill = halo * (1 - alpha) * glow
        out = out + spill * (1 - out / 255.0)                    # screen-blend the spill so it never clips
    return np.clip(out, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plate"); ap.add_argument("content"); ap.add_argument("out")
    ap.add_argument("--corners", help="x1,y1,x2,y2,x3,y3,x4,y4 in plate pixels: top-left, top-right, bottom-right, bottom-left")
    ap.add_argument("--detect", choices=["bright", "dark"], default="bright")
    ap.add_argument("--track", action="store_true", help="follow the screen in a handheld or moving shot")
    ap.add_argument("--at", type=float, default=0.0)
    ap.add_argument("--fit", choices=["cover", "contain"], default="cover")
    ap.add_argument("--glare", type=float, default=0.08)
    ap.add_argument("--glow", type=float, default=0.15)
    ap.add_argument("--preview")
    a = ap.parse_args()

    still_plate = Path(a.plate).suffix.lower() in IMAGE_EXT
    still_content = Path(a.content).suffix.lower() in IMAGE_EXT
    pi, ci = probe(a.plate), probe(a.content)
    W, H = pi["w"] // 2 * 2, pi["h"] // 2 * 2
    fps = 30.0 if still_plate else pi["fps"]
    rate = "30" if still_plate else pi["rate"]
    if still_plate:
        img = next(reader(a.plate, W, H))
        dur = a.at + (ci["dur"] if not still_content else 5.0)
        n = int(round(dur * fps))
        plates = (img for _ in range(n))
    else:
        plates = reader(a.plate, W, H, rate)
    if still_content:
        content_img = next(reader(a.content, ci["w"], ci["h"]))
        contents = None
    else:
        contents = reader(a.content, ci["w"], ci["h"], rate)

    first = next(plates)
    if a.corners:
        v = [float(x) for x in a.corners.split(",")]
        if len(v) != 8:
            sys.exit("--corners needs 8 numbers: x1,y1,x2,y2,x3,y3,x4,y4")
        quad = order_quad(np.array(v).reshape(4, 2) * [W / pi["w"], H / pi["h"]])
    else:
        quad = detect(first, a.detect)
    print("screen corners: " + ", ".join(f"{x:.0f},{y:.0f}" for x, y in quad))
    tracker = Tracker(first, quad, fps) if a.track else None

    if a.preview:
        c0 = content_img if still_content else next(reader(a.content, ci["w"], ci["h"]))
        prev = composite(first, c0, quad, a.glare, a.glow, a.fit)
        dbg = first.copy()
        cv2.polylines(dbg, [quad.astype(np.int32)], True, (240, 120, 43), max(2, W // 400))
        both = np.concatenate([dbg, prev], axis=1)
        cv2.imwrite(a.preview, cv2.cvtColor(both, cv2.COLOR_RGB2BGR))
        print(f"preview → {a.preview} (left: the corners found, right: the first composited frame)")
        return

    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", rate, "-i", "-",
                            *(["-i", a.plate] if pi["audio"] and not still_plate else []),
                            "-map", "0:v", *(["-map", "1:a?", *encode.AUDIO] if pi["audio"] and not still_plate else []),
                            *encode.WORK, "-movflags", "+faststart", "-shortest", a.out],
                           stdin=subprocess.PIPE)
    i, last_c = 0, None
    frame = first
    while frame is not None:
        t = i / fps
        q = tracker.update(frame) if (tracker and i) else quad if not tracker else tracker.quad
        if t >= a.at:
            if still_content:
                last_c = content_img
            else:
                last_c = next(contents, last_c)
            out = composite(frame, last_c, q, a.glare, a.glow, a.fit) if last_c is not None else frame
        else:
            out = frame
        enc.stdin.write(np.ascontiguousarray(out).tobytes())
        i += 1
        frame = next(plates, None)
        if i % int(fps) == 0:
            print(f"\r{i / fps:.1f} s", end="", flush=True)
    enc.stdin.close()
    enc.wait()
    print(f"\rwrote {a.out} ({i} frames)")


if __name__ == "__main__":
    main()
