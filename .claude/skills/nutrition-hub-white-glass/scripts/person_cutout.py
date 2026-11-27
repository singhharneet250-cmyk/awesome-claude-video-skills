#!/usr/bin/env python3
"""
Remove the background behind a person (owner request, 2026-11-26): an AI portrait matte (MODNet, Apache-2.0, run
locally with onnxruntime; the model comes from huggingface.co/Xenova/modnet on first use), refined to the frame's
own edges, steadied over time, kept to where a stronger model (BiRefNet-lite, a few
keyframes a second) sees the person so furniture never sticks to them, then the person is put on the Liquid Glass stage (or a blur, white, or your own
image or clip) with a soft contact shadow and a light wrap so they sit in the new background instead of on it.

    python3 person_cutout.py take.mp4 out.mp4                         # person on the Liquid Glass stage, 1080x1920
    python3 person_cutout.py take.mp4 out.mp4 --matte-out matte.mp4   # also write the matte (white = person) for fx.py
    python3 person_cutout.py take.mp4 out.mp4 --bg blur               # keep the room, blurred and lightened
    python3 person_cutout.py take.mp4 out.mp4 --bg /abs/store.jpg     # your own picture or clip behind you
    python3 person_cutout.py take.mp4 --preview cut.png --at 5        # one frame: matte, cut-out and result

Options:
  --size 1080x1920   output size (the take is scaled to fill it)
  --grade            give the person the soft studio grade (SKILL.md §2); on by default, --no-grade to skip
  --shadow 0.16      contact shadow strength behind the person (0 = none)
  --wrap 0.35        light wrap: how much of the new background glows into the edge
The audio is copied unchanged. Needs ffmpeg, numpy, OpenCV and onnxruntime (pip install onnxruntime).
Then: fx.py takes the matte (`--matte matte.mp4`) for the frame escape, orbit and depth scatter; timeline.py
takes out.mp4 as its source (set "grade": false, it is graded here).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import encode  # noqa: E402

try:
    import cv2
except ImportError:
    sys.exit("person_cutout.py needs OpenCV: pip install opencv-python-headless==4.10.0.84")

GRADE = "eq=brightness=0.02:contrast=0.96:saturation=0.92,colorbalance=rh=-0.01:bh=0.015"
MODEL_REPO, MODEL_FILE = "Xenova/modnet", "onnx/model.onnx"


def model_path():
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        sys.exit("person_cutout.py downloads its model with huggingface_hub: pip install huggingface_hub")
    try:
        return hf_hub_download(MODEL_REPO, MODEL_FILE)
    except Exception as e:  # network or host not allowed
        sys.exit(f"Could not download the MODNet model from huggingface.co ({e}). The cloud environment must allow "
                 "huggingface.co and its CDN hosts.")


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        v = next(s for s in d["streams"] if s.get("codec_type") == "video")
    except (json.JSONDecodeError, KeyError, StopIteration):
        sys.exit(f"Could not read {path}.")
    return {"w": int(v["width"]), "h": int(v["height"]), "rate": v.get("r_frame_rate", "30/1"),
            "dur": float(d["format"].get("duration", 0) or 0), "audio": any(s.get("codec_type") == "audio" for s in d["streams"])}


def frames(path, W, H, rate, grade, start=None, count=None):
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps={rate},unsharp=5:5:0.45:5:5:0" + \
         ("," + GRADE if grade else "")
    cmd = ["ffmpeg", "-v", "error", *(["-ss", str(start)] if start is not None else []), "-i", str(path),
           *(["-frames:v", str(count)] if count else []), "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    size = W * H * 3
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    p.stdout.close(); p.wait()


def guided(I, p, r, eps):
    """He et al. guided filter: snaps the matte to the frame's own edges (hair, turban, fingers)."""
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mI, mp = box(I), box(p)
    a = (box(I * p) - mI * mp) / (box(I * I) - mI * mI + eps)
    b = mp - a * mI
    return box(a) * I + box(b)


