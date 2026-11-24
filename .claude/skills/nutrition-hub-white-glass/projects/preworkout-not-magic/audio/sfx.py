"""Original sound design for the "Pre-workout is NOT magic" reel (procedural, royalty-free).

Writes a 48 kHz stereo 16-bit WAV with every effect placed on the composition's timeline:
soft pops on the dot wave, ripple blooms, whooshes on card swipes, flip clacks, a shield crack,
sparkle chimes, heartbeat pulses along the vein, battery blips, timer ticks, keyboard clicks
for the search bar and a shimmer under the logo. No music: add a track inside Instagram.

usage: python3 audio/sfx.py <out.wav> [warp.json]   (needs numpy only)
warp.json (from audio/build_vo.py) retimes every cue to the voiceover cut; without it the 24.5 s cut is used.
Then normalise to -14 LUFS / -1.5 dBTP with ffmpeg loudnorm (see README.md).
Cue times mirror index.html; change both together.
"""
import sys
import wave

try:
    import numpy as np
except ImportError:
    sys.exit("sfx.py needs numpy: pip install numpy")

if len(sys.argv) not in (2, 3):
    sys.exit("usage: python3 audio/sfx.py <out.wav> [warp.json]")

SR = 48000
DUR = 24.5
WARP = [[0, 0], [24.5, 24.5]]                                  # [real, anim] knots, same table as index.html
if len(sys.argv) == 3:
    import json
    _w = json.load(open(sys.argv[2]))
    WARP, DUR = _w["warp"], _w["duration"]


def a2r(t):
    """Animation time (the cue times below) → real time on the retimed cut."""
    for (r0, a0), (r1, a1) in zip(WARP, WARP[1:]):
        if t <= a1:
            return r0 + (r1 - r0) * (t - a0) / (a1 - a0)
    return t - WARP[-1][1] + WARP[-1][0]

rng = np.random.default_rng(22)
mix = np.zeros((int(DUR * SR) + SR, 2))


def T(d):
    return np.arange(int(d * SR)) / SR


def place(x, t0, gain=1.0, pan=0.0):
    """Add mono x at t0 seconds with constant-power pan (-1 left .. 1 right)."""
    i = int(a2r(t0) * SR)
    a = (pan + 1) * np.pi / 4
    seg = x[: max(0, len(mix) - i)] * gain
    mix[i:i + len(seg), 0] += seg * np.cos(a)
    mix[i:i + len(seg), 1] += seg * np.sin(a)


def add(*xs):
    """Sum sounds of different lengths (zero-padded)."""
    n = max(len(x) for x in xs)
    out = np.zeros(n)
    for x in xs:
        out[:len(x)] += x
    return out


def adsr(n, a=.002, tau=.05):
    t = np.arange(n) / SR
    e = np.exp(-t / tau)
    ai = max(1, int(a * SR))
    e[:ai] *= np.linspace(0, 1, ai)
    return e


def glide_sine(f0, f1, d, curve=40.0):
    t = T(d)
    f = f1 + (f0 - f1) * np.exp(-t * curve)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def band_noise(d, f_lo, f_hi, shape=None):
    """Noise through a band whose centre glides from f_lo to f_hi (log), via a numpy STFT mask."""
    n = int(d * SR)
    win, hop = 1024, 256
    x = rng.standard_normal(n + win)
    w = np.hanning(win)
    out = np.zeros(n + win)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    lf = np.log2(np.maximum(freqs, 20))
    frames = range(0, n, hop)
    for k, s in enumerate(frames):
        p = s / max(1, n)
        fc = np.log2(f_lo) + (np.log2(f_hi) - np.log2(f_lo)) * p
        g = np.exp(-.5 * ((lf - fc) / .7) ** 2)
        spec = np.fft.rfft(x[s:s + win] * w) * g
        out[s:s + win] += np.fft.irfft(spec, win) * w
    out = out[:n]
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** (shape or 1.6)
    y = out * env
    return y / (np.max(np.abs(y)) + 1e-9)


