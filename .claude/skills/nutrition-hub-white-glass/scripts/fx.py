#!/usr/bin/env python3
"""
Person-aware effects for talking-head footage (SKILL.md §4 G–H). Both follow the speaker's
face (person_track.py) and use a person matte (person_matte.py) so things pass behind them.

ORBIT (R5): ceramic spheres, or word chips, burst out from behind the speaker's head onto a ring
and turn slowly around it; then they fold back behind the head.
    python3 fx.py orbit in.mp4 out.mp4 --at 3.0-6.0                       # 8 spheres, 1 orange
    python3 fx.py orbit in.mp4 out.mp4 --at 3-6 --words "Whey,Creatine,Omega-3,Multivitamin"
    python3 fx.py orbit in.mp4 out.mp4 --at 3-6 --tilt 70                 # a 3D ring: the back half passes behind
  --spheres 8 --accent 1   count and how many are signal orange    --radius 1.8  (face heights)
  --speed 30 (degrees/s)   --tilt 0 = a flat ring around the head (R5); 50-75 = a tilted ring
  --matte head (default: a head-and-shoulders shape from the face track) | wall | FILE

FRAME ESCAPE: the picture shrinks into a porcelain frame on the White Glass stage while the
speaker's head and hands stay outside it, as if stepping out of the frame.
    python3 fx.py escape in.mp4 out.mp4 --at 2.0-5.0 --matte wall          # plain wall behind the speaker
    python3 fx.py escape in.mp4 out.mp4 --at 2-5 --matte person_matte.mp4  # matte from CapCut or Runway
  --stage ice (white to ice-mist) | blur (the room, blurred and washed light)
  --top 0.35   where the frame's top edge sits, in face heights below the chin

MORE (the R7 pack, fx_pack.py): sticky, wipe (before + after), pullback, scatter (depth scatter), bgswap
(green screen without a green screen). See fx_pack.py for each one's options and rules.

All follow the head at the full frame rate (motion_track.py), so nods and leans are followed; with the
head matte, detected hands pass in front of orbit spheres (--no-hands to switch off).
Timing: 0.6 s in (ease-out, no overshoot), 0.45 s out (ease-in), held in between (SKILL.md §5).
Each run also writes <out>.sfx.json (a soft whoosh on the move) for sfx.py --cues.
Audio is copied unchanged. Needs numpy, OpenCV 4.10, Pillow and ffmpeg.
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
    sys.exit("fx.py needs OpenCV: pip install opencv-python-headless==4.10.0.84")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

WHITE = np.array([1.0, 1.0, 1.0], np.float32)
ICE = np.array([0xEA, 0xF0, 0xF6], np.float32) / 255
INK = np.array([0x20, 0x2B, 0x38], np.float32) / 255
ORANGE = np.array([0xF0, 0x78, 0x2B], np.float32) / 255
IN_S, OUT_S = 0.6, 0.45


# ---------------------------------------------------------------- video io
def probe(path):
    if not Path(path).is_file():
        sys.exit(f"File not found: {path}")
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    try:
        info = json.loads(r.stdout)
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        num, den = (float(x) for x in v["r_frame_rate"].split("/"))
        dur = float(info["format"]["duration"])
    except (json.JSONDecodeError, StopIteration, KeyError, ValueError, ZeroDivisionError):
        sys.exit(f"Could not read {path}. Is it a video file?")
    fps = num / den
    return {"w": int(v["width"]) // 2 * 2, "h": int(v["height"]) // 2 * 2, "fps": fps, "rate": v["r_frame_rate"],
            "dur": dur, "frames": int(round(dur * fps)), "audio": any(s["codec_type"] == "audio" for s in info["streams"])}


def frames(video, info, s=0.0, e=None):
    """Yield (frame index, time, RGB uint8 frame) from s to e."""
    W, H = info["w"], info["h"]
    e = info["dur"] if e is None else e
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", str(video),
                          "-vf", f"scale={W}:{H},fps={info['rate']}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)   # a reader stopped early would print "broken pipe"
    k0, n = int(round(s * info["fps"])), W * H * 3
    k = 0
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield k0 + k, (k0 + k) / info["fps"], np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        k += 1
    p.wait()


class Writer:
    def __init__(self, out, info, audio_from):
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{info['w']}x{info['h']}",
               "-r", info["rate"], "-i", "-"]
        if audio_from and info["audio"]:
            cmd += ["-i", str(audio_from), "-map", "0:v", "-map", "1:a", "-c:a", "copy"]
        cmd += ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    def write(self, rgb):
        self.p.stdin.write(np.ascontiguousarray(rgb, np.uint8).tobytes())

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.p.stdin.close()
        err = self.p.stderr.read().decode(errors="replace")
        if self.p.wait():
            sys.exit("ffmpeg failed:\n" + err[-2000:])


# ---------------------------------------------------------------- easing and drawing
def ease_out(x):   # close to cubic-bezier(.22,1,.36,1): fast start, settles exactly at 1
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 4


def ease_in(x):
    x = min(max(x, 0.0), 1.0)
    return x ** 3


def envelope(t, s, e):
    """0 → 1 over IN_S after s, 1 → 0 over OUT_S before e."""
    if t < s or t > e:
        return 0.0
    return min(ease_out((t - s) / IN_S), 1 - ease_in(1 - (e - t) / OUT_S) if e - t < OUT_S else 1.0)


def over(dst, rgba, x, y):
    """Alpha-composite an RGBA float sprite onto dst (float RGB) with its top-left at (x, y)."""
    h, w = rgba.shape[:2]
    H, W = dst.shape[:2]
    x0, y0, x1, y1 = max(int(x), 0), max(int(y), 0), min(int(x) + w, W), min(int(y) + h, H)
    if x0 >= x1 or y0 >= y1:
        return
    s = rgba[y0 - int(y):y1 - int(y), x0 - int(x):x1 - int(x)]
    a = s[..., 3:4]
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + s[..., :3] * a


def sphere(d, accent=False):
    """A shaded ceramic sphere (or signal orange), soft studio light, with a contact shadow, RGBA."""
    ss = 3
    D = int(d * ss)
    pad = int(D * 0.35)
    size = D + 2 * pad
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    c = size / 2
    nx, ny = (xx - c) / (D / 2), (yy - c) / (D / 2)
    r2 = nx * nx + ny * ny
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    L = np.array([-0.45, -0.62, 0.64]); L /= np.linalg.norm(L)
    lam = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    Hh = L + np.array([0, 0, 1.0]); Hh /= np.linalg.norm(Hh)
    spec = np.clip(nx * Hh[0] + ny * Hh[1] + nz * Hh[2], 0, 1) ** 60
    rim = (1 - nz) ** 3
    base = ORANGE if accent else np.array([0.955, 0.965, 0.975], np.float32)
    col = base * (0.62 + 0.42 * lam[..., None])
    col = col * (1 - 0.35 * rim[..., None]) + ICE * 0.35 * rim[..., None]          # ice-mist studio reflection
    col = col + (0.75 if not accent else 0.55) * spec[..., None]
    col = col * (1 - 0.06 * np.clip(ny, 0, 1)[..., None])                         # slightly darker underneath
    alpha = np.clip((1 - np.sqrt(r2)) * D / 2, 0, 1)                               # 1 px anti-aliased edge
    sh = np.exp(-(((xx - c) / (0.42 * D)) ** 2 + ((yy - c - 0.55 * D) / (0.12 * D)) ** 2))   # contact shadow
    sh_a = 0.22 * sh * (1 - alpha)
    rgba = np.zeros((size, size, 4), np.float32)
    rgba[..., :3] = np.clip(col, 0, 1) * alpha[..., None] + INK * (sh_a / np.maximum(sh_a + alpha, 1e-6))[..., None] * (1 - alpha[..., None])
    rgba[..., 3] = np.clip(alpha + sh_a, 0, 1)
    rgba[..., :3] = np.where(rgba[..., 3:4] > 0, rgba[..., :3], 0)
    small = cv2.resize(rgba, (size // ss, size // ss), interpolation=cv2.INTER_AREA)
    return small


def find_font():
    for p in ("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", "/usr/share/fonts/truetype/inter/Inter-SemiBold.ttf"):
        if Path(p).is_file():
            return p
    out = subprocess.run(["fc-match", "-f", "%{file}", "Inter:semibold"], capture_output=True, text=True).stdout.strip()
    if "inter" not in out.lower():
        sys.exit("Word chips need the Inter font (SKILL.md §3). Install it, or use spheres.")
    return out


def chip(word, height):
    """A frosted glass pill with an ink word, RGBA."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    ss = 2
    hpx = int(height * ss)
    font = ImageFont.truetype(find_font(), int(hpx * 0.46))
    tw = int(font.getlength(word))
    w = tw + int(hpx * 1.1)
    pad = int(hpx * 0.4)
    im = Image.new("RGBA", (w + 2 * pad, hpx + 2 * pad), (0, 0, 0, 0))
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((pad, pad + hpx * 0.12, pad + w, pad + hpx + hpx * 0.12), hpx // 2, fill=(32, 43, 56, 50))
    im = Image.alpha_composite(im, shadow.filter(ImageFilter.GaussianBlur(hpx * 0.16)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((pad, pad, pad + w, pad + hpx), hpx // 2, fill=(255, 255, 255, 238), outline=(32, 43, 56, 26), width=ss)
    d.text((pad + w / 2, pad + hpx / 2), word, font=font, fill=(32, 43, 56, 255), anchor="mm")
    im = im.resize((im.width // ss, im.height // ss), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    return a


# ---------------------------------------------------------------- effects
def orbit_frame(out, matte, face, t, a, sprites, W, H):
    k = envelope(t, a.s, a.e)
    if k <= 0:
        return out
    fh = face["fh"] * H
    cx = face["cx"] * W
    # flat ring: around the face (the matte hides anything crossing it); tilted ring: centred at the chin,
    # so its front half passes over the chest and its back half behind the head, never across the face
    cy = (face["top"] + face["chin"]) / 2 * H if not a.tilt else face["chin"] * H + 0.25 * fh
    half = max(sp.shape[1] for sp in sprites) / 2
    r_fit = min(cx, W - cx) - half - 72 * W / 1080              # keep every item inside the side safe margins
    r = min(a.radius * fh, 0.44 * W, max(r_fit, 1.0 * fh)) * k  # burst out from behind the head, fold back in
    tilt = np.radians(a.tilt)
    back = out.copy()
    front_items = []
    n = len(sprites)
    ring = np.zeros((H, W), np.float32)
    ring_back = np.zeros((H, W), np.float32)
    sweep = 360 * ease_out((t - a.s) / 0.7)
    ry = r * np.cos(tilt)
    if not a.no_ring and r > 4:
        th = max(2, int(round(W / 420)))
        if a.tilt:
            cv2.ellipse(ring_back, (int(cx), int(cy)), (int(r), int(ry)), 0, 180, 180 + min(sweep, 180), 1.0, th, cv2.LINE_AA)
            if sweep > 180:
                cv2.ellipse(ring, (int(cx), int(cy)), (int(r), int(ry)), 0, 0, sweep - 180, 1.0, th, cv2.LINE_AA)
        else:
            cv2.ellipse(ring_back, (int(cx), int(cy)), (int(r), int(r)), 0, -90, -90 + sweep, 1.0, th, cv2.LINE_AA)
    ring_alpha = 0.55 * k
    back = back * (1 - ring_alpha * ring_back[..., None]) + WHITE * ring_alpha * ring_back[..., None]
    order = []
    for i, spr in enumerate(sprites):
        th_i = 2 * np.pi * i / n + np.radians(a.speed) * (t - a.s)
        z = np.sin(th_i) * np.sin(tilt)
        x = cx + r * np.cos(th_i)
        y = cy + r * np.sin(th_i) * np.cos(tilt)
        scale = (1 + 0.18 * z) * (0.6 + 0.4 * k)
        order.append((z, x, y, scale, spr))
    for z, x, y, scale, spr in sorted(order, key=lambda o: o[0]):
        s = cv2.resize(spr, (max(2, int(spr.shape[1] * scale)), max(2, int(spr.shape[0] * scale))), interpolation=cv2.INTER_AREA)
        s = s.copy(); s[..., 3] *= min(1.0, k * 1.4)
        if a.tilt and z > 0:
            front_items.append((s, x, y))
        else:
            over(back, s, x - s.shape[1] / 2, y - s.shape[0] / 2)
    m = matte[..., None]
    out = out * m + back * (1 - m)                             # the speaker stays in front of the back half
    out = out * (1 - ring_alpha * ring[..., None]) + WHITE * ring_alpha * ring[..., None]
    for s, x, y in front_items:
        over(out, s, x - s.shape[1] / 2, y - s.shape[0] / 2)
    return out


def rounded_mask(W, H, x0, y0, x1, y1, rad):
    m = np.zeros((H, W), np.uint8)
    rad = int(max(0, min(rad, (x1 - x0) / 2, (y1 - y0) / 2)))
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    cv2.rectangle(m, (x0 + rad, y0), (x1 - rad, y1), 255, -1)
    cv2.rectangle(m, (x0, y0 + rad), (x1, y1 - rad), 255, -1)
    for cxy in ((x0 + rad, y0 + rad), (x1 - rad, y0 + rad), (x0 + rad, y1 - rad), (x1 - rad, y1 - rad)):
        cv2.circle(m, cxy, rad, 255, -1, cv2.LINE_AA)
    return m.astype(np.float32) / 255


def escape_frame(frame_f, matte, face, t, a, W, H, stage_cache):
    k = envelope(t, a.s, a.e)
    if k <= 0:
        return frame_f
    fh = face["fh"] * H
    top_t = min(face["chin"] * H + a.top * fh, 0.62 * H)
    tgt = (0.08 * W, top_t, 0.92 * W, 0.86 * H)
    x0, y0, x1, y1 = (full + (g - full) * k for g, full in zip(tgt, (0, 0, W, H)))   # full frame → the card
    rad = 44 * W / 1080 * k
    border = 16 * W / 1080 * k
    if a.stage == "blur":
        small = cv2.resize(frame_f, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        stage = cv2.resize(cv2.GaussianBlur(small, (0, 0), 6), (W, H)) * 0.35 + 0.65 * ICE
    else:
        if "ice" not in stage_cache:
            g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
            stage_cache["ice"] = WHITE * (1 - g) + ICE * g
        stage = stage_cache["ice"]
    out = stage.copy()
    sh = rounded_mask(W, H, x0, y0 + 22 * k, x1, y1 + 22 * k, rad + border)
    sh = cv2.GaussianBlur(sh, (0, 0), 28 * W / 1080)
    out = out * (1 - 0.22 * k * sh[..., None]) + INK * 0.22 * k * sh[..., None]
    plate = rounded_mask(W, H, x0 - border, y0 - border, x1 + border, y1 + border, rad + border)
    out = out * (1 - plate[..., None]) + WHITE * plate[..., None]
    inside = rounded_mask(W, H, x0, y0, x1, y1, rad)
    out = out * (1 - inside[..., None]) + frame_f * inside[..., None]
    yy = np.arange(H, dtype=np.float32)[:, None]
    xx = np.arange(W, dtype=np.float32)[None, :]
    allowed = ((yy < y0 + 0.02 * H) & (xx > x0 - 0.05 * W) & (xx < x1 + 0.05 * W)).astype(np.float32)
    pop = matte * (1 - inside) * allowed
    pop = cv2.GaussianBlur(pop, (3, 3), 0)[..., None]
    return out * (1 - pop) + frame_f * pop


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    import fx_pack
    ap.add_argument("effect", choices=["orbit", "escape", *fx_pack.EFFECTS])
    ap.add_argument("video"); ap.add_argument("out")
    ap.add_argument("--at", required=True, metavar="START-END")
    ap.add_argument("--matte", default=None, help="head | wall | a matte video (white = person)")
    ap.add_argument("--spheres", type=int, default=8); ap.add_argument("--accent", type=int, default=1)
    ap.add_argument("--words", default=None, help="comma-separated words for glass chips instead of spheres")
    ap.add_argument("--radius", type=float, default=1.8); ap.add_argument("--speed", type=float, default=30)
    ap.add_argument("--tilt", type=float, default=0.0); ap.add_argument("--no-ring", action="store_true")
    ap.add_argument("--no-hands", action="store_true", help="orbit: don't let detected hands pass in front")
    ap.add_argument("--stage", choices=["ice", "blur"], default="ice"); ap.add_argument("--top", type=float, default=0.35)
    ap.add_argument("--text", help="sticky: the sticker's words"); ap.add_argument("--badge", help="sticky: a short number or tag in an orange badge")
    ap.add_argument("--anchor", choices=["chest", "head", "hand"], default="chest", help="sticky: what it sticks to")
    ap.add_argument("--mode", choices=["sweep", "line"], default="sweep",
                    help="wipe: sweep (one light bar) or line (R18's attention style: a moving divider with a glass handle)")
    ap.add_argument("--before", help="wipe: the same take before the edit"); ap.add_argument("--bg", help="bgswap: a clip, an image, stage or blur")
    a = ap.parse_args()
    try:
        a.s, a.e = (float(x) for x in a.at.split("-"))
    except ValueError:
        sys.exit(f"--at {a.at!r}: write it as START-END in seconds, e.g. 3.0-6.0")
    info = probe(a.video)
    if not 0 <= a.s < a.e <= info["dur"] + 0.05:
        sys.exit(f"--at {a.at}: must sit inside the video (0–{info['dur']:.2f} s), start before end.")
    if a.e - a.s < IN_S + OUT_S + 0.5:
        sys.exit(f"--at {a.at}: give the effect at least {IN_S + OUT_S + 0.5:.2f} s (in, hold, out).")
    if not 0 <= a.tilt <= 85:
        sys.exit("--tilt must be 0 to 85 degrees.")
    matte_src = a.matte or ("head" if a.effect in ("orbit", "scatter") else None)
    if a.effect in ("escape", "bgswap") and matte_src in (None, "head"):
        sys.exit(f"The {a.effect} needs a real outline of the speaker: --matte wall (plain wall behind them) "
                 "or --matte FILE (a cut-out or matte video from ghost-editor, CapCut or Runway).")
    needs_matte = a.effect in ("orbit", "escape", "scatter", "bgswap")

    import person_matte as pm
    W, H = info["w"], info["h"]
    faces = pm.FaceSeries(a.video)
    key = pm.WallKey(W, H) if matte_src == "wall" else None
    fm = pm.FileMatte(matte_src, W, H, info["frames"]) if matte_src not in (None, "head", "wall") else None

    sprites = []
    if a.effect == "orbit":
        fh_px = float(np.median(faces.v["fh"])) * H
        if a.words:
            words = [w.strip() for w in a.words.split(",") if w.strip()]
            if not 2 <= len(words) <= 6:
                sys.exit("--words: give 2 to 6 words (one short word or two per chip).")
            sprites = [chip(w, 0.46 * fh_px) for w in words]
        else:
            if not 3 <= a.spheres <= 12:
                sys.exit("--spheres: 3 to 12.")
            d = 0.42 * fh_px
            white, orange = sphere(d), sphere(d, accent=True)
            step = max(1, a.spheres // max(a.accent, 1)) if a.accent else 0
            sprites = [orange if a.accent and i % step == step // 2 and i // step < a.accent else white for i in range(a.spheres)]

    import motion_track
    tracker = motion_track.MotionTracker(info["fps"])     # head at the full frame rate, and the hands
    pack = None
    if a.effect in fx_pack.EFFECTS:
        fh_px = float(np.median(faces.v["fh"])) * H
        cls = fx_pack.EFFECTS[a.effect]
        pack = cls(a, W, H, fh_px, info) if a.effect in fx_pack.NEEDS_INFO else cls(a, W, H, fh_px)
    stage_cache, wall_q, tracked = {}, None, 0
    with Writer(a.out, info, a.video) as wr:
        for k, t, frame in frames(a.video, info):
            head, hands, hand_mask = tracker.update(frame)
            if not a.s <= t <= a.e:
                wr.write(frame); continue
            face = head or faces.at(t)
            tracked += head is not None
            if key is not None and key.bg is None:
                wall_q = key.fit(frame, face)
            matte = (key(frame, face) if key else fm(k) if fm else pm.head_matte(face, W, H)) if needs_matte else None
            if a.effect in ("orbit", "scatter") and matte_src == "head" and hand_mask is not None and not a.no_hands:
                hm = cv2.GaussianBlur(cv2.resize(hand_mask, (W, H), interpolation=cv2.INTER_LINEAR), (0, 0), 3 * W / 1080)
                matte = np.maximum(matte, hm)                   # hands pass in front of the spheres
            f = frame.astype(np.float32) / 255
            if pack is not None:
                res = pack(f, matte, face, t, hands=hands)
            elif a.effect == "orbit":
                res = orbit_frame(f, matte, face, t, a, sprites, W, H)
            else:
                res = escape_frame(f, matte, face, t, a, W, H, stage_cache)
            wr.write(np.clip(res * 255 + 0.5, 0, 255).astype(np.uint8))
    if wall_q is not None and wall_q > 12:
        print(f"note: the wall isn't very plain (ΔE {wall_q:.0f}); check the outline, or use a matte file")
    n_win = max(1, int((a.e - a.s) * info["fps"]))
    if tracked < 0.8 * n_win:
        print(f"note: the head was tracked in {tracked / n_win:.0%} of the effect's frames; the rest use the slower face track")
    sound = {"sticky": ("pop", 0.12, 0), "wipe": ("swish", 0.8, -2)}.get(a.effect, ("whoosh", 0.25, -3))
    cues = [{"t": round(a.s + sound[1], 3), "sfx": sound[0], "gain": sound[2], "what": f"{a.effect} in"}]
    Path(str(Path(a.out).with_suffix("")) + ".sfx.json").write_text(json.dumps(cues, indent=2))
    print(f"wrote {a.out} ({a.effect} {a.s:.2f}-{a.e:.2f} s, matte: {matte_src}); SFX cue → {Path(a.out).with_suffix('')}.sfx.json")


if __name__ == "__main__":
    main()
