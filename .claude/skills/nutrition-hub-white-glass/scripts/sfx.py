#!/usr/bin/env python3
"""
White Glass sound effects: an original kit synthesised in code (no samples, no licence needed)
and a mixer that places them on a video, under the voice (SKILL.md §5 Sound).

    # the cue sheet render.cjs writes next to each render (slams, pills, cards, logo)
    python3 sfx.py final.mp4 out.mp4 --cues hook.sfx.json
    python3 sfx.py final.mp4 out.mp4 --cues callout.sfx.json@1 --cues endcard.sfx.json@11.6   # FILE@START in this video

    # b-roll: a swish into each dip to white, a soft whoosh into each dissolve (plain cuts stay silent)
    python3 sfx.py final.mp4 out.mp4 --broll broll_plan.json

    # by hand: TIME=SOUND, optionally @GAIN in dB
    python3 sfx.py final.mp4 out.mp4 --at 4.9=thud --at 6.5=tick --at 8.2=glass@-2

    python3 sfx.py --kit sfx_kit/          # export the kit as WAV files + kit.json (CapCut, Premiere...)
    python3 sfx.py --preview kit.wav       # every sound once, to listen to

The kit (each sound lands its "hit" exactly on the cue time):
  thud    a slam word lands (low, soft impact)             6 dB under the voice
  riser   leads into a slam (ends on the cue)              14 dB under
  whoosh  a dissolve or a scene change (soft air)          10 dB under
  swish   a dip to white (airy, with a glass sheen)        10 dB under
  pop     a glass card or callout appears                  12 dB under
  tick    a check pill, badge or list item (glass tick;    14 dB under
          ticks in a row step up in pitch)
  glass   the logo or end card (glass bell shimmer)        11 dB under

Levels follow the voice: each sound's loudest 400 ms is set relative to the voice's integrated
loudness (BS.1770 K-weighted). With a voice, the mix is mastered to -14 LUFS, true peak -2 (headroom so
the AAC encode stays under qa.py's -1.5 limit)
(skip with --no-master). With no voice, sounds sit where they would against a mastered voice
(-14 LUFS) and nothing is mastered. Run it LAST, on the finished video, after the end card.
The video stream is copied unchanged. Needs ffmpeg and numpy.
"""
import argparse
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000
MIN_GAP = 0.15        # two cues closer than this: the later one is dropped
MAX_RATE = 0.5        # more than one cue every 2 s on average gets a warning
SILENT_REF = -14.0    # no voice: place sounds where they would sit against a mastered voice


# ---------------------------------------------------------------- synthesis helpers
def tvec(dur):
    return np.arange(int(round(dur * SR))) / SR


def fades(x, fin=0.0015, fout=0.012):
    n_in, n_out = max(1, int(fin * SR)), max(1, int(fout * SR))
    x = x.copy()
    x[:n_in] *= np.linspace(0, 1, n_in)[:, None] if x.ndim == 2 else np.linspace(0, 1, n_in)
    x[-n_out:] *= np.linspace(1, 0, n_out)[:, None] if x.ndim == 2 else np.linspace(1, 0, n_out)
    return x


def shaped_noise(dur, fc, sigma_oct, seed):
    """Noise whose spectrum is a band centred on fc(t) (Hz, per frame), sigma in octaves. STFT overlap-add."""
    rng = np.random.default_rng(seed)
    n, N, hop = int(round(dur * SR)), 2048, 512
    x = rng.standard_normal(n + N)
    win = np.hanning(N)
    freqs = np.fft.rfftfreq(N, 1 / SR)
    lf = np.log2(np.maximum(freqs, 20.0))
    out, norm = np.zeros(n + N), np.zeros(n + N)
    for start in range(0, n, hop):
        c = fc(min((start + N / 2) / SR, dur))
        band = np.exp(-0.5 * ((lf - np.log2(c)) / sigma_oct) ** 2)
        seg = np.fft.irfft(np.fft.rfft(x[start:start + N] * win) * band, N) * win
        out[start:start + N] += seg
        norm[start:start + N] += win ** 2
    return out[:n] / np.maximum(norm[:n], 1e-3)