def pop(f, d=.11, tau=.035):
    """Soft bubble pop: a quick downward glide with a fast decay."""
    y = glide_sine(f * 1.7, f, d, 55) * adsr(int(d * SR), .0015, tau)
    return y


def click(d=.006, bright=True):
    n = int(d * SR)
    x = rng.standard_normal(n)
    if bright:
        x = np.diff(np.concatenate([[0], x]))
    return x * adsr(n, .0003, d / 3)


def chime(freqs, d=1.2, tau=.45):
    t = T(d)
    y = sum(np.sin(2 * np.pi * f * t + .3 * np.sin(2 * np.pi * 5.5 * t)) / (k + 1) for k, f in enumerate(freqs))
    return y * adsr(len(t), .004, tau)


def thud(f=70, d=.35, tau=.12):
    return glide_sine(f * 2.2, f, d, 30) * adsr(int(d * SR), .002, tau)


def tick(f=2400, d=.03):
    return np.sin(2 * np.pi * f * T(d)) * adsr(int(d * SR), .0005, .006)


def bloom(d=.9):
    """Ripple bloom: a soft low swell with an airy top."""
    t = T(d)
    body = np.sin(2 * np.pi * 220 * t) * .35 + np.sin(2 * np.pi * 330 * t) * .2
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return add(body * env, band_noise(d, 3000, 6000, 2.5) * .18)


C = ["blue", "red", "yellow", "green"]

# ---------- S1 hook: dot wave → NOT ----------
for i in range(4):
    place(pop(520 + 110 * i), .06 + i * .07, .55, -.45 + .3 * i)
for i in range(3):
    place(pop(760 + 150 * i, .14, .05), .42 + i * .07, .7, -.4 + .3 * i)
    place(band_noise(.25, 2500, 5000, 2), .44 + i * .07, .08)
place(pop(1250, .08, .025), .8, .5, .5)                      # 4th dot lands as the full stop
place(band_noise(.3, 4000, 1200), 1.56, .18)                 # letters fold back to dots

# ---------- S2 spinner → scoop → orbs ----------
place(band_noise(.6, 600, 2400), 1.88, .3)
for k in range(5):
    place(tick(1800 + 120 * k, .02), 2.15 + k * .15, .18, -.3 + .15 * k)
place(thud(150, .3, .08), 2.72, .45)
place(band_noise(.25, 5000, 7000), 2.72, .1)
for k in range(4):                                           # powder shake
    place(band_noise(.09, 3500, 6000, 1.2), 3.0 + k * .12, .22 * (1 - k * .2), (-1) ** k * .2)
place(band_noise(.5, 900, 3200), 3.18, .28)
for k in range(4):
    place(pop(600 + 100 * k), 3.22 + k * .07 + .5, .45, [-.6, .6, -.6, .6][k])

# ---------- S3 caffeine ----------
place(band_noise(.55, 500, 2000), 3.95, .32)
place(bloom(.9), 4.25, .5)
place(band_noise(.6, 3000, 6500, 2.2), 4.45, .06)          # line art drawing on
crack = np.zeros(int(.22 * SR))
for k in range(7):
    c = click(.004 + .004 * rng.random())
    s = int(rng.random() * .14 * SR)
    crack[s:s + len(c)] += c * (1 - k * .1)
place(crack, 5.22, .9, .35)
place(band_noise(.18, 2000, 900), 5.22, .25, .35)
place(chime([1568, 2349, 3136]), 5.45, .3, .2)
place(band_noise(.42, 2500, 500), 6.7, .4, -.5)              # swipe left
place(band_noise(.5, 600, 2200), 6.95, .3, .5)               # next card in

# ---------- S4 beta-alanine ----------
for a in (7.92, 7.98, 8.5, 8.56):                            # flip clacks
    place(add(click(.006, False) * .8, thud(240, .06, .015) * .5), a, .45, -.2)
    place(add(click(.005), thud(180, .05, .012) * .4), a + .42, .4, -.2)
