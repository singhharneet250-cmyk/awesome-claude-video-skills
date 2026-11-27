#!/usr/bin/env python3
"""
Clear, natural voice (owner request, 2026-11-26). Measures the recording first, then corrects only what it finds,
gently, so the voice still sounds like the person in the room:

  rumble   high-pass at 80 Hz (always)
  noise    light spectral denoise, only as strong as the measured noise floor needs (never "underwater")
  mud      a cut around 250 Hz when 150-300 Hz sits well above 300-800 Hz
  clarity  a presence lift around 3 kHz when 2-4 kHz sits too far below the body of the voice
  air      a small high shelf from 6 kHz when the top end is dull (phone and WhatsApp audio)
  sibilance a light de-esser after the lifts
  level    gentle 2.5:1 compression so quiet words come up; loudness is finished later (sfx.py, -14 LUFS)

    python3 voice.py take.mp4 clean.mp4              # the video with the cleaned voice (picture copied)
    python3 voice.py take.mp4 clean.wav              # just the voice, 48 kHz
    python3 voice.py take.mp4 --report               # what it measured and what it would change
    python3 voice.py take.mp4 ab.wav --ab 0-10       # before then after, level-matched, to listen to

Run it before timeline.py (the cleaned file becomes the source) or on the finished reel before sfx.py.
Needs ffmpeg, numpy and soundfile.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

try:
    import soundfile as sf
except ImportError:
    sys.exit("voice.py needs soundfile: pip install soundfile")

SR = 48000


def load(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True)
    x = np.frombuffer(r.stdout, np.float32)
    if not len(x):
        sys.exit(f"No audio in {path}")
    return x


def measure(x):
    win = int(0.05 * SR)
    n = len(x) // win
    rms = np.sqrt((x[: n * win].reshape(n, win) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms)
    speech = db > np.percentile(db, 60)
    noise_db, speech_db = float(np.percentile(db, 10)), float(np.percentile(db, 90))
    seg = 4096
    frames = x[: (len(x) // seg) * seg].reshape(-1, seg)
    fdb = 20 * np.log10(np.sqrt((frames ** 2).mean(1)) + 1e-9)
    loud = frames[fdb > np.percentile(fdb, 60)]
    S = np.abs(np.fft.rfft(loud * np.hanning(seg), axis=1)).mean(0)
    f = np.fft.rfftfreq(seg, 1 / SR)
    band = lambda lo, hi: float(20 * np.log10(S[(f >= lo) & (f < hi)].mean() + 1e-9))
    b = {"low": band(150, 300), "body": band(300, 800), "pres": band(2000, 4000), "air": band(4000, 8000)}
    return {"noise": noise_db, "speech": speech_db, "snr": speech_db - noise_db, "peak": float(20 * np.log10(np.abs(x).max() + 1e-9)), **b}


def plan(m):
    mud = float(np.clip((m["low"] - m["body"]) - 1.5, 0, 4))           # dB to cut at 250 Hz
    pres = float(np.clip(((m["body"] - m["pres"]) - 16) * 0.6, 0, 6))    # dB to lift at 3 kHz (phone voices sit 20-25 dB down)
    air = float(np.clip(((m["pres"] - m["air"]) - 10) * 0.4, 0, 3))      # dB high shelf from 6 kHz
    nr = float(np.clip(30 - m["snr"], 4, 10))                           # denoise strength, dB (the compressor lifts the floor)
    chain = ["highpass=f=80",
             f"afftdn=nr={nr:.1f}:nf={max(-80, m['noise'] - 4):.0f}:tn=1"]
    if mud >= 0.5:
        chain.append(f"equalizer=f=250:t=q:w=1.0:g={-mud:.1f}")
    if pres >= 0.5:
        chain.append(f"equalizer=f=3000:t=q:w=0.9:g={pres:.1f}")
    if air >= 0.5:
        chain.append(f"highshelf=f=6000:g={air:.1f}")
    chain += ["deesser=i=0.35:m=0.5:f=0.5",
              "acompressor=threshold=-26dB:ratio=2.5:attack=8:release=160:makeup=1.5",
              f"aresample={SR}"]
    return {"mud_cut": mud, "presence": pres, "air": air, "denoise": nr}, ",".join(chain)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src"); ap.add_argument("out", nargs="?")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--ab", metavar="S-E", help="write before then after of this stretch, both at -16 LUFS")
    a = ap.parse_args()
    x = load(a.src)
    m = measure(x)
    p, chain = plan(m)
    print(f"measured: speech {m['speech']:.0f} dBFS, noise {m['noise']:.0f} dBFS (SNR {m['snr']:.0f} dB), peak {m['peak']:.1f} dBFS; "
          f"150-300 Hz {m['low'] - m['body']:+.1f} dB vs body, 2-4 kHz {m['pres'] - m['body']:+.1f} dB, 4-8 kHz {m['air'] - m['body']:+.1f} dB")
    print(f"plan: denoise {p['denoise']:.1f} dB, mud cut {p['mud_cut']:.1f} dB, presence +{p['presence']:.1f} dB, air +{p['air']:.1f} dB")
    if a.report or not a.out:
        print("chain:", chain)
        return
    out = Path(a.out)
    if a.ab:
        s, e = (float(v) for v in a.ab.split("-"))
        norm = "loudnorm=I=-16:TP=-2:LRA=11"
        g = ["ffmpeg", "-y", "-v", "error", "-ss", str(s), "-t", str(e - s), "-i", a.src, "-filter_complex",
             f"[0:a]asplit[a][b];[a]aformat=channel_layouts=mono,{norm},aresample={SR}[x];"
             f"[b]aformat=channel_layouts=mono,{chain},{norm},aresample={SR}[y];[x]apad=pad_dur=0.6[x2];[x2][y]concat=n=2:v=0:a=1[o]",
             "-map", "[o]", str(out)]
        r = subprocess.run(g, capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stderr[-600:])
        print(f"wrote {out}: before ({e - s:.0f} s), then after")
        return
    if out.suffix.lower() in (".wav", ".flac"):
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.src, "-vn", "-af", f"aformat=channel_layouts=mono,{chain}", "-ac", "2", str(out)]
    else:
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.src, "-map", "0:v?", "-map", "0:a", "-c:v", "copy",
               "-af", f"aformat=channel_layouts=mono,{chain}", "-ac", "2", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-600:])
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
