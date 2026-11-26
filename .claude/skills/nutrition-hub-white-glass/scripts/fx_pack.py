#!/usr/bin/env python3
"""
The R7 effect pack for fx.py (SKILL.md §4 K): five more person-aware footage effects in the White Glass
look. Run them through fx.py, which follows the head (motion_track.py) and supplies the person matte:

  sticky     a porcelain sticker (optional orange number badge) that sticks to the speaker's chest,
             head or hand and follows them      fx.py sticky in.mp4 out.mp4 --at 3-5 --text "3-5 g a day" --anchor chest
  wipe       before + after: a white light bar sweeps across; "Before" stays on the left until the bar
             passes, "After" is revealed         fx.py wipe graded.mp4 out.mp4 --at 2-4.5 --before raw.mp4
  pullback   the picture pulls back into a White Glass editor (checklist, timeline with the real audio
             waveform), then pushes back in        fx.py pullback in.mp4 out.mp4 --at 6-9
  scatter    depth scatter: one big word behind the speaker's head, one in front; the letters fly in from
             scattered depths and fly apart at the end   fx.py scatter in.mp4 out.mp4 --at 5-7.5 --words "Label,first"
  bgswap     green screen without a green screen: the room behind the speaker becomes a clip, an image,
             the ice-mist stage or a soft blur     fx.py bgswap in.mp4 out.mp4 --at 2-5 --matte wall --bg broll/shelf.mp4

Rules (SKILL.md §4 K): before + after only for edits, grades or product comparisons, never body or
health results; scatter words are one or two short words; green screen backgrounds are your own,
licensed or the stage, never memes or other people's footage.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import cv2

HERE = Path(__file__).resolve().parent
SK = HERE.parent
import fx  # noqa: E402  (shared io, easing, colours, sprites)

BEBAS = SK / "assets" / "fonts" / "BebasNeue-Regular.ttf"


# ---------------------------------------------------------------- sprites
def text_sprite(text, px, color, font_path=None, shadow=0.35, pad=None):
    """RGBA float sprite of text with a soft shadow (for words straight on footage)."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    font = ImageFont.truetype(str(font_path or fx.find_font()), int(px))
    l, t, r, b = font.getbbox(text)
    pad = pad or int(px * 0.25)
    w, h = r - l + 2 * pad, b - t + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l, pad - t + px * 0.04), text, font=font, fill=(20, 27, 36, int(255 * shadow)))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(px * 0.06)))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=font, fill=tuple(int(c * 255) for c in color) + (255,))
    return np.asarray(im).astype(np.float32) / 255


