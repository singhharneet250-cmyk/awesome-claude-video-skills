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
  --strength 0.9  the iOS 27 Liquid Glass slider: 0 = opaque porcelain, 1 = completely clear. It sets the frost
                  and the auto tint together. House default since 2026-11-26 (owner): clear, 0.9
  --frost 8       blur of the footage seen through the glass, px (overrides the strength's frost; 0 = clear)
  --tint auto     white mixed into the glass: auto adapts to the footage so ink text reads (target luminance 0.85
                  at strength 0.4, 0.73 at 0.9), smoothed over time; or a number 0-1
  --rim 32        width of the thick rounded edge that bends the light, px
  --liquid 1.0    how far that edge bends the picture, easing from the edge to the flat face like a drop of
                  water (0 = a flat slab; the owner asked for a liquid, glossy look)
  --ior 1.5       index of refraction (1.5 = glass); higher bends more
  --dispersion 0.8  colour split at the rim (0 = none; real glass keeps it faint)
  --light 0.85    strength of the rim highlight (light from the top left, turning a little as the panel moves)
  --grad 1.0      gradient tint (owner, 2026-11-26): warm peach at the lit corner, white, cool ice at the far corner
                  (light tints of the brand orange and ice; 0 = plain porcelain white)
  --gloss 1.0     the polished-glass highlights: a soft sheen across the face toward the light, a bloom on the key
                  highlight, a fainter line on the far rim (light caught inside the slab) and fresnel on every edge
  --variant clear  clear (strength 0.9, the house default) or regular (strength 0.4, frosted), after Apple's Liquid
                  Glass variants. Clear glass keeps the brand's ink text (owner's choice): its legibility layer is a
                  light porcelain one, where iOS puts a dark dimming layer under white text. No glow or shadow
                  around words, and no drop shadow under the glass
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import encode  # noqa: E402  (visually lossless output; encode.py deliver for the final file)

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
    def __init__(self, scale, frost, tint, rim=32, ior=1.5, dispersion=0.8, light=0.85, strength=0.9, gloss=1.0, liquid=1.0, grad=1.0):
        # one slider, like iOS 27's Liquid Glass control: 0 = opaque porcelain, 1 = completely clear
        strength = float(np.clip(strength, 0, 1))
        if frost is None:
            frost = max(0.0, 14 - 15 * strength)
        self.target, self.tmin = 0.95 - 0.25 * strength, max(0.05, 0.6 - 0.62 * strength)
        self.s, self.frost, self.tint, self.ior, self.disp, self.light = scale, frost * scale, tint, ior, dispersion, light
        self.rim = max(4.0, rim * scale)
        self.grad = grad                                 # gradient tint: 0 = plain white
        self.gloss, self.liquid = gloss, liquid          # liquid: how far the rounded edge bends the picture (0 = none)
        self.t_smooth = None
        self.W = None

    # gradient glass (owner, 2026-11-26): the tint runs from a warm peach at the lit corner, through white, to a cool
    # ice blue at the far corner, both light tints of the brand's orange and ice, so ink text still reads everywhere
    WARM, COOL = np.array([255, 214, 182], np.float32), np.array([196, 216, 242], np.float32)

    def tint_field(self, inside, L, w, h):
        if self.grad <= 0 or not inside.any():
            return np.float32(255)
        ys, xs = np.nonzero(inside)
        cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
        hx, hy = max(1.0, (xs.max() - xs.min()) / 2), max(1.0, (ys.max() - ys.min()) / 2)
        X, Y = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        p = np.clip(((X - cx) * L[0] + (Y - cy) * L[1]) / (abs(L[0]) * hx + abs(L[1]) * hy), -1, 1)[..., None]   # +1 lit
        white = np.float32(255)
        col = np.where(p > 0, white + (self.WARM - white) * p, white + (self.COOL - white) * -p)
        return white + (col - white) * self.grad

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
        # liquid lensing (owner: "liquid glossy"): a thick, rounded edge pulls the picture in across the whole rim,
        # strongest at the edge and easing to nothing where the face turns flat, like a drop of water
        gn = np.sqrt(gx ** 2 + gy ** 2) + 1e-4
        amp = self.rim * (1 - 1 / self.ior) * 2.2 * self.liquid * k * cv2.GaussianBlur((1 - u) ** 2, (0, 0), 1.0)
        nx, ny = gx / gn * amp, gy / gn * amp
        X, Y = np.meshgrid(np.arange(x1 - x0, dtype=np.float32), np.arange(y1 - y0, dtype=np.float32))
        out = np.empty_like(src)
        for c, kc in enumerate((1.0, 1.0 + 0.045 * self.disp, 1.0 + 0.09 * self.disp)):   # R, G, B bend a little differently
            out[..., c] = cv2.remap(np.ascontiguousarray(frosted[..., c]), X - nx * kc, Y - ny * kc,
                                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        ly = (out[..., 0] * 0.2126 + out[..., 1] * 0.7152 + out[..., 2] * 0.0722)[..., None]
        out = np.clip(ly + (out - ly) * (1 + 0.25 * k), 0, 255)            # vibrancy: the bent picture a touch richer
        lum = float((out[..., 0] * 0.2126 + out[..., 1] * 0.7152 + out[..., 2] * 0.0722)[m > 0.5].mean() / 255) if (m > 0.5).any() else 1.0
        if self.tint == "auto":
            t = float(np.clip((self.target - lum) / max(1e-3, 1 - lum), self.tmin, 0.9))   # light enough that ink text reads
            self.t_smooth = t if self.t_smooth is None else self.t_smooth + 0.12 * (t - self.t_smooth)   # no flicker
            t = self.t_smooth * k
        else:
            t = float(self.tint) * k
        tmap = t * (0.42 + 0.58 * u)                             # the rim stays clearer, so the bent picture shows there
        col = self.tint_field(inside, L, x1 - x0, y1 - y0)
        out = out * (1 - tmap[..., None]) + col * tmap[..., None]
        if self.grad > 0:                                        # tinted glass filters the light it lets through
            out = out * (1 - 0.55 * k * (1 - col / 255))
        g = np.sqrt(gx ** 2 + gy ** 2) + 1e-6
        facing = np.clip(-(gx * L[0] + gy * L[1]) / g, -1, 1)   # +1 where the rim faces the light (top left)
        band = (1 - u) * (g > 1e-3)
        line = np.exp(-d / (1.0 * self.s)) * inside              # the rigid rim: a thin bright line all round
        lit, far = np.clip(facing, 0, 1), np.clip(-facing, 0, 1)
        # gloss (owner: "realistic glossy"), as polished glass shows it:
        #  key      a crisp specular along the rim that faces the light, brightest where the corner curves into it
        #  bloom    that highlight glows a little into the glass, as a bright reflection does in a lens
        #  far edge light caught inside the slab leaves a fainter line on the opposite rim, just past a soft shade
        #  fresnel  every edge reflects more than the face (grazing angle), so the rim reads glassy all round
        #  sheen    the polished face reflects a broad soft light: brighter toward the light, falling off across the
        #           panel with a soft edge; it moves as the panel moves, so it never looks painted on
        G = self.gloss * self.light * k
        key = (lit ** 2 * band ** 2.2 * 1.0 + line * (0.45 + 0.55 * lit)) * self.light * k
        bloom = cv2.GaussianBlur(key, (0, 0), 5.0 * self.s) * 0.6 * self.gloss
        back = (far ** 2 * np.exp(-d / (1.8 * self.s)) * 0.6 + far ** 3 * band ** 4 * 0.25) * G
        fres = band ** 2 * 0.18 * G
        ys_, xs_ = np.nonzero(inside)
        if len(ys_):
            pcx, pcy = (xs_.min() + xs_.max()) / 2, (ys_.min() + ys_.max()) / 2
            hx, hy = max(1.0, (xs_.max() - xs_.min()) / 2), max(1.0, (ys_.max() - ys_.min()) / 2)
            pr = ((X - pcx) * L[0] + (Y - pcy) * L[1]) / (abs(L[0]) * hx + abs(L[1]) * hy)   # +1 at the lit corner
            q = ((X - pcx) * -L[1] + (Y - pcy) * L[0]) / (abs(L[1]) * hx + abs(L[0]) * hy)   # across the light
            pr = pr + 0.22 * q ** 2                              # a softbox seen in a polished face: a curved edge
            ss_ = lambda e0, e1, v: np.clip((v - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((v - e0) / (e1 - e0), 0, 1))
            face = cv2.GaussianBlur(np.clip(u * 1.4, 0, 1), (0, 0), 2.0) * inside
            sheen = (0.10 * ss_(-0.6, 1.0, pr) + 0.24 * ss_(0.22, 0.46, pr)) * face * G
        else:
            sheen = 0.0
        shade = far * band ** 2 * 0.14 * self.light * k * (1 - np.exp(-d / (2.5 * self.s)))
        out = out * (1 - shade[..., None])
        out = out + (255 - out) * np.clip(sheen + fres, 0, 1)[..., None]
        out = out + (255 - out) * np.clip(key + bloom + back, 0, 1)[..., None]
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
    ap.add_argument("--strength", type=float, help="0 opaque … 1 clear (default 0.9; 0.4 with --variant regular)")
    ap.add_argument("--frost", type=float)
    ap.add_argument("--tint", default="auto")
    ap.add_argument("--rim", type=float, default=32.0)
    ap.add_argument("--ior", type=float, default=1.5)
    ap.add_argument("--dispersion", type=float, default=0.8)
    ap.add_argument("--light", type=float, default=0.85)
    ap.add_argument("--grad", type=float, default=1.0, help="gradient tint, warm peach (lit corner) to cool ice (0 = plain white)")
    ap.add_argument("--liquid", type=float, default=1.0, help="how far the thick rounded edge bends the picture (0 = flat slab)")
    ap.add_argument("--gloss", type=float, default=1.0, help="sheen, bloom, far-edge and fresnel highlights (0 = rim light only)")
    ap.add_argument("--variant", choices=["clear", "regular"], default="clear")
    ap.add_argument("--compare", metavar="FLAT.mov", help="write a side-by-side: this flat-glass overlay left, real glass right")
    a = ap.parse_args()
    if a.tint != "auto":
        try:
            a.tint = float(a.tint)
        except ValueError:
            sys.exit("--tint is auto or a number 0-1")

    bi = probe(a.base)
    W, H = bi["w"], bi["h"]
    strength = a.strength if a.strength is not None else (0.9 if a.variant == "clear" else 0.4)
    glass = Glass(W / 1080, a.frost, a.tint, a.rim, a.ior, a.dispersion, a.light, strength, a.gloss, a.liquid, a.grad)
    start = int(round(a.at * bi["fps"]))
    content = frames(a.content, W, H, "rgba", bi["rate"])
    mask = frames(a.mask, W, H, "rgba", bi["rate"])
    flat = frames(a.compare, W, H, "rgba", bi["rate"]) if a.compare else None
    OW = W * 2 if flat else W
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{H}", "-r", bi["rate"], "-i", "-",
                            "-i", str(a.base), "-map", "0:v", "-map", "1:a?", *encode.WORK, "-c:a", "copy", "-movflags", "+faststart", "-shortest", a.out], stdin=subprocess.PIPE)
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
