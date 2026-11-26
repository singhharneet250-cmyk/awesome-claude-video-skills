#!/usr/bin/env python3
"""
Original music for Nutrition Hub films, made in code, so there is no licence to check (owner, 2026-11-26: the
Winter Wellness reel, "no voice: text + music"; assets.mixkit.co is not reachable from the cloud environment).

A calm cinematic bed at 120 BPM, so every scene change on a whole or half second lands on a beat:
  pad    warm, detuned voices on each chord, slow attack and release, gently filtered
  pluck  a soft FM arpeggio in eighth notes through the main section (a second octave joins in the second half)
  bells  a high FM bell motif in the intro and the ending
  pulse  a soft sub on beats 1 and 3 from the first scene change until the ending
  swells a short reverse swell into each scene change and a low bloom on it (--cuts)
Everything goes through a stereo convolution hall. The ending resolves on C add9 and fades.
Output: 48 kHz stereo WAV at about -20 LUFS; sfx.py adds the sound effects and sets the final -14 LUFS.

    python3 score.py music.wav --dur 48 --cuts 5,12,19,26,33,40
    python3 score.py music.wav --dur 30 --cuts 6,12,18,24 --ending 24

Needs numpy and scipy.
"""
import argparse
import sys

import numpy as np

try:
    from scipy.signal import fftconvolve
except ImportError:
    sys.exit("score.py needs scipy: pip install scipy")

SR = 48000
BPM = 120
BEAT = 60 / BPM
BAR = 4 * BEAT
# A minor, winter colour: Am9 · Fmaj7 · C add9 · G6, one bar each (MIDI notes)
CHORDS = {
    "Am9": [45, 52, 55, 59, 60], "Fmaj7": [41, 48, 52, 57, 64], "Cadd9": [48, 55, 62, 64, 67], "G6": [43, 50, 55, 59, 64],
}
ARP = {"Am9": [69, 72, 76, 71], "Fmaj7": [69, 72, 76, 77], "Cadd9": [67, 72, 74, 76], "G6": [67, 71, 74, 76]}
LOOP = ["Am9", "Fmaj7", "Cadd9", "G6"]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, r, sustain_n):
    """Attack a s, hold, release r s; n samples in total."""
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-3))
    rel_start = sustain_n / SR
    e = e * np.where(t > rel_start, np.exp(-(t - rel_start) / max(r, 1e-3)), 1)
    return e


def pad_note(f, dur, a=0.9, r=1.4, cutoff=1500, detune=(-0.07, 0.0, 0.07)):
    n = int((dur + r * 3) * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for k, cents in enumerate(detune):
        fd = f * 2 ** (cents / 12)
        v = np.zeros(n)
        for h in range(1, 13):
            fh = fd * h
            if fh > 9000:
                break
            v += np.sin(2 * np.pi * fh * t + h * 0.7 + k) * (1 / h) / (1 + (fh / cutoff) ** 2)
        p = (k - 1) * 0.45
        out[:, 0] += v * np.sqrt(0.5 * (1 - p)); out[:, 1] += v * np.sqrt(0.5 * (1 + p))
    return out * env_adsr(n, a, r, int(dur * SR))[:, None] * 0.12


def fm(f, dur, ratio, index, idecay, adecay, attack=0.004, amp=0.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    mod = index * np.exp(-t / idecay) * np.sin(2 * np.pi * f * ratio * t)
    v = np.sin(2 * np.pi * f * t + mod) * np.exp(-t / adecay) * np.minimum(1, t / attack)
    return v * amp


def sub_hit(f=55.0, dur=0.6, amp=0.32):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.6 * np.exp(-t / 0.035))) / SR
    return np.sin(ph) * np.exp(-t / 0.22) * np.minimum(1, t / 0.006) * amp