def sticker(text, height, badge=None):
    """A porcelain sticker with ink text and an optional orange badge, no shadow, RGBA float."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    ss = 2
    hp = int(height * ss)
    font = ImageFont.truetype(fx.find_font(), int(hp * 0.44))
    bfont = ImageFont.truetype(fx.find_font(), int(hp * 0.34))
    tw = int(font.getlength(text))
    bw = int(hp * 0.62) if badge else 0
    w = tw + int(hp * 0.7) + (bw + int(hp * 0.18) if badge else 0)
    pad = int(hp * 0.45)
    im = Image.new("RGBA", (w + 2 * pad, hp + 2 * pad), (0, 0, 0, 0))
    # no drop shadow beside the words (owner, 2026-11-26)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((pad, pad, pad + w, pad + hp), int(hp * 0.28), fill=(255, 255, 255, 250), outline=(32, 43, 56, 22), width=ss)
    x = pad + int(hp * 0.32)
    if badge:
        d.rounded_rectangle((x, pad + hp * 0.2, x + bw, pad + hp * 0.8), int(hp * 0.16), fill=(240, 120, 43, 255))
        d.text((x + bw / 2, pad + hp / 2), str(badge), font=bfont, fill=(255, 255, 255, 255), anchor="mm")
        x += bw + int(hp * 0.18)
    d.text((x, pad + hp / 2), text, font=font, fill=(32, 43, 56, 255), anchor="lm")
    im = im.resize((im.width // ss, im.height // ss), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255


def rotate(rgba, deg, scale=1.0):
    h, w = rgba.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), deg, scale)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw, nh = int(h * sin + w * cos) + 2, int(h * cos + w * sin) + 2
    m[0, 2] += nw / 2 - w / 2
    m[1, 2] += nh / 2 - h / 2
    pm = rgba.copy(); pm[..., :3] *= pm[..., 3:4]                      # rotate premultiplied, so edges stay clean
    out = cv2.warpAffine(pm, m, (nw, nh), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    a = out[..., 3:4]
    out[..., :3] = np.where(a > 1e-4, out[..., :3] / np.maximum(a, 1e-4), 0)
    return out


def blur(rgba, sigma):
    if sigma < 0.3:
        return rgba
    pm = rgba.copy(); pm[..., :3] *= pm[..., 3:4]
    k = int(sigma * 3) * 2 + 1
    pad = k
    pm = cv2.copyMakeBorder(pm, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
    pm = cv2.GaussianBlur(pm, (k, k), sigma)
    a = pm[..., 3:4]
    pm[..., :3] = np.where(a > 1e-4, pm[..., :3] / np.maximum(a, 1e-4), 0)
    return pm


# ---------------------------------------------------------------- effects
class Sticky:
    def __init__(self, a, W, H, fh_px):
        if not a.text:
            sys.exit("sticky needs --text, e.g. --text \"3-5 g a day\" (and optionally --badge 12).")
        self.spr = sticker(a.text, max(0.7 * fh_px, 0.045 * H), a.badge)     # readable in wide shots too
        self.pos = None
        self.a, self.W, self.H = a, W, H

    def __call__(self, f, matte, face, t, hands, **_):
        a, W, H = self.a, self.W, self.H
        k = fx.envelope(t, a.s, a.e)
        if k <= 0:
            return f
        fw, fh = face["fw"] * W, face["fh"] * H
        cx, chin = face["cx"] * W, face["chin"] * H
        side = -1 if cx > W / 2 else 1                                   # lean into the free side
        if a.anchor == "hand" and hands:
            hnd = min(hands, key=lambda h: abs(h["cx"] * W - (cx + side * fw)))
            target = (hnd["cx"] * W, hnd["cy"] * H - 0.9 * fh)
        elif a.anchor == "head":
            target = (cx + side * 1.6 * fw, face["top"] * H + 0.2 * fh)
        else:
            target = (cx + side * 0.9 * fw, chin + 1.25 * fh)
        p = np.array(target, np.float32)
        self.pos = p if self.pos is None else self.pos + 0.35 * (p - self.pos)   # sticks, with a little lag
        spr = rotate(self.spr, -5 - 5 * (1 - k), 0.9 + 0.1 * k)
        spr = spr.copy(); spr[..., 3:] *= k
        x = np.clip(self.pos[0], spr.shape[1] / 2 + 72 * W / 1080, W - spr.shape[1] / 2 - 72 * W / 1080)
        y = np.clip(self.pos[1], 250 * H / 1920, 1500 * H / 1920)
        fx.over(f, spr, x - spr.shape[1] / 2, y - spr.shape[0] / 2)
        return f


class Wipe:
    SWEEP = 0.9

    def __init__(self, a, W, H, fh_px, info):
        if not a.before:
            sys.exit("wipe needs --before FILE: the same take before the edit (e.g. the ungraded reframe).")
        bi = fx.probe(a.before)
        self.reader = fx.frames(a.before, {**info, "dur": bi["dur"]}, a.s, a.e + 0.1)
        labels = [x.strip() for x in (getattr(a, "words", None) or "Before,After").split(",")][:2] + ["After"]
        self.chip_b = fx.chip(labels[0], 0.42 * fh_px)
        self.chip_a = fx.chip(labels[1], 0.42 * fh_px)
        self.a, self.W, self.H = a, W, H
        # "line" (the attention style of the owner's liquid-glass reference, R18): the divider keeps moving, a glass
        # handle rides it, the labels sit at the top under an optional headline pill ("Same reel. Watch the line.")
        self.line = getattr(a, "mode", "sweep") == "line"
        if self.line:
            self.handle = self._handle(int(78 * W / 1080))
            self.head = fx.chip(a.text, 0.5 * fh_px) if getattr(a, "text", None) else None
        xs = np.arange(W, dtype=np.float32)
        self.xs = xs

    @staticmethod
    def _handle(d):
        """A clear Liquid Glass knob with two ink chevrons, no shadow: RGBA plus the knob's shape (fx.over puts glass
        under it)."""
        from PIL import Image, ImageDraw
        ss, pad = 3, d // 3
        D, P = d * ss, pad * ss
        im = Image.new("RGBA", (D + 2 * P, D + 2 * P), (0, 0, 0, 0))   # no drop shadow (owner, 2026-11-26)
        knob = Image.new("L", im.size, 0)
        ImageDraw.Draw(knob).ellipse((P, P, P + D, P + D), fill=255)
        g = ImageDraw.Draw(im)
        c, r, w = P + D / 2, D * 0.13, int(ss * 2.6)
        for sgn in (-1, 1):
            x = c + sgn * D * 0.13
            g.line([(x + sgn * -r * 0.0, c - r), (x + sgn * r * 0.8, c), (x, c + r)], fill=(32, 43, 56, 255), width=w, joint="curve")
        size = (im.width // ss, im.height // ss)
        im = im.resize(size, Image.LANCZOS)
        return np.dstack([np.asarray(im).astype(np.float32) / 255, np.asarray(knob.resize(size, Image.LANCZOS)).astype(np.float32) / 255])

    def __call__(self, f, matte, face, t, **_):
        a, W, H = self.a, self.W, self.H
        try:
            _, _, bf = next(self.reader)
            before = bf.astype(np.float32) / 255
        except StopIteration:
            before = f
        k = fx.envelope(t, a.s, a.e)
        if k <= 0:
            return f
        if self.line:
            P = max(2.4, min(4.0, a.e - a.s))                            # one slow swing right, left and back
            bar = W * (0.5 + 0.3 * np.sin(2 * np.pi * (t - a.s) / P) * k)
            m = np.clip((self.xs - bar) / 2 + 0.5, 0, 1)[None, :, None]
            out = before * (1 - m) + f * m
            d = np.abs(self.xs - bar)
            glow = (np.exp(-(d / 2.2) ** 2) * 0.95 + np.exp(-(d / 40) ** 2) * 0.16)[None, :, None] * k
            out = out * (1 - glow) + fx.WHITE * glow
            hd = self.handle.copy(); hd[..., 3:] *= k
            fx.over(out, hd, bar - hd.shape[1] / 2, 0.52 * H - hd.shape[0] / 2)           # chest height: clear of the face and the lower overlays
            cb, ca = self.chip_b.copy(), self.chip_a.copy()
            cb[..., 3:] *= k; ca[..., 3:] *= k
            u = W / 1080
            fx.over(out, cb, 72 * u, 0.2 * H)
            fx.over(out, ca, W - 72 * u - ca.shape[1], 0.2 * H)
            if self.head is not None:
                hh = self.head.copy(); hh[..., 3:] *= k
                fx.over(out, hh, (W - hh.shape[1]) / 2, 0.135 * H - hh.shape[0] / 2)
            return out
        start = a.s + 0.35
        p = fx.ease_out(min(1, max(0, (t - start) / self.SWEEP))) if t >= start else 0.0
        bar = W * (1.04 - 1.08 * p)                                       # sweeps right → left
        m = np.clip((self.xs - bar) / 3 + 0.5, 0, 1)[None, :, None]       # 1 = after (right of the bar)
        out = before * (1 - m) + f * m
        if 0 < p < 1:
            d = np.abs(self.xs - bar)
            glow = (np.exp(-(d / 5) ** 2) * 0.9 + np.exp(-(d / 60) ** 2) * 0.35)[None, :, None]
            out = out * (1 - glow) + fx.WHITE * glow
        y = 0.58 * H
        cb, ca = self.chip_b.copy(), self.chip_a.copy()
        cb[..., 3:] *= k * (1 - p)
        ca[..., 3:] *= k * min(1, p * 3)
        fx.over(out, cb, 72 * W / 1080, y)
        fx.over(out, ca, W - 72 * W / 1080 - ca.shape[1], y)
        return out


class Pullback:
    def __init__(self, a, W, H, fh_px, info):
        self.a, self.W, self.H = a, W, H
        self.rect = (0.07 * W, 0.15 * H, 0.66 * W, 0.62 * H)             # the picture inside the editor
        self.chrome = self._chrome(a.video, info)

    def _chrome(self, video, info):
        from PIL import Image, ImageDraw, ImageFont
        W, H = self.W, self.H
        g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        base = (fx.WHITE * (1 - g) + fx.ICE * g)
        im = Image.fromarray((np.repeat(base, W, 1) * 255).astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(im)
        f = lambda s, b=False: ImageFont.truetype(fx.find_font(), int(s * W / 1080))
        u = W / 1080
        d.rounded_rectangle((40 * u, 60 * u, W - 40 * u, 150 * u), int(26 * u), fill=(255, 255, 255, 235), outline=(32, 43, 56, 20))
        for i, c in enumerate(((240, 120, 43), (201, 213, 226), (201, 213, 226))):
            d.ellipse((72 * u + i * 30 * u, 95 * u, 90 * u + i * 30 * u, 113 * u), fill=c + (255,))
        d.text((W / 2, 105 * u), "Nutrition Hub · reel edit", font=f(30), fill=(32, 43, 56, 255), anchor="mm")
        x0, y0, x1, y1 = self.rect
        px0 = x1 + 34 * u
        d.rounded_rectangle((px0, y0, W - 40 * u, y0 + 520 * u), int(26 * u), fill=(255, 255, 255, 240), outline=(32, 43, 56, 20))
        d.text((px0 + 28 * u, y0 + 30 * u), "CHECKLIST", font=f(22), fill=(230, 109, 42, 255))
        for i, item in enumerate(("Grade", "Captions", "B-roll", "Sound", "Export")):
            yy = y0 + (92 + i * 80) * u
            done = i < 4
            d.ellipse((px0 + 28 * u, yy, px0 + 62 * u, yy + 34 * u), fill=(240, 120, 43, 255) if done else (234, 240, 246, 255))
            if done:
                d.line((px0 + 37 * u, yy + 17 * u, px0 + 44 * u, yy + 25 * u, px0 + 55 * u, yy + 10 * u), fill=(255, 255, 255, 255), width=int(4 * u))
            d.text((px0 + 80 * u, yy + 17 * u), item, font=f(28), fill=(32, 43, 56, 255) if done else (89, 104, 121, 255), anchor="lm")
        ty0, ty1 = 0.71 * H, 0.93 * H
        d.rounded_rectangle((40 * u, ty0, W - 40 * u, ty1), int(26 * u), fill=(255, 255, 255, 240), outline=(32, 43, 56, 20))
        lanes = [(ty0 + 40 * u, [(0.0, 0.22, (234, 240, 246)), (0.24, 0.52, (201, 213, 226)), (0.54, 0.80, (234, 240, 246)), (0.82, 1.0, (201, 213, 226))]),
                 (ty0 + 110 * u, [(0.10, 0.30, (240, 120, 43)), (0.58, 0.74, (240, 120, 43))])]
        lx0, lx1 = 72 * u, W - 72 * u
        for y, clips in lanes:
            for a_, b_, c in clips:
                d.rounded_rectangle((lx0 + (lx1 - lx0) * a_, y, lx0 + (lx1 - lx0) * b_ - 6 * u, y + 52 * u), int(10 * u), fill=c + (255,))
        # the real audio waveform of the take
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-ac", "1", "-ar", "8000", "-f", "f32le", "-"], capture_output=True).stdout
        aud = np.frombuffer(raw, np.float32)
        wy = ty0 + 210 * u
        if len(aud):
            n = int((lx1 - lx0) / (6 * u))
            chunks = np.array_split(np.abs(aud), n)
            lev = np.array([c.max() if len(c) else 0 for c in chunks])
            lev = lev / max(lev.max(), 1e-6)
            for i, v in enumerate(lev):
                x = lx0 + i * 6 * u
                hh = max(2 * u, v * 44 * u)
                d.rounded_rectangle((x, wy - hh, x + 3.5 * u, wy + hh), int(2 * u), fill=(89, 104, 121, 200))
        self.lane_x = (lx0, lx1, ty0 + 20 * u, ty1 - 20 * u)
        return np.asarray(im).astype(np.float32) / 255

    def __call__(self, f, matte, face, t, **_):
        a, W, H = self.a, self.W, self.H
        k = fx.envelope(t, a.s, a.e)
        if k <= 0:
            return f
        tx0, ty0, tx1, ty1 = self.rect
        x0, y0 = tx0 * k, ty0 * k
        x1, y1 = W + (tx1 - W) * k, H + (ty1 - H) * k
        ch = self.chrome
        out = f * (1 - k) + ch[..., :3] * k if k < 1 else ch[..., :3].copy()
        lx0, lx1, ly0, ly1 = self.lane_x                                 # orange playhead moving along the timeline
        ph = lx0 + (lx1 - lx0) * min(1, max(0, (t - a.s) / max(a.e - a.s, 0.1)))
        out[int(ly0):int(ly1), int(ph):int(ph + 3 * W / 1080)] = out[int(ly0):int(ly1), int(ph):int(ph + 3 * W / 1080)] * (1 - k) + fx.ORANGE * k
        w, h = int(x1 - x0), int(y1 - y0)
        if w > 4 and h > 4:
            small = cv2.resize(f, (w, h), interpolation=cv2.INTER_AREA)
            rad = 28 * W / 1080 * k
            m = fx.rounded_mask(w, h, 0, 0, w - 1, h - 1, rad)[..., None]
            plate = fx.rounded_mask(W, H, x0 - 6 * k, y0 - 6 * k, x1 + 6 * k, y1 + 6 * k, rad + 6 * k)[..., None]
            out = out * (1 - plate) + fx.WHITE * plate
            region = out[int(y0):int(y0) + h, int(x0):int(x0) + w]
            hh, ww = region.shape[:2]
            out[int(y0):int(y0) + hh, int(x0):int(x0) + ww] = region * (1 - m[:hh, :ww]) + small[:hh, :ww] * m[:hh, :ww]
        return out


class Scatter:
    def __init__(self, a, W, H, fh_px):
        words = [w.strip() for w in (a.words or "").split(",") if w.strip()]
        if len(words) != 2 or any(len(w) > 10 for w in words):
            sys.exit("scatter needs --words with two short words: the first goes behind the head, the second in front, e.g. --words \"Label,first\"")
        rng = np.random.default_rng(7)
        self.a, self.W, self.H = a, W, H
        self.layers = []
        for li, (word, px, color) in enumerate(((words[0], 1.7 * fh_px, fx.WHITE), (words[1], 1.25 * fh_px, fx.ORANGE))):
            from PIL import ImageFont
            font = ImageFont.truetype(str(BEBAS), int(px))
            letters = [text_sprite(ch, px, color, BEBAS, shadow=0.3) for ch in word.upper()]
            widths = [font.getlength(ch) * 1.04 for ch in word.upper()]      # the font's own advance, slightly open
            self.layers.append({"letters": letters, "widths": widths,
                                "scatter": [(rng.uniform(-0.5, 0.5) * W, rng.uniform(-0.25, 0.25) * H, rng.uniform(0.4, 1.9), rng.uniform(-35, 35))
                                            for _ in letters], "behind": li == 0})

    def __call__(self, f, matte, face, t, **_):
        a, W, H = self.a, self.W, self.H
        if not a.s <= t <= a.e:
            return f
        pin = fx.ease_out((t - a.s) / 0.6)
        pout = fx.ease_in((t - (a.e - 0.45)) / 0.45) if t > a.e - 0.45 else 0.0
        spread = (1 - pin) + pout
        fh = face["fh"] * H
        cx = face["cx"] * W
        centres = [(cx, (face["top"] + face["chin"]) / 2 * H - 0.15 * fh), (cx, face["chin"] * H + 1.3 * fh)]
        back = f.copy()
        out_front = []
        for layer, (lx, ly) in zip(self.layers, centres):
            total = sum(layer["widths"])
            x = lx - total / 2
            for spr, w, (dx, dy, depth, rot) in zip(layer["letters"], layer["widths"], layer["scatter"]):
                sc = 1 + (depth - 1) * spread
                s = rotate(spr, rot * spread, max(0.2, sc))
                s = blur(s, 10 * abs(depth - 1) * spread)
                s = s.copy(); s[..., 3:] *= min(1.0, pin * 1.5) * (1 - pout)
                px, py = x + w / 2 + dx * spread, ly + dy * spread
                x = x + w
                tgt = back if layer["behind"] else None
                if tgt is not None:
                    fx.over(back, s, px - s.shape[1] / 2, py - s.shape[0] / 2)
                else:
                    out_front.append((s, px, py))
        m = matte[..., None]
        out = f * m + back * (1 - m)                                      # the first word sits behind the speaker
        for s, px, py in out_front:
            fx.over(out, s, px - s.shape[1] / 2, py - s.shape[0] / 2)
        return out


class BgSwap:
    def __init__(self, a, W, H, fh_px, info):
        self.a, self.W, self.H = a, W, H
        self.kind = "stage" if a.bg in (None, "stage") else "blur" if a.bg == "blur" else "file"
        self.img = self.reader = None
        if self.kind == "file":
            p = Path(a.bg)
            if not p.is_file():
                sys.exit(f"Background not found: {a.bg}")
            if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                im = cv2.cvtColor(cv2.imread(str(p), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
                self.img = self._cover(im.astype(np.float32) / 255)
            else:
                bi = fx.probe(p)
                self.reader = fx.frames(p, {**bi, "w": W, "h": H, "rate": info["rate"], "fps": info["fps"]}, 0, bi["dur"])
        g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        self.stage = np.repeat(fx.WHITE * (1 - g) + fx.ICE * g, W, 1)

    def _cover(self, im):
        h, w = im.shape[:2]
        s = max(self.W / w, self.H / h)
        im = cv2.resize(im, (int(w * s + 1), int(h * s + 1)), interpolation=cv2.INTER_AREA)
        y, x = (im.shape[0] - self.H) // 2, (im.shape[1] - self.W) // 2
        return im[y:y + self.H, x:x + self.W]

    def __call__(self, f, matte, face, t, **_):
        a = self.a
        k = fx.envelope(t, a.s, a.e)
        if k <= 0:
            return f
        if self.kind == "stage":
            bg = self.stage
        elif self.kind == "blur":
            small = cv2.resize(f, (self.W // 8, self.H // 8), interpolation=cv2.INTER_AREA)
            bg = cv2.resize(cv2.GaussianBlur(small, (0, 0), 5), (self.W, self.H)) * 0.55 + 0.45 * fx.ICE
        elif self.img is not None:
            bg = self.img
        else:
            try:
                _, _, b = next(self.reader)
                self.last = b.astype(np.float32) / 255
            except StopIteration:
                pass
            bg = getattr(self, "last", self.stage)
        m = matte[..., None]
        swapped = f * m + bg * (1 - m)
        return f * (1 - k) + swapped * k


EFFECTS = {"sticky": Sticky, "wipe": Wipe, "pullback": Pullback, "scatter": Scatter, "bgswap": BgSwap}
NEEDS_INFO = {"wipe", "pullback", "bgswap"}
