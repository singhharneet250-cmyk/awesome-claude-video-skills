#!/usr/bin/env python3
"""
Real glass over footage (learned from the owner's "liquid glass" reference): CSS blur only smears; real glass
bends light at a rigid rim, splits colour a little at the edge, and catches the light along its rim. An overlay
rendered on its own can't see the footage behind it, so this script does the glass at composite time: under every
glass panel it refracts the footage through a rounded slab (Snell, IOR 1.5), frosts it, adds a white tint until ink
text reads, puts a thin specular rim on the lit edge, then lays the overlay's words and icons on top.

    # 1) two passes of the same overlay (render.cjs): words and icons with clear panels, and the panel shapes
    node render.cjs "chat-takeover.html?bottom=560" --transparent --real-glass --out chat.mov
    node render.cjs "chat-takeover.html?bottom=560" --transparent --glass-mask --out chat.mask.mov
    # 2) composite them onto the footage at 10 s
    python3 glass.py take.mp4 out.mp4 --content chat.mov --mask chat.mask.mov --at 10

    # a side-by-side check: flat glass (today's near-opaque panels) on the left, real glass on the right
    python3 glass.py take.mp4 compare.mp4 --content chat.mov --mask chat.mask.mov --at 10 --compare flat.mov

timeline.py render does all of this for every overlay ("glass": "real" is the default; "flat" switches it off).

Options (sizes are for a 1080 px wide frame and scale with it):
  --frost 8       blur of the footage seen through the glass, px (White Glass is frosted; 0 = clear liquid glass)
  --tint auto     white mixed into the glass: auto keeps the glass porcelain-light for ink text (about 0.86 luminance)
                  over any footage, smoothed over time; or a number 0-1
  --rim 20        width of the bevelled rim that bends the light, px
  --ior 1.5       index of refraction (1.5 = glass); higher bends more
  --dispersion 0.6  colour split at the rim (0 = none; real glass keeps it faint)
  --light 0.85    strength of the rim highlight (light from the top left, turning a little as the panel moves)
  --variant regular  regular (frosted, adapts to stay legible: the White Glass default) or clear (see-through, only
                  for panels without small text), after Apple's Liquid Glass variants
A panel "materializes" the way Apple's Liquid Glass does: as the overlay's reveal brings it in, the lensing, frost,
tint and rim grow together instead of a flat fade.
Audio and everything outside the overlay's time are copied from the footage. Needs ffmpeg, numpy and OpenCV.
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
    sys.exit("glass.py needs OpenCV: pip install opencv-python-headless")


def probe(path):
    if not Path(path).is_file():
        sys.exit(f"File not found: {path}")
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        v = next(s for s in d["streams"] if s.get("codec_type") == "video")
    except (json.JSONDecodeError, KeyError, StopIteration):
        sys.exit(f"Could not read {path}.")
    n, k = v.get("r_frame_rate", "30/1").split("/")
    return {"w": int(v["width"]), "h": int(v["height"]), "rate": v.get("r_frame_rate", "30/1"), "fps": float(n) / float(k or 1),
            "dur": float(d.get("format", {}).get("duration", 0) or 0), "audio": any(s.get("codec_type") == "audio" for s in d["streams"])}


def frames(path, w, h, fmt="rgb24", rate=None):
    ch = 4 if fmt == "rgba" else 3
    vf = f"scale={w}:{h}" + (f",fps={rate}" if rate else "")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", vf, "-f", "rawvideo", "-pix_fmt", fmt, "-"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    size = w * h * ch
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, ch)
    p.stdout.close()
    p.wait()


class Glass:
    def __init__(self, scale, frost, tint, rim, ior, dispersion, light, variant="regular"):
        if variant == "clear":                                  # Apple's clear variant: more see-through, for panels without small text
            frost, tint = min(frost, 2.0), (0.18 if tint == "auto" else tint)
        self.s, self.frost, self.tint, self.ior, self.disp, self.light = scale, frost * scale, tint, ior, dispersion, light
        self.rim = max(4.0, rim * scale)
        self.t_smooth = None
        self.W = None

    def apply(self, base, mask):
        """base: HxWx3 uint8 footage; mask: HxW float 0-1 (the glass panels). Returns the footage with glass."""
        if mask.max() < 0.02:
            return base
        H, W = mask.shape
        ys, xs = np.nonzero(mask > 0.02)
        pad = int(self.rim * 2 + self.frost * 3 + 8)
        y0, y1, x0, x1 = max(0, ys.min() - pad), min(H, ys.max() + pad + 1), max(0, xs.min() - pad), min(W, xs.max() + pad + 1)
        m = mask[y0:y1, x0:x1]
        src = base[y0:y1, x0:x1].astype(np.float32)
        # materialize (Apple's Liquid Glass): a panel appears by bending light in, not by fading; its opacity in the
        # mask (the HTML reveal) drives the lensing, frost, tint and rim together
        k = float(np.clip(m.max(), 0, 1)) ** 0.8
        frosted = cv2.GaussianBlur(src, (0, 0), self.frost * k) if self.frost * k > 0.3 else src
        # the highlight answers movement: the light turns a little as the panel moves across the frame
        cy_, cx_ = [float(v.mean()) for v in np.nonzero(m > 0.5)] if (m > 0.5).any() else (H / 2 - y0, W / 2 - x0)
        ang = np.deg2rad(-124 + 28 * ((cx_ + x0) / W - 0.5) + 14 * ((cy_ + y0) / H - 0.5))
        L = np.array([np.cos(ang), np.sin(ang)])
        inside = (m > 0.5).astype(np.uint8)
        d = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
        u = np.clip(d / self.rim, 0, 1)
        z = np.sqrt(1 - (1 - u) ** 2)                            # a rounded slab: steep at the rim, flat in the middle
        z = cv2.GaussianBlur(z, (0, 0), 1.2)
        gx = cv2.Sobel(z, cv2.CV_32F, 1, 0, ksize=3) / 8
        gy = cv2.Sobel(z, cv2.CV_32F, 0, 1, ksize=3) / 8
        bend = self.rim * (1 - 1 / self.ior) * 3.4 * k           # how far the rim pulls the picture, px
        X, Y = np.meshgrid(np.arange(x1 - x0, dtype=np.float32), np.arange(y1 - y0, dtype=np.float32))
        out = np.empty_like(src)
        for c, k in enumerate((1.0, 1.0 + 0.045 * self.disp, 1.0 + 0.09 * self.disp)):   # R, G, B bend a little differently
            out[..., c] = cv2.remap(np.ascontiguousarray(frosted[..., c]), X - gx * bend * k, Y - gy * bend * k,
                                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        lum = float((out[..., 0] * 0.2126 + out[..., 1] * 0.7152 + out[..., 2] * 0.0722)[m > 0.5].mean() / 255) if (m > 0.5).any() else 1.0
        if self.tint == "auto":
            t = float(np.clip((0.86 - lum) / max(1e-3, 1 - lum), 0.35, 0.85))    # porcelain-light: ink text always reads
            self.t_smooth = t if self.t_smooth is None else self.t_smooth + 0.12 * (t - self.t_smooth)   # no flicker
            t = self.t_smooth * k
        else:
            t = float(self.tint) * k
        tmap = t * (0.42 + 0.58 * u)                             # the rim stays clearer, so the bent picture shows there
        out = out * (1 - tmap[..., None]) + 255 * tmap[..., None]
        g = np.sqrt(gx ** 2 + gy ** 2) + 1e-6
        facing = np.clip(-(gx * L[0] + gy * L[1]) / g, -1, 1)   # +1 where the rim faces the light (top left)
        band = (1 - u) * (g > 1e-3)
        line = np.exp(-d / (1.0 * self.s)) * inside              # the rigid rim: a thin bright line all round
        spec = (np.clip(facing, 0, 1) ** 2 * band ** 3 * 0.85 + line * (0.35 + 0.45 * np.clip(facing, 0, 1))) * self.light * k
        shade = np.clip(-facing, 0, 1) * band ** 2 * 0.2 * self.light * k
        out = out * (1 - shade[..., None])
        out = out + (255 - out) * np.clip(spec, 0, 1)[..., None]
        res = base.copy()
        a = np.clip(m * 3, 0, 1)[..., None]                       # the shape is there at once; the glass itself grows in
        res[y0:y1, x0:x1] = np.clip(src * (1 - a) + out * a, 0, 255).astype(np.uint8)
        return res


def over(base, rgba):
    a = rgba[..., 3:4].astype(np.float32) / 255
    return (base.astype(np.float32) * (1 - a) + rgba[..., :3].astype(np.float32) * a).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base"); ap.add_argument("out")
    ap.add_argument("--content", required=True, help="overlay pass rendered with --transparent --real-glass")
    ap.add_argument("--mask", required=True, help="the same overlay rendered with --transparent --glass-mask")
    ap.add_argument("--at", type=float, default=0.0, help="where the overlay starts in the footage, seconds")
    ap.add_argument("--frost", type=float, default=8.0)
    ap.add_argument("--tint", default="auto")
    ap.add_argument("--rim", type=float, default=20.0)
    ap.add_argument("--ior", type=float, default=1.5)
    ap.add_argument("--dispersion", type=float, default=0.6)
    ap.add_argument("--light", type=float, default=0.85)
    ap.add_argument("--variant", choices=["regular", "clear"], default="regular")
    ap.add_argument("--compare", metavar="FLAT.mov", help="write a side-by-side: this flat-glass overlay left, real glass right")
    a = ap.parse_args()
    if a.tint != "auto":
        try:
            a.tint = float(a.tint)
        except ValueError:
            sys.exit("--tint is auto or a number 0-1")

    bi = probe(a.base)
    W, H = bi["w"], bi["h"]
    glass = Glass(W / 1080, a.frost, a.tint, a.rim, a.ior, a.dispersion, a.light, a.variant)
    start = int(round(a.at * bi["fps"]))
    content = frames(a.content, W, H, "rgba", bi["rate"])
    mask = frames(a.mask, W, H, "rgba", bi["rate"])
    flat = frames(a.compare, W, H, "rgba", bi["rate"]) if a.compare else None
    OW = W * 2 if flat else W
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{H}", "-r", bi["rate"], "-i", "-",
                            "-i", str(a.base), "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", "-shortest", a.out], stdin=subprocess.PIPE)
    n = 0
    for i, f in enumerate(frames(a.base, W, H, "rgb24", bi["rate"])):
        out, left = f, f
        if i >= start:
            c, m = next(content, None), next(mask, None)
            if c is not None and m is not None:
                out = over(glass.apply(f, m[..., 3].astype(np.float32) / 255), c)
            if flat is not None:
                fl = next(flat, None)
                left = over(f, fl) if fl is not None else f
        if flat is not None:
            out = np.concatenate([left, out], axis=1)
            cv2.line(out, (W, 0), (W, H), (255, 255, 255), max(2, W // 540))
        enc.stdin.write(np.ascontiguousarray(out).tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    print(f"wrote {a.out} ({n} frames" + (", flat left | real right)" if flat is not None else ")"))


if __name__ == "__main__":
    main()
