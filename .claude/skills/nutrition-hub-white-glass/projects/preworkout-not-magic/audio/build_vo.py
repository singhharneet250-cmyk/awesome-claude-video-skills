"""Place the chosen voiceover takes on the reel and work out the time warp that retimes the animation to them.

    python3 audio/build_vo.py <takes_dir> <out_dir> 1:1 2:2 3:1 ... [--tempo 1.1]   (line:take, one per line)

--tempo speeds the cloned lines (pitch kept) toward the client's natural pace; take 9 (their real recording) is left as is.

For each scene it keeps the motion at its designed speed and spends any extra time the line needs in that scene's
static hold (HOLD below), so reveals and transitions never slow down; scene 2 has no hold and stretches evenly.
Writes <out_dir>/vo.wav (48 kHz mono, lines placed on the real timeline) and <out_dir>/warp.json
([real, anim] knots for index.html WARP and audio/sfx.py WARP). Needs numpy and ffmpeg.
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000
A = [0, 2.0, 4.0, 7.0, 10.0, 13.0, 16.0, 19.0, 21.6, 24.5]          # scene boundaries, animation time
LEAD = [0.15, 0.3, 0.45, 0.45, 0.3, 0.35, 0.3, 0.35, 0.5]            # line starts this long after its scene starts
HOLD = [(1.0, 1.55), (2.0, 4.0), (5.9, 6.7), (9.0, 9.45), (11.8, 12.5), (15.1, 15.65), (16.8, 18.45), (20.55, 21.2), (23.4, 24.5)]
GAP = 0.25                                                            # silence after a line before the next scene
END_HOLD = 1.3                                                        # end card holds this long after the last line


def load48k(path, tempo=1.0):
    af = ["-af", f"atempo={tempo}"] if tempo != 1.0 else []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), *af, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def trim(x, floor_db=-42.0, pre=.03, post=.10):
    win = int(.01 * SR)
    n = len(x) // win
    rms = np.sqrt(np.mean(x[: n * win].reshape(n, win) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms / (np.max(rms) + 1e-12))
    on = np.where(db > floor_db)[0]
    if not len(on):
        return x
    a = max(0, on[0] * win - int(pre * SR))
    b = min(len(x), (on[-1] + 1) * win + int(post * SR))
    y = x[a:b].copy()
    f = int(.008 * SR)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y


def level(x, target_db=-20.0):
    """Match every line's speech level (RMS of its voiced 10 ms frames), so cloned and recorded lines sit together."""
    win = int(.01 * SR)
    n = len(x) // win
    rms = np.sqrt(np.mean(x[: n * win].reshape(n, win) ** 2, axis=1) + 1e-12)
    voiced = rms[rms > np.max(rms) * .1]
    return x * (10 ** (target_db / 20) / (np.sqrt(np.mean(voiced ** 2)) + 1e-9))


def main():
    takes, out = Path(sys.argv[1]), Path(sys.argv[2])
    args = sys.argv[3:]
    tempo = 1.0
    if "--tempo" in args:
        i = args.index("--tempo"); tempo = float(args[i + 1]); del args[i:i + 2]
    choice = dict(map(int, s.split(":")) for s in args)
    out.mkdir(parents=True, exist_ok=True)
    lines = [level(trim(load48k(takes / f"line{n}_take{choice.get(n, 1)}.wav", 1.0 if choice.get(n) == 9 else tempo)))
             for n in range(1, 10)]

    knots, starts, R = [[0.0, 0.0]], [], 0.0
    for k in range(9):
        a0, a1 = A[k], A[k + 1]
        d = len(lines[k]) / SR
        need = LEAD[k] + d + (END_HOLD if k == 8 else GAP)
        L = max(a1 - a0, need)
        ext = L - (a1 - a0)
        h0, h1 = HOLD[k]
        starts.append(R + LEAD[k] * (L / (a1 - a0) if (h0, h1) == (a0, a1) else 1))
        if ext > 1e-6 and (h0, h1) != (a0, a1):
            knots.append([round(R + (h0 - a0), 4), h0])
            knots.append([round(R + (h1 - a0) + ext, 4), h1])
        R += L
        if knots[-1][1] != a1:
            knots.append([round(R, 4), a1])
        print(f"scene {k + 1}: line {d:.2f} s  scene {a1 - a0:.2f} -> {L:.2f} s  line at {starts[-1]:.2f} s")

    total = R
    track = np.zeros(int(total * SR) + SR)
    for s, x in zip(starts, lines):
        i = int(s * SR)
        track[i:i + len(x)] += x
    track = track[: int(total * SR)]
    pcm = (np.clip(track / (np.max(np.abs(track)) + 1e-9) * .9, -1, 1) * 32767).astype("<i2")
    with wave.open(str(out / "vo.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    (out / "warp.json").write_text(json.dumps({"duration": round(total, 3), "warp": knots,
                                               "lines": [[round(s, 3), round(len(x) / SR, 3)] for s, x in zip(starts, lines)]}, indent=1))
    print(f"total {total:.2f} s → {out / 'vo.wav'}, {out / 'warp.json'}")


if __name__ == "__main__":
    main()