class Guide:
    """A second, stronger opinion a few times a second: BiRefNet-lite (MIT, huggingface.co/onnx-community/
    BiRefNet_lite-ONNX) segments the person cleanly, furniture included, but takes about 7 s a frame on a CPU, so it
    runs on keyframes (3 a second by default). Each frame keeps MODNet's detail only inside the guide: the union of the
    two nearest keyframes' person, widened by about 3% of the width so arms moving between keyframes stay whole, and
    the part both keyframes are sure of is filled (MODNet can leave holes in a plaid shirt)."""
    SW, SH = 270, 480

    def __init__(self, video, rate, grade, per_sec=3.0, cache=None):
        fps = eval(rate) if "/" in rate else float(rate)
        self.step = max(1, int(round(fps / per_sec)))
        if cache and Path(cache).is_file():
            d = np.load(cache)
            if int(d["step"]) == self.step:
                self.keys = d["keys"].astype(np.float32)
                print(f"guide: {len(self.keys)} keyframes from {cache}")
                return
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        so = ort.SessionOptions(); so.intra_op_num_threads = 4; so.enable_mem_pattern = False
        try:
            sess = ort.InferenceSession(hf_hub_download("onnx-community/BiRefNet_lite-ONNX", "onnx/model.onnx"), so,
                                        providers=["CPUExecutionProvider"])
        except Exception as e:
            sys.exit(f"Could not load BiRefNet-lite from huggingface.co ({e}); run with --guide 0 to skip it.")
        name = sess.get_inputs()[0].name
        mean, std = np.array([0.485, 0.456, 0.406], np.float32), np.array([0.229, 0.224, 0.225], np.float32)
        keys = []
        total = None
        for i, f in enumerate(frames(video, 540, 960, rate, grade)):
            if i % self.step:
                continue
            x = (cv2.resize(f, (1024, 1024), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 - mean) / std
            o = sess.run(None, {name: x.transpose(2, 0, 1)[None]})[-1][0, 0]
            keys.append(cv2.resize(1 / (1 + np.exp(-o)), (self.SW, self.SH)).astype(np.float16))
            print(f"\rguide keyframe {len(keys)}", end="", flush=True)
        print()
        self.keys = np.stack(keys).astype(np.float32)
        if cache:
            np.savez_compressed(cache, keys=self.keys.astype(np.float16), step=self.step)
        k = max(3, int(self.SW * 0.035)) | 1
        self.k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))

    def __call__(self, i, a):
        if not hasattr(self, "k"):
            k = max(3, int(self.SW * 0.035)) | 1
            self.k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        H, W = a.shape
        k0 = min(i // self.step, len(self.keys) - 1)
        k1 = min(k0 + 1, len(self.keys) - 1)
        g = (np.maximum(self.keys[k0], self.keys[k1]) > 0.5).astype(np.uint8)
        g = cv2.GaussianBlur(cv2.dilate(g, self.k).astype(np.float32), (0, 0), 1.5)
        # and fill: where both keyframes are sure it is the person (shrunk a little), MODNet's holes in a busy shirt
        # pattern are closed; MODNet keeps the edges
        core = cv2.erode((np.minimum(self.keys[k0], self.keys[k1]) > 0.5).astype(np.uint8), self.k)
        core = cv2.GaussianBlur(core.astype(np.float32), (0, 0), 1.5)
        a = a * cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
        return np.maximum(a, cv2.resize(core, (W, H), interpolation=cv2.INTER_LINEAR))


def tidy(a):
    """Keep the person as one shape: break hairline attachments (thin edges of furniture), keep the largest piece and
    anything big touching it (a hand), and keep the soft edge of what stays."""
    H, W = a.shape
    k = max(3, W // 150) | 1
    m = cv2.morphologyEx((a > 0.5).astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    if n <= 1:
        return a
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    keep = (lab == big) | np.isin(lab, [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 0.04 * stats[big, cv2.CC_STAT_AREA]])
    keep = cv2.dilate(keep.astype(np.uint8), np.ones((k + 4, k + 4), np.uint8)).astype(np.float32)
    return a * cv2.GaussianBlur(keep, (0, 0), 2)


class Matter:
    def __init__(self):
        import onnxruntime as ort
        so = ort.SessionOptions(); so.intra_op_num_threads = 4
        self.sess = ort.InferenceSession(model_path(), so, providers=["CPUExecutionProvider"])
        self.prev = None

    def __call__(self, rgb, steady=True):
        H, W = rgb.shape[:2]
        s = 512 / min(H, W)
        h, w = int(round(H * s / 32) * 32), int(round(W * s / 32) * 32)
        x = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 127.5 - 1
        a = self.sess.run(None, {"input": x.transpose(2, 0, 1)[None]})[0][0, 0]
        a = cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)
        g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
        a = np.clip(guided(g, a.astype(np.float32), max(2, W // 180), 1e-4), 0, 1)
        if steady and self.prev is not None:      # steady still edges; let real movement through at once
            calm = np.abs(a - self.prev) < 0.18
            a = np.where(calm, 0.55 * self.prev + 0.45 * a, a)
        if steady:
            self.prev = a
        a = np.where(a < 0.04, 0, np.where(a > 0.97, 1, a))
        return a.astype(np.float32)


def stage(W, H):
    """The Liquid Glass stage (brand.css --nh-stage-bg + two .nh-orb discs), drawn to match the templates."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ang = np.deg2rad(160 - 90)
    d = (xx * np.cos(ang) + yy * np.sin(ang)); d = (d - d.min()) / (d.max() - d.min())
    top, mid, bot = np.array([255, 255, 255.]), np.array([0xFA, 0xFC, 0xFE], np.float32), np.array([0xEA, 0xF0, 0xF6], np.float32)
    img = np.where(d[..., None] < 0.45, top + (mid - top) * (d[..., None] / 0.45), mid + (bot - mid) * ((d[..., None] - 0.45) / 0.55))
    g = np.exp(-(((xx - W) / (0.7 * W)) ** 2 + ((yy - 0.08 * H) / (0.45 * H)) ** 2) * 2.2)[..., None]
    img = img * (1 - 0.55 * g) + np.array([0xEA, 0xF0, 0xF6], np.float32) * 0.55 * g
    for cx, cy, r in ((W + 0.035 * W, 0.0 * H + 0.2 * H, 0.42 * W), (-0.01 * W, H - 0.22 * H, 0.36 * W)):
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        sh = np.clip(1 - np.abs(dist - r) / (0.12 * W), 0, 1) * (dist > r) * 0.05
        img = img * (1 - sh[..., None]) + np.array([32, 43, 56.]) * sh[..., None]
        disc = np.clip((r - dist) / 3, 0, 1)[..., None]
        hl = np.clip(1 - np.sqrt((xx - (cx - 0.3 * r)) ** 2 + (yy - (cy - 0.4 * r)) ** 2) / (1.4 * r), 0, 1)[..., None]
        img = img * (1 - disc) + (np.array([244, 247, 250.]) + (255 - np.array([244, 247, 250.])) * hl) * disc
    return np.clip(img, 0, 255).astype(np.float32)


def background(kind, W, H, rate):
    if kind == "stage":
        st = stage(W, H)
        while True:
            yield st
    if kind == "white":
        while True:
            yield np.full((H, W, 3), 255, np.float32)
    p = Path(kind)
    if not p.is_file():
        sys.exit(f"--bg must be stage, blur, white or a picture/clip; not found: {kind}")
    if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        im = next(frames(p, W, H, rate, False)).astype(np.float32)
        while True:
            yield im
    while True:                                   # a clip loops
        for f in frames(p, W, H, rate, False):
            yield f.astype(np.float32)


def composite(fg, a, bg, shadow, wrap):
    H, W = a.shape
    if shadow > 0:
        sh = cv2.GaussianBlur(a, (0, 0), W / 30)
        sh = np.roll(sh, int(W / 60), axis=0) * shadow
        bg = bg * (1 - sh[..., None]) + np.array([32, 43, 56.]) * sh[..., None]
    f = fg.astype(np.float32)
    if wrap > 0:                                  # the new background's light spills onto the edges
        edge = np.clip(a - cv2.erode(a, np.ones((9, 9), np.uint8)), 0, 1)
        edge = cv2.GaussianBlur(edge, (0, 0), 3)[..., None] * wrap
        f = f * (1 - edge) + cv2.GaussianBlur(bg, (0, 0), 8) * edge
    A = a[..., None]
    return np.clip(f * A + bg * (1 - A), 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("out", nargs="?")
    ap.add_argument("--bg", default="stage", help="stage (default), blur, white, or a picture or clip")
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--no-grade", action="store_true")
    ap.add_argument("--shadow", type=float, default=0.16)
    ap.add_argument("--wrap", type=float, default=0.35)
    ap.add_argument("--matte-out", help="write the matte as a grey video (white = person)")
    ap.add_argument("--guide", type=float, default=3.0,
                    help="BiRefNet-lite keyframes per second that keep furniture out (default 3, about 7 s each on a CPU; 0 = off)")
    ap.add_argument("--preview", help="write one frame (matte | cut-out | result) and stop")
    ap.add_argument("--at", type=float, default=0.0, help="--preview: which second")
    a = ap.parse_args()
    if not a.out and not a.preview:
        sys.exit("Give an output video, or --preview frame.png")
    info = probe(a.video)
    W, H = (int(v) for v in a.size.split("x"))
    rate = info["rate"]
    matter = Matter()
    grade = not a.no_grade
    guide = Guide(a.video, rate, grade, a.guide, cache=(str(a.out or a.preview) + ".guide.npz")) if a.guide > 0 else None
    if a.preview:
        f = next(frames(a.video, W, H, rate, grade, start=max(0, a.at - 0.5), count=16))
        fps0 = eval(rate) if "/" in rate else float(rate)
        i0 = int(round(max(0, a.at - 0.5) * fps0))
        for j, f in enumerate(frames(a.video, W, H, rate, grade, start=max(0, a.at - 0.5), count=16)):
            al = matter(f)
            if guide is not None:
                al = guide(i0 + j, al)
            al = tidy(al)
        bg = next(background(a.bg if a.bg != "blur" else "white", W, H, rate)) if a.bg != "blur" else \
            cv2.GaussianBlur(f.astype(np.float32), (0, 0), W / 40) * 0.8 + 255 * 0.2
        res = composite(f, al, bg, a.shadow, a.wrap)
        m3 = (np.repeat(al[..., None], 3, 2) * 255).astype(np.uint8)
        cut = (f * al[..., None] + np.array([255, 0, 255]) * (1 - al[..., None])).astype(np.uint8)
        both = np.concatenate([m3, cut, res], axis=1)
        cv2.imwrite(a.preview, cv2.cvtColor(both, cv2.COLOR_RGB2BGR))
        print(f"preview → {a.preview} (matte | cut-out | result)")
        return
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", rate, "-i", "-",
                            "-i", str(a.video), "-map", "0:v", "-map", "1:a?", *encode.WORK,
                            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", "-shortest", a.out], stdin=subprocess.PIPE)
    menc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", rate, "-i", "-",
                             "-c:v", "libx264", "-crf", "4", "-pix_fmt", "yuv420p", a.matte_out], stdin=subprocess.PIPE) if a.matte_out else None
    bgs = background(a.bg, W, H, rate) if a.bg != "blur" else None
    n = 0
    fps = eval(rate) if "/" in rate else float(rate)
    for f in frames(a.video, W, H, rate, grade):
        al = matter(f)
        if guide is not None:
            al = guide(n, al)
        al = tidy(al)
        bg = next(bgs) if bgs is not None else cv2.GaussianBlur(f.astype(np.float32), (0, 0), W / 40) * 0.8 + 255 * 0.2
        enc.stdin.write(composite(f, al, bg, a.shadow, a.wrap).tobytes())
        if menc:
            menc.stdin.write((al * 255).astype(np.uint8).tobytes())
        n += 1
        if n % int(fps * 2) == 0:
            print(f"\r{n / fps:.0f} / {info['dur']:.0f} s", end="", flush=True)
    enc.stdin.close(); enc.wait()
    if menc:
        menc.stdin.close(); menc.wait()
    print(f"\rwrote {a.out} ({n} frames)" + (f" and the matte {a.matte_out}" if a.matte_out else ""))


if __name__ == "__main__":
    main()