def pan(mono, p):
    """p in -1..1 (scalar or per sample), equal-power."""
    a = (np.asarray(p) + 1) * np.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)], axis=1)


def sweep(t, f0, f1, f2, hit):
    """Exponential glide f0 -> f1 at the hit, then toward f2."""
    def fc(s):
        if s <= hit:
            return f0 * (f1 / f0) ** (s / hit)
        return f1 * (f2 / f1) ** min(1.0, (s - hit) / max(t - hit, 1e-3))
    return fc


def air(dur, hit, f0, f1, f2, sigma, seed, rise=2.2, tail=0.11, width=0.35):
    t = tvec(dur)
    env = np.where(t <= hit, (t / hit) ** rise, np.exp(-(t - hit) / tail))
    left = shaped_noise(dur, sweep(dur, f0, f1, f2, hit), sigma, seed) * env
    right = shaped_noise(dur, sweep(dur, f0, f1, f2, hit), sigma, seed + 1) * env
    p = np.linspace(-width, width, len(t))
    a = (p + 1) * np.pi / 4
    return np.stack([left * np.cos(a) * 1.2, right * np.sin(a) * 1.2], axis=1)


# ---------------------------------------------------------------- the kit
def s_whoosh(v=0):
    return fades(air(0.62, 0.32, 320, 2400, 900, 0.55, 11))


def s_swish(v=0):
    dur, hit = 0.7, 0.30
    x = air(dur, hit, 1100, 6500, 3200, 0.7, 21, rise=2.6, tail=0.09)
    t = tvec(dur)
    after = np.clip(t - hit, 0, None)
    ramp = np.clip(after / 0.006, 0, 1) * (t >= hit)          # 6 ms fade-in: a hard start would click
    sheen = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-after / d) * ramp
                for f, a, d in ((3520, 0.10, 0.22), (5274, 0.07, 0.16), (7040, 0.05, 0.11)))
    return fades(x + np.stack([sheen, sheen * 0.92], axis=1))


def s_thud(v=0):
    t = tvec(0.62)
    f = 48 + 62 * np.exp(-t / 0.05)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16) * np.minimum(1, t / 0.002)
    rng = np.random.default_rng(31)
    click = np.convolve(rng.standard_normal(len(t)), np.ones(14) / 14, "same") * np.exp(-t / 0.006) * 2.2
    m = np.tanh(1.6 * (body + click)) / np.tanh(1.6)
    return fades(pan(m, 0.0), fin=0.0005)


def s_riser(v=0):
    dur = 1.0
    t = tvec(dur)
    env = (t / dur) ** 3
    noise = shaped_noise(dur, lambda s: 300 * (6000 / 300) ** (s / dur), 0.6, 41) * env
    tone = np.sin(2 * np.pi * np.cumsum(220 * 4 ** (t / dur)) / SR) * env * 0.18
    return fades(pan(noise + tone, np.linspace(-0.2, 0.2, len(t))), fout=0.015)


def s_tick(v=0):
    k = 2 ** ((v % 4) / 12 * 2)          # a run of ticks steps up a whole tone each
    t = tvec(0.16)
    m = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t / d)
            for f, a, d in ((2637, 1.0, 0.028), (3951, 0.5, 0.02), (6271, 0.3, 0.012)))
    rng = np.random.default_rng(51)
    m = m + np.diff(rng.standard_normal(len(t) + 1)) * np.exp(-t / 0.0012) * 0.25
    return fades(pan(m * np.minimum(1, t / 0.0006), 0.12 * ((v % 3) - 1)), fin=0.0003)


def s_pop(v=0):
    t = tvec(0.18)
    f = 340 + 260 * np.exp(-t / 0.018)
    ph = 2 * np.pi * np.cumsum(f) / SR
    m = (np.sin(ph) + 0.15 * np.sin(2 * ph)) * np.exp(-t / 0.04) * np.minimum(1, t / 0.0025)
    return fades(pan(np.tanh(1.3 * m), 0.0), fin=0.0005)


