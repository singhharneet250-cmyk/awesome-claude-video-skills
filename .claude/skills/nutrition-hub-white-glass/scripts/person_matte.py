#!/usr/bin/env python3
"""
Person mattes for the orbit and frame-escape effects (scripts/fx.py, SKILL.md §4 G–H).
A matte is a float image in 0..1, where 1 is the person. Three sources, none of which
download a model:

  head   A head-and-shoulders shape built from the face track (person_track.py). Rough, but
         enough to hide orbit spheres as they pass behind the head. Works on any background.
  wall   A plain-background key: the wall colour is modelled from the frame edges (a smooth
         quadratic fit, so light fall-off is fine), and everything that differs from it and
         joins the speaker becomes the person. Needs a locked camera and a plain, evenly lit
         wall that differs from hair and clothes (the "Free Space" set-up in the shot list).
  FILE   A matte made elsewhere at the same length, resized to the footage: white-on-black, or a cut-out
         with transparency (ghost-editor's matte.py WebM, CapCut "Remove background" exported as
         ProRes 4444), whose alpha channel is used.

    python3 person_matte.py footage.mp4 --source wall --out matte.mp4 --at 3-6   # to check by eye
Needs numpy, OpenCV 4.10 (opencv-python-headless==4.10.0.84) and ffmpeg.
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
    sys.exit("person_matte.py needs OpenCV: pip install opencv-python-headless==4.10.0.84")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import person_track  # noqa: E402


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


class FaceSeries:
    """Per-frame face box (shares of the frame), interpolated from the smoothed face track."""

    def __init__(self, video):
        self.track = person_track.track(video)
        if not self.track.get("person"):
            sys.exit(f"No face found in {video}: the orbit and frame escape follow the speaker's face.")
        tl = self.track["timeline"]
        self.t = np.array([p["t"] for p in tl])
        self.v = {k: np.array([p[k] for p in tl]) for k in ("cx", "top", "chin", "fh", "fw")}

    def at(self, t):
        return {k: float(np.interp(t, self.t, v)) for k, v in self.v.items()}


def head_matte(face, W, H):
    """Rough head, neck and shoulders from the face box (soft edged)."""
    cx, top, chin, fh, fw = face["cx"] * W, face["top"] * H, face["chin"] * H, face["fh"] * H, face["fw"] * W
    m = np.zeros((H, W), np.float32)
    cy = (top + chin) / 2
    cv2.ellipse(m, (int(cx), int(cy - 0.08 * fh)), (int(0.78 * fw), int(0.72 * fh)), 0, 0, 360, 1.0, -1)   # head + hair
    neck_w = 0.42 * fw
    cv2.rectangle(m, (int(cx - neck_w), int(cy)), (int(cx + neck_w), int(chin + 0.45 * fh)), 1.0, -1)
    sh_y = chin + 0.55 * fh
    pts = np.array([[cx - neck_w, chin + 0.3 * fh], [cx + neck_w, chin + 0.3 * fh],
                    [cx + 1.55 * fw, sh_y + 0.4 * fh], [cx + 1.75 * fw, H], [cx - 1.75 * fw, H],
                    [cx - 1.55 * fw, sh_y + 0.4 * fh]], np.int32)
    cv2.fillPoly(m, [pts], 1.0)
    k = int(max(3, 0.08 * fh)) | 1
    return cv2.GaussianBlur(m, (k, k), 0)


class WallKey:
    """Plain-wall key with a smooth background model and temporal smoothing."""

    def __init__(self, W, H, lo=10.0, hi=22.0, l_weight=0.35):
        self.W, self.H, self.lo, self.hi, self.lw = W, H, lo, hi, l_weight
        self.bg = None
        self.prev = None

    def fit(self, frame, face):
        small = cv2.resize(frame, (self.W // 4, self.H // 4), interpolation=cv2.INTER_AREA)
        lab = cv2.cvtColor(small, cv2.COLOR_RGB2LAB).astype(np.float32)
        h, w = lab.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w]
        chin = face["chin"] * h
        fw = face["fw"] * w
        cx = face["cx"] * w
        band = (yy < 0.12 * h) | (((xx < 0.07 * w) | (xx > 0.93 * w)) & (yy < chin + 0.6 * face["fh"] * h))
        band &= np.abs(xx - cx) > 1.3 * fw            # keep away from the speaker's head and hair
        ys, xs = yy[band].astype(np.float32) / h, xx[band].astype(np.float32) / w
        if len(xs) < 50:
            sys.exit("Not enough plain wall around the speaker to key against; use a matte file instead.")
        A = np.stack([np.ones_like(xs), xs, ys, xs * xs, ys * ys, xs * ys], 1)
        coef = [np.linalg.lstsq(A, lab[..., c][band], rcond=None)[0] for c in range(3)]
        X, Y = xx.astype(np.float32) / w, yy.astype(np.float32) / h
        basis = np.stack([np.ones_like(X), X, Y, X * X, Y * Y, X * Y], -1)
        bg = np.stack([basis @ c for c in coef], -1)
        self.bg = cv2.resize(bg, (self.W, self.H), interpolation=cv2.INTER_LINEAR)
        resid = np.sqrt(((lab[band] - bg[band]) ** 2).sum(1))
        return float(np.percentile(resid, 95))          # how plain the wall is (ΔE, 95th percentile)

    def __call__(self, frame, face):
        if self.bg is None:
            self.fit(frame, face)
        lab = cv2.cvtColor(frame, cv2.COLOR_RGB2LAB).astype(np.float32)
        d = lab - self.bg
        dist = np.sqrt(self.lw * d[..., 0] ** 2 + d[..., 1] ** 2 + d[..., 2] ** 2)
        alpha = smoothstep(self.lo, self.hi, dist).astype(np.float32)
        # keep only what joins the speaker: components touching the face, at half resolution
        hb = (cv2.resize(alpha, (self.W // 2, self.H // 2)) > 0.5).astype(np.uint8)
        hb = cv2.morphologyEx(hb, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, lab_img, stats, _ = cv2.connectedComponentsWithStats(hb, 8)
        seed = (int(face["cx"] * self.W / 2), int((face["top"] + face["chin"]) / 2 * self.H / 2))
        sx, sy = min(max(seed[0], 0), self.W // 2 - 1), min(max(seed[1], 0), self.H // 2 - 1)
        keep = lab_img == lab_img[sy, sx] if lab_img[sy, sx] else np.zeros_like(hb, bool)
        if not keep.any():                              # the seed fell in a gap: take the biggest blob near the face
            near = [i for i in range(1, n) if abs(stats[i, 0] + stats[i, 2] / 2 - sx) < self.W * 0.3]
            if near:
                keep = lab_img == max(near, key=lambda i: stats[i, 4])
        keep = keep.astype(np.uint8)
        inv = (1 - keep).copy()                         # fill holes: what the outside can't reach is inside
        cv2.floodFill(inv, None, (0, 0), 2)
        keep = np.maximum(keep, (inv == 1).astype(np.uint8))
        keep = cv2.dilate(keep, np.ones((5, 5), np.uint8))
        region = cv2.resize(keep.astype(np.float32), (self.W, self.H), interpolation=cv2.INTER_LINEAR)
        alpha = alpha * region
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
        if self.prev is not None:                       # calm edge flicker, but let real movement (hands) through
            alpha = np.where(np.abs(alpha - self.prev) < 0.25, 0.55 * alpha + 0.45 * self.prev, alpha)
        self.prev = alpha
        return alpha


class FileMatte:
    def __init__(self, path, W, H, n_frames):
        if not Path(path).is_file():
            sys.exit(f"Matte file not found: {path}")
        # a cut-out with transparency (ghost-editor's matte.py WebM, a CapCut ProRes 4444 export) carries the person
        # in its alpha channel; a plain matte video carries it as white on black
        pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,pix_fmt:stream_tags=alpha_mode",
                             "-of", "json", str(path)], capture_output=True, text=True)
        try:
            st = json.loads(pr.stdout)["streams"][0]
        except (json.JSONDecodeError, KeyError, IndexError):
            sys.exit(f"Could not read the matte video {path}.")
        tags = {k.lower(): v for k, v in st.get("tags", {}).items()}        # WebM writes ALPHA_MODE in capitals
        has_alpha = tags.get("alpha_mode") == "1" or any(a in st.get("pix_fmt", "") for a in ("yuva", "rgba", "argb", "bgra", "gbrap"))
        dec = ["-c:v", "libvpx-vp9"] if st.get("codec_name") == "vp9" and has_alpha else []   # ffmpeg's own VP9 decoder drops alpha
        vf = (f"alphaextract,scale={W}:{H}" if has_alpha else f"scale={W}:{H}")
        # streamed frame by frame (a full-length 1080x1920 matte is 4 GB in memory); effects ask for frames in order
        self.cmd = ["ffmpeg", "-v", "error", *dec, "-i", str(path), "-vf", vf, "-f", "rawvideo", "-pix_fmt", "gray", "-"]
        self.W, self.H, self.proc, self.pos, self.last = W, H, None, 0, None
        cnt = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                              "stream=nb_read_packets", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip()
        n = int(cnt) if cnt.isdigit() else 0
        if n == 0:
            sys.exit(f"Could not read the matte video {path}.")
        if abs(n - n_frames) > 2:
            print(f"note: the matte has {n} frames and the footage {n_frames}; they are matched by frame number")

    def _read(self):
        buf = self.proc.stdout.read(self.W * self.H)
        if len(buf) < self.W * self.H:
            return None
        self.pos += 1
        return np.frombuffer(buf, np.uint8).reshape(self.H, self.W)

    def __call__(self, k):
        if self.proc is None or k < self.pos - 1:          # first call, or a step back: start the stream again
            if self.proc is not None:
                self.proc.kill()
            self.proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=self.W * self.H * 2)
            self.pos, self.last = 0, None
        while self.pos <= k:
            fr = self._read()
            if fr is None:                                  # past the end: hold the last frame
                break
            self.last = fr
        if self.last is None:
            sys.exit("The matte video has no frames.")
        return self.last.astype(np.float32) / 255


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--source", default="wall", help="head, wall or a matte video file")
    ap.add_argument("--out", required=True); ap.add_argument("--at", default=None, help="START-END to check")
    a = ap.parse_args()
    import fx  # noqa: E402  (shared video reader/writer)
    info = fx.probe(a.video)
    s, e = (float(x) for x in a.at.split("-")) if a.at else (0.0, info["dur"])
    faces = FaceSeries(a.video)
    key = WallKey(info["w"], info["h"]) if a.source == "wall" else None
    fm = FileMatte(a.source, info["w"], info["h"], info["frames"]) if a.source not in ("wall", "head") else None
    with fx.Writer(a.out, info, None) as wr:
        for k, t, frame in fx.frames(a.video, info, s, e):
            face = faces.at(t)
            m = key(frame, face) if key else fm(k) if fm else head_matte(face, info["w"], info["h"])
            wr.write(np.repeat((m[..., None] * 255).astype(np.uint8), 3, 2))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