for k in range(46):                                          # the tingle
    place(tick(4500 + 2500 * rng.random(), .012), 7.75 + rng.random() * 1.65, .05 + .04 * rng.random(), .3 + .5 * rng.random())
place(band_noise(.45, 2400, 400), 9.55, .35)                 # card shrinks to a dot

# ---------- S5 citrulline ----------
place(band_noise(.5, 500, 1800), 10.0, .3)
place(pop(500, .16, .06), 10.0, .45)
for a in (10.45, 11.3):                                      # pulse: lub-dub
    place(thud(58, .32, .09), a, .95)
    place(thud(52, .3, .08), a + .19, .7)
    place(band_noise(.7, 400, 1600, 1.4), a, .08, -.6 + 1.2 * 0)
place(add(thud(85, .4, .1), click(.008, False) * .6), 11.45, .85)  # BIG PUMP stamp
place(band_noise(.42, 2000, 500), 12.56, .3)

# ---------- S6 creatine ----------
place(band_noise(.55, 700, 2500, 2.0), 12.85, .18)
for k, f in enumerate([523.25, 659.25, 783.99, 1046.5]):     # battery steps
    y = np.sin(2 * np.pi * f * T(.28)) * adsr(int(.28 * SR), .004, .09) + np.sin(2 * np.pi * 2 * f * T(.28)) * adsr(int(.28 * SR), .002, .05) * .25
    place(y, 13.45 + k * .28, .42, -.4 + .27 * k)
place(pop(880, .12, .04), 14.5, .4)
place(chime([1760, 2637, 3520], 1.1, .4), 14.66, .26, .3)
place(band_noise(.32, 2000, 800), 15.66, .2)

# ---------- S7 timing ----------
place(band_noise(.75, 500, 2600), 15.85, .3)
for k in range(4):
    place(pop(660 + 90 * k, .1, .03), 16.42 + k * .04, .4, [0, .6, 0, -.6][k])
place(add(click(.01, False) * .6, thud(320, .08, .02) * .6), 16.78, .55)
place(bloom(.8), 16.78, .32)
t = 16.95
while t < 18.3:
    place(tick(2600, .02), t, .16, .1)
    t += .17
place(pop(700, .1, .03), 17.22, .35)
for k in range(2):
    place(band_noise(.12, 1500, 5000, 1.2), 17.8 + k * .12, .3, .4)
place(thud(110, .3, .07), 17.84, .45)
place(band_noise(.3, 1800, 700), 18.48, .18)

# ---------- S8 search ----------
place(band_noise(.58, 400, 1800), 18.74, .32)
for i, ch in enumerate("best pre-workout for me?"):
    k = add(click(.004 + .003 * rng.random(), False) * .7, band_noise(.018, 3000 + 1500 * rng.random(), 3600, 1.0) * .3)
    place(k, 19.35 + i * .03 + .004 * rng.random(), .32 if ch != " " else .45, .15)
place(band_noise(.45, 2400, 700), 20.08, .3)
place(pop(560, .14, .05), 20.42, .45)

# ---------- S8 → S9 colour sweep and end card ----------
for k in range(5):
    place(band_noise(.42, 300 + 160 * k, 1400 + 400 * k, 2.0), 21.22 + k * .06, .24 - .02 * k)
for i in range(4):
    place(pop(620 + 120 * i, .1, .03), 21.82 + i * .07, .4, -.45 + .3 * i)
place(band_noise(.35, 900, 3600), 22.1, .2)
logo = add(chime([523.25, 659.25, 783.99, 1046.5], 2.2, .9) * .6, band_noise(1.6, 2500, 7000, 2.5) * .2)
place(logo, 22.18, .5)
place(pop(700, .1, .03), 22.78, .3, .2)

# ---------- write ----------
y = mix[: int(DUR * SR)]
y = y / (np.max(np.abs(y)) + 1e-9) * .7                       # headroom; loudness is set by ffmpeg loudnorm
pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
with wave.open(sys.argv[1], "wb") as f:
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(SR)
    f.writeframes(pcm.tobytes())
print(f"wrote {sys.argv[1]} ({DUR} s)")