def s_glass(v=0):
    t = tvec(1.7)
    base = 1318.5
    att = np.minimum(1, t / 0.004)
    chans = []
    for det in (-0.8, 0.8):
        m = sum(a * np.sin(2 * np.pi * (base * r + det * r) * t) * np.exp(-t / d)
                for r, a, d in ((1.0, 1.0, 1.0), (2.0, 0.35, 0.6), (2.76, 0.5, 0.5), (4.07, 0.2, 0.35), (5.4, 0.25, 0.25)))
        chans.append(m * att * (1 + 0.04 * np.sin(2 * np.pi * 6 * t)))
    sheen = shaped_noise(1.7, lambda s: 8000, 0.4, 61) * np.exp(-t / 0.05) * np.minimum(1, t / 0.01) * 0.6
    return fades(np.stack([chans[0] + sheen, chans[1] + sheen], axis=1), fout=0.05)


KIT = {   # name: (synth, hit time in the sound, dB relative to the voice, use)
    "thud": (s_thud, 0.0, -6, "a slam word lands"),
    "riser": (s_riser, 1.0, -14, "leads into a slam (ends on the cue)"),
    "whoosh": (s_whoosh, 0.32, -10, "a dissolve or a scene change"),
    "swish": (s_swish, 0.30, -10, "a dip to white"),
    "pop": (s_pop, 0.0, -12, "a glass card or callout appears"),
    "tick": (s_tick, 0.0, -14, "a check pill, badge or list item"),
    "glass": (s_glass, 0.02, -11, "the logo or end card"),
}


# ---------------------------------------------------------------- loudness (ITU-R BS.1770)
K_STAGES = (((1.53512485958697, -2.69169618940638, 1.19839281085285), (1.0, -1.69065929318241, 0.73248077421585)),
            ((1.0, -2.0, 1.0), (1.0, -1.99004745483398, 0.99007225036621)))