def swell(dur=0.7, seed=0, amp=0.05):
    """A soft reverse swell: filtered noise rising into the cut."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / SR)
    X *= np.exp(-((np.log2(np.maximum(fr, 1) / 2500)) ** 2) / 2)
    x = np.fft.irfft(X, n)
    x /= np.abs(x).max() + 1e-9
    e = (np.arange(n) / n) ** 2.6
    return x * e * amp


def add(buf, sig, at, pan=0.0, gain=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    if sig.ndim == 1:
        l, r = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
        sig = np.stack([sig * l, sig * r], 1)
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def hall(seconds=2.8, seed=3):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-t / 0.75)[:, None]
    k = 24
    ir = np.stack([np.convolve(ir[:, c], np.ones(k) / k, "same") for c in range(2)], 1)   # darker tail
    ir[: int(0.012 * SR)] = 0                                                           # pre-delay
    return ir / np.sqrt((ir ** 2).sum(0, keepdims=True))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--dur", type=float, default=48.0)
    ap.add_argument("--cuts", default="5,12,19,26,33,40", help="scene changes in seconds (swell into each, bloom on it)")
    ap.add_argument("--ending", type=float, help="when the ending starts (default: the last cut)")
    ap.add_argument("--intro", type=float, help="when the main section starts (default: the first cut)")
    a = ap.parse_args()
    cuts = [float(c) for c in a.cuts.split(",") if c.strip()]
    intro = a.intro if a.intro is not None else (cuts[0] if cuts else 4.0)
    ending = a.ending if a.ending is not None else (cuts[-1] if cuts else a.dur - 8)
    N = int((a.dur + 3) * SR)
    mix = np.zeros((N, 2))

    # pad: Am9 through the intro, then the loop, then F · G · C add9 to resolve
    plan = [("Am9", 0.0, intro)]
    t = intro
    k = 0
    while t < ending - 1e-6:
        d = min(BAR, ending - t)
        plan.append((LOOP[k % 4], t, d)); t += d; k += 1
    end_plan = [("Fmaj7", ending, BAR), ("G6", ending + BAR, BAR), ("Cadd9", ending + 2 * BAR, max(BAR, a.dur - ending - 2 * BAR))]
    plan += [p for p in end_plan if p[1] < a.dur]
    for name, t0, d in plan:
        for m in CHORDS[name]:
            add(mix, pad_note(hz(m), d, a=0.9 if t0 == 0 else 0.35, r=1.6 if name == "Cadd9" else 1.0), t0, gain=0.9)

    # pluck arpeggio: eighth notes from the intro to the last bar before the resolve
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    for name, t0, d in plan:
        if t0 < intro or t0 >= ending + 2 * BAR:
            continue
        steps = int(round(d / (BEAT / 2)))
        for s in range(steps):
            m = ARP[name][pat[s % 8]]
            tt = t0 + s * BEAT / 2
            vel = 0.75 + 0.25 * (s % 2 == 0)
            add(mix, fm(hz(m), 1.2, 2.0, 2.2, 0.12, 0.45, amp=0.07 * vel), tt, pan=0.35 * np.sin(s * 0.9))
            if tt >= (intro + ending) / 2 and s % 2 == 0:                 # the second half lifts an octave
                add(mix, fm(hz(m + 12), 1.0, 2.0, 1.6, 0.1, 0.35, amp=0.03), tt, pan=-0.3 * np.sin(s * 0.7))

    # bells: intro motif and the ending
    for tt, m in [(0.5, 76), (1.5, 81), (2.5, 83), (3.0, 79), (3.5, 76), (4.25, 74)]:
        if tt < intro:
            add(mix, fm(hz(m), 3.2, 3.5, 2.6, 0.7, 1.6, amp=0.06), tt, pan=0.2 * np.sin(tt * 3))
    for i, m in enumerate([79, 84, 86, 88, 91]):
        tt = ending + 2 * BAR + i * BEAT
        if tt < a.dur - 0.5:
            add(mix, fm(hz(m), 3.5, 3.5, 2.4, 0.8, 1.8, amp=0.055), tt, pan=0.25 * (i - 2) / 2)

    # pulse: soft sub on beats 1 and 3 through the main section
    tt = intro
    while tt < ending + BAR:
        add(mix, sub_hit(55.0, 0.55, 0.16), tt)
        tt += 2 * BEAT

    # scene changes: a swell into the cut and a low bloom on it
    for i, c in enumerate(cuts):
        add(mix, swell(0.7, seed=i, amp=0.06), c - 0.7)
        add(mix, sub_hit(41.2, 1.2, 0.26), c)

    # hall, master
    wet = np.stack([fftconvolve(mix[:, ch], hall()[:, ch])[:N] for ch in range(2)], 1)
    out = mix * 0.82 + wet * 0.34
    n_end = int(a.dur * SR)
    out = out[:n_end]
    fade = int(2.5 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.6
    out = np.tanh(out * 1.4) / 1.4
    rms = np.sqrt((out ** 2).mean())
    out *= 10 ** (-21 / 20) / max(rms, 1e-9)                   # about -20 LUFS for a soft bed
    peak = np.abs(out).max()
    if peak > 0.9:
        out *= 0.9 / peak
    import wave
    pcm = (np.clip(out, -1, 1) * 32767).astype(np.int16)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print(f"wrote {a.out}: {a.dur:.1f} s, {BPM} BPM, cuts {cuts}, ending {ending:.1f} s")


if __name__ == "__main__":
    main()