def k_weight(x):
    """K-weighting applied as a magnitude response in the frequency domain (power is what loudness needs)."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    z = np.exp(-2j * np.pi * f / SR)
    h = np.ones_like(z)
    for b, a in K_STAGES:
        h *= (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)
    return np.fft.irfft(np.fft.rfft(x, axis=0) * np.abs(h)[:, None], n, axis=0)


def block_loudness(x):
    y = k_weight(x)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    if len(y) < blk:
        y = np.pad(y, ((0, blk - len(y)), (0, 0)))
    ms = np.array([np.mean(np.sum(y[i:i + blk] ** 2, axis=1)) for i in range(0, len(y) - blk + 1, hop)])
    return -0.691 + 10 * np.log10(np.maximum(ms, 1e-12)), ms


def integrated(x):
    lk, ms = block_loudness(x)
    keep = lk > -70
    if not keep.any():
        return None
    rel = -0.691 + 10 * np.log10(np.mean(ms[keep])) - 10
    keep &= lk > rel
    return -0.691 + 10 * np.log10(np.mean(ms[keep])) if keep.any() else None


def momentary_max(x):
    return float(np.max(block_loudness(x)[0]))


# ---------------------------------------------------------------- io
def probe(path):
    if not Path(path).is_file():
        sys.exit(f"File not found: {path}")
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True)
    try:
        info = json.loads(r.stdout)
        dur = float(info["format"]["duration"])
    except (json.JSONDecodeError, KeyError, ValueError):
        sys.exit(f"Could not read {path}. Is it a video file?")
    kinds = [s.get("codec_type") for s in info.get("streams", [])]
    if "video" not in kinds:
        sys.exit(f"{path} has no picture; sfx.py adds sound to a video.")
    return dur, "audio" in kinds


def read_audio(path, dur, has_audio):
    n = int(round(dur * SR))
    if not has_audio:
        return np.zeros((n, 2), np.float32)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-vn", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    return np.pad(a, ((0, max(0, n - len(a))), (0, 0)))[:max(n, len(a))]


def write_wav(path, x, peak_db=-3.0):
    x = x / max(np.max(np.abs(x)), 1e-9) * 10 ** (peak_db / 20)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


# ---------------------------------------------------------------- cues
def parse_at(text):
    m = re.fullmatch(r"\s*([\d.]+)\s*=\s*([a-z]+)\s*(?:@\s*(-?[\d.]+))?\s*", text)
    if not m:
        sys.exit(f"--at {text!r}: write it as TIME=SOUND or TIME=SOUND@GAIN, e.g. 4.9=thud or 8.2=glass@-2")
    return {"t": float(m.group(1)), "sfx": m.group(2), "gain": float(m.group(3) or 0), "what": "by hand"}


def load_json(path, what):
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as e:
        sys.exit(f"Could not read the {what} {path}: {e}")
    return data.get("cuts", data) if isinstance(data, dict) else data


def broll_cues(plan):
    out, cuts = [], 0
    for c in plan:
        tr = c.get("transition", "cut")
        if tr in ("white", "flash"):
            out.append({"t": float(c["start"]), "sfx": "swish", "gain": 0, "what": f"dip to white into {Path(c['file']).name}"})
        elif tr == "soft":
            out.append({"t": float(c["start"]), "sfx": "whoosh", "gain": -3, "what": f"dissolve into {Path(c['file']).name}"})
        else:
            cuts += 1
    return out, cuts


def place(cues, dur):
    notes, kept = [], []
    for c in sorted(cues, key=lambda c: c["t"]):
        if c["sfx"] not in KIT:
            sys.exit(f"Unknown sound {c['sfx']!r}. The kit has: {', '.join(KIT)}.")
        if not 0 <= c["t"] < dur:
            notes.append(f"{c['t']:.2f} s {c['sfx']}: outside the video (0–{dur:.2f} s), skipped"); continue
        if kept and c["t"] - kept[-1]["t"] < MIN_GAP:
            notes.append(f"{c['t']:.2f} s {c['sfx']}: {c['t'] - kept[-1]['t']:.2f} s after {kept[-1]['sfx']}, skipped"); continue
        kept.append(c)
    # a run of ticks steps up in pitch
    run = 0
    for i, c in enumerate(kept):
        prev = next((p for p in reversed(kept[:i]) if p["sfx"] == "tick"), None)
        run = run + 1 if c["sfx"] == "tick" and prev and c["t"] - prev["t"] < 1.0 else 0
        c["variant"] = run if c["sfx"] == "tick" else 0
    beats = sum(1 for i, c in enumerate(kept) if i == 0 or c["t"] - kept[i - 1]["t"] > 0.6)   # a run of ticks is one beat
    if dur and beats / dur > MAX_RATE:
        notes.append(f"{beats} sound beats in {dur:.1f} s: keep SFX for structure (slams, dips, pills, logo), not every word")
    return kept, notes


def mix(base, cues, ref, level):
    out = base.copy()
    cache = {}
    for c in cues:
        key = (c["sfx"], c["variant"])
        if key not in cache:
            snd = KIT[c["sfx"]][0](c["variant"])
            cache[key] = snd / 10 ** (momentary_max(snd) / 20)      # loudest 400 ms at 0 LUFS
        snd = cache[key] * 10 ** ((ref + KIT[c["sfx"]][2] + c.get("gain", 0) + level) / 20)
        start = int(round((c["t"] - KIT[c["sfx"]][1]) * SR))
        if start < 0:
            snd, start = snd[-start:], 0
        end = min(len(out), start + len(snd))
        out[start:end] += snd[:end - start]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", nargs="?"); ap.add_argument("out", nargs="?")
    ap.add_argument("--cues", action="append", default=[], metavar="FILE[@START]",
                    help="cue sheet from render.cjs; @START = where that render begins in this video")
    ap.add_argument("--offset", type=float, default=0.0, help="default START for --cues given without @")
    ap.add_argument("--broll", help="placements from broll.py --plan-out")
    ap.add_argument("--at", action="append", default=[], metavar="TIME=SOUND[@GAIN]")
    ap.add_argument("--level", type=float, default=0.0, help="raise or lower every sound (dB)")
    ap.add_argument("--no-master", action="store_true", help="keep the voice level as it is (no loudnorm)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--kit", metavar="DIR", help="export the kit as WAV files")
    ap.add_argument("--preview", metavar="WAV", help="write every sound once, to listen to")
    a = ap.parse_args()

    if a.kit:
        d = Path(a.kit); d.mkdir(parents=True, exist_ok=True)
        meta = {}
        for name, (fn, hit, rel, use) in KIT.items():
            write_wav(d / f"nh-{name}.wav", fn(0))
            meta[name] = {"file": f"nh-{name}.wav", "hit_seconds": hit, "db_under_voice": -rel, "use": use}
        (d / "kit.json").write_text(json.dumps(meta, indent=2))
        print(f"{len(KIT)} sounds → {d}/ (hit_seconds = where the sound lands; line that point up with the event)")
        return
    if a.preview:
        parts = []
        for name, (fn, hit, rel, use) in KIT.items():
            s = fn(0); s = s / 10 ** (momentary_max(s) / 20) * 10 ** ((-18 + rel + 6) / 20)
            parts += [s, np.zeros((int(0.6 * SR), 2))]
            print(f"  {sum(len(p) for p in parts[:-2]) / SR:5.2f} s  {name:7s} {use}")
        write_wav(a.preview, np.concatenate(parts), peak_db=-6)
        print(f"wrote {a.preview}")
        return
    if not a.video or not a.out:
        sys.exit("Give a video and an output: sfx.py final.mp4 out.mp4 --cues ... (or --kit DIR / --preview kit.wav)")

    dur, has_audio = probe(a.video)
    cues = [parse_at(t) for t in a.at]
    for spec in a.cues:
        f, sep, off = spec.rpartition("@")
        if not sep or not re.fullmatch(r"-?[\d.]+", off):
            f, off = spec, a.offset
        off = float(off)
        for c in load_json(f, "cue sheet"):
            if "t" not in c or "sfx" not in c:
                sys.exit(f"{f}: each cue needs t and sfx: {c}")
            cues.append({"t": float(c["t"]) + off, "sfx": c["sfx"], "gain": float(c.get("gain", 0)), "what": c.get("what", "")})
    if a.broll:
        found, cuts = broll_cues(load_json(a.broll, "b-roll plan"))
        cues += found
        if cuts:
            print(f"note: {cuts} plain cut{'s' if cuts > 1 else ''} into b-roll left silent (natural cutaways); add one with --at if needed")
    if not cues:
        sys.exit("No sounds to place. Give --cues, --broll or --at.")
    kept, notes = place(cues, dur)
    for n in notes:
        print("note: " + n)

    base = read_audio(a.video, dur, has_audio)
    voice = integrated(base) if has_audio else None
    ref = voice if voice is not None else SILENT_REF
    print(f"{len(kept)} sound{'s' if len(kept) != 1 else ''} on {Path(a.video).name} ({dur:.2f} s), "
          + (f"voice at {voice:.1f} LUFS" if voice is not None else f"no voice: sounds set against {SILENT_REF:g} LUFS, not mastered"))
    for c in kept:
        print(f"  {c['t']:6.2f}  {c['sfx']:7s} {KIT[c['sfx']][2] + c.get('gain', 0) + a.level:+.0f} dB  {c.get('what', '')}")
    if a.dry_run:
        return

    out = mix(base, kept, ref, a.level)
    master = voice is not None and not a.no_master
    if not master and np.max(np.abs(out)) > 0.89:        # keep a little headroom without a mastering pass
        out *= 0.89 / np.max(np.abs(out))
    af = ["-af", "loudnorm=I=-14:TP=-2:LRA=11,aresample=48000"] if master else []
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(a.video), "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
           "-map", "0:v", "-map", "1:a", "-c:v", "copy", *af, "-c:a", "aac", "-b:a", "192k", "-ar", str(SR),
           "-shortest", "-movflags", "+faststart", str(a.out)]
    r = subprocess.run(cmd, input=out.astype(np.float32).tobytes(), capture_output=True)
    if r.returncode:
        sys.exit("ffmpeg failed:\n" + r.stderr.decode(errors="replace")[-2000:])
    print(f"wrote {a.out}" + (" (mastered to -14 LUFS)" if master else ""))


if __name__ == "__main__":
    main()
