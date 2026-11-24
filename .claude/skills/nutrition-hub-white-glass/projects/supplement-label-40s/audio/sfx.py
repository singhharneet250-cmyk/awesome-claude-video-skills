"""Original sound design for the supplement-label reel (procedural, royalty-free).
Writes sfx.wav (48 kHz stereo float32) placed on the composition's timeline.
usage: sfx.py <out.wav>"""
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
rng = np.random.default_rng(7)
DUR = 59.9

# timeline (must match index.html SC + beat times)
SC = dict(s1=0, s2=4.37, s3=7.70, s4=15.07, s5=29.30, s6=38.00, s7=46.95, s8=51.02)
TURN = 2.15


def T(n): return np.arange(int(n * SR)) / SR
def db(x): return 10 ** (x / 20)


def norm(x):
    m = np.max(np.abs(x)) + 1e-12
    return x / m


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype='band', fs=SR, output='sos'); return signal.sosfilt(sos, x)


def hp(x, f, order=2):
    sos = signal.butter(order, f, btype='high', fs=SR, output='sos'); return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    sos = signal.butter(order, f, btype='low', fs=SR, output='sos'); return signal.sosfilt(sos, x)


def fade(x, a=.002, r=.01):
    n = len(x); ai, ri = max(1, int(a * SR)), max(1, int(r * SR))
    e = np.ones(n); e[:ai] = np.linspace(0, 1, ai); e[-ri:] = np.minimum(e[-ri:], np.linspace(1, 0, ri)); return x * e


def swept_noise(dur, f0, f1, width_oct=.7):
    """noise through a band that glides from f0 to f1 (STFT mask)"""
    n = int(dur * SR); x = rng.standard_normal(n + 2048)
    f, tt, Z = signal.stft(x, SR, nperseg=1024, noverlap=896)
    prog = np.clip(tt / dur, 0, 1)
    fc = np.exp(np.log(f0) + (np.log(f1) - np.log(f0)) * prog)
    ff = np.maximum(f, 20)[:, None]
    G = np.exp(-.5 * (np.log2(ff / fc[None, :]) / width_oct) ** 2)
    _, y = signal.istft(Z * G, SR, nperseg=1024, noverlap=896)
    return y[:n]


# ---------------- sound sources ----------------
def whoosh(dur=.55, f0=500, f1=3200, peak=.62):
    y = swept_noise(dur, f0, f1); t = T(dur)[:len(y)]
    e = np.where(t < peak * dur, np.sin(np.pi / 2 * t / (peak * dur)) ** 2, np.cos(np.pi / 2 * np.clip((t - peak * dur) / ((1 - peak) * dur), 0, 1)) ** 1.5)
    return fade(norm(y * e), .005, .02)


def riser(dur=.7):
    y = swept_noise(dur, 400, 6000, .9); t = T(dur)[:len(y)]
    gl = np.sin(2 * np.pi * np.cumsum(300 + 700 * (t / dur) ** 1.5) / SR) * .25
    e = (t / dur) ** 1.8
    return fade(norm((y + gl) * e), .01, .04)


def impact():
    t = T(1.0); f = 42 + 26 * np.exp(-t / .09)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .38)
    body = lp(rng.standard_normal(len(t)), 420) * np.exp(-t / .06) * .9
    air = hp(rng.standard_normal(len(t)), 6000) * np.exp(-t / .16) * .12
    return fade(norm(sub + body + air), .006, .1)


def pop(freq=900):
    t = T(.2); f = freq * (1 + .55 * np.exp(-t / .012)); ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / .05) + .3 * np.sin(2 * ph) * np.exp(-t / .025)
    click = hp(rng.standard_normal(len(t)), 3000) * np.exp(-t / .0015) * .25
    return fade(norm(y + click), .001, .03)


def tick(f=4200):
    t = T(.03)
    y = bp(rng.standard_normal(len(t)), 2500, 7000) * np.exp(-t / .0018) + .6 * np.sin(2 * np.pi * f * t) * np.exp(-t / .005)
    return fade(norm(y), .0003, .005)


def beep(f=2300, dur=.09):
    t = T(dur); y = np.sin(2 * np.pi * f * t) + .15 * np.sin(2 * np.pi * 2 * f * t)
    return fade(norm(y), .004, .02)


def thud():
    t = T(.35); f = 58 + 90 * np.exp(-t / .03)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .12)
    y += lp(rng.standard_normal(len(t)), 900) * np.exp(-t / .025) * .6
    y += bp(rng.standard_normal(len(t)), 1400, 2600) * np.exp(-t / .012) * .35
    return fade(norm(y), .0005, .05)


def clink(seed):
    r = np.random.default_rng(seed); t = T(.3)
    modes = [(2300, .06, 1), (3650, .045, .7), (5200, .03, .5), (7300, .02, .35)]
    y = sum(a * np.sin(2 * np.pi * f * (1 + r.uniform(-.08, .08)) * t + r.uniform(0, 6)) * np.exp(-t / d) for f, d, a in modes)
    y += np.sin(2 * np.pi * 170 * t) * np.exp(-t / .02) * .8
    y += hp(r.standard_normal(len(t)), 2500) * np.exp(-t / .002) * .5
    return fade(norm(y), .0003, .05)


def scan(dur=.6):
    t = T(dur); f = 1400 + 1200 * t / dur
    car = np.sin(2 * np.pi * np.cumsum(f) / SR) * (.55 + .45 * np.sin(2 * np.pi * 30 * t))
    nz = bp(rng.standard_normal(len(t)), 1800, 4200) * .35
    e = np.sin(np.pi * t / dur) ** 1.2
    return fade(norm((car + nz) * e), .005, .02)


def lock():
    t = T(.08)
    y = hp(rng.standard_normal(len(t)), 2000) * np.exp(-t / .0015) * .7
    y += np.sin(2 * np.pi * 1250 * t) * np.exp(-t / .018) + .5 * np.sin(2 * np.pi * 2500 * t) * np.exp(-t / .01)
    return fade(norm(y), .0005, .02)


def fill(dur=1.6):
    t = T(dur); p = 1 - (1 - t / dur) ** 3
    f = 520 + 560 * p + 4 * np.sin(2 * np.pi * 5 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + .25 * np.sin(2 * ph) + .1 * np.sin(3 * ph)
    e = np.minimum(1, t / .08) * (1 - .55 * t / dur)
    return fade(norm(y * e), .01, .12)


def bell(f, dur=.7, ratio=1.4, index=1.6, decay=.3):
    t = T(dur); mi = index * np.exp(-t / .12)
    y = np.sin(2 * np.pi * f * t + mi * np.sin(2 * np.pi * f * ratio * t)) * np.exp(-t / decay)
    return fade(y, .002, .05)


def chord(notes, gap, **kw):
    parts = [bell(f, **kw) for f in notes]
    out = np.zeros(int(gap * SR * (len(notes) - 1)) + len(parts[0]))
    for i, p in enumerate(parts):
        s = int(i * gap * SR); out[s:s + len(p)] += p
    return norm(out)


def confirm(f=880):
    return chord([f, f * 1.5], .075, ratio=2.0, index=.6, decay=.2, dur=.5)


def success():
    return chord([1046.5, 1318.5, 1568.0, 2093.0], .07, ratio=1.4, index=1.2, decay=.35, dur=.9)


def ping():
    return chord([1760.0, 2349.3], .09, ratio=2.0, index=1.5, decay=.3, dur=.9)


def alert():
    t = T(.5); y = np.zeros(len(t))
    for i, f in enumerate([660, 523]):
        s = int(i * .13 * SR); tt = t[:len(t) - s]
        y[s:] += (np.sin(2 * np.pi * f * tt) + .12 * np.sin(2 * np.pi * 3 * f * tt)) * np.exp(-tt / .16)
    return fade(norm(y), .003, .05)


def marker(dur=.45):
    y = swept_noise(dur, 1800, 5200, .5); t = T(dur)[:len(y)]
    e = np.minimum(1, t / .05) * np.minimum(1, (dur - t) / .08)
    return fade(norm(y * e), .005, .02)


def tap(seed):
    r = np.random.default_rng(seed); t = T(.05)
    y = bp(r.standard_normal(len(t)), 1800, 4200) * np.exp(-t / .003) + .5 * np.sin(2 * np.pi * r.uniform(160, 200) * t) * np.exp(-t / .012)
    return fade(norm(y), .0003, .01)


def shimmer(dur=2.2):
    t = T(dur); y = np.zeros((len(t), 2))
    r = np.random.default_rng(3)
    for _ in range(26):
        f = r.uniform(2500, 9000); s = r.uniform(0, .9) ** 1.6; d = r.uniform(.2, .55); a = r.uniform(.2, 1) * (1 - s)
        n0 = int(s * SR); tt = t[:len(t) - n0]
        part = np.sin(2 * np.pi * f * tt) * np.exp(-tt / d) * a
        pan = r.uniform(.15, .85)
        y[n0:, 0] += part * np.sqrt(1 - pan); y[n0:, 1] += part * np.sqrt(pan)
    pad = sum(np.sin(2 * np.pi * f * t) for f in (1318.5, 1975.5, 2637.0)) * np.minimum(1, t / .3) * np.exp(-t / 1.0) * .35
    y += pad[:, None]
    y /= np.max(np.abs(y)) + 1e-9
    e = np.ones(len(t)); e[-int(.3 * SR):] = np.linspace(1, 0, int(.3 * SR))
    return y * e[:, None]


def bloom():
    t = T(1.6)
    y = (np.sin(2 * np.pi * 55 * t) + .5 * np.sin(2 * np.pi * 110 * t) + .2 * np.sin(2 * np.pi * 165 * t))
    e = np.minimum(1, t / .18) ** 2 * np.exp(-np.maximum(0, t - .18) / .6)
    return fade(norm(y * e), .01, .2)


# ---------------- LCD count ticks (match the page's ease-out bezier) ----------------
def bezier(x1, y1, x2, y2):
    cx, cy = 3 * x1, 3 * y1; bx, by = 3 * (x2 - x1) - cx, 3 * (y2 - y1) - cy; ax, ay = 1 - cx - bx, 1 - cy - by
    sx = lambda t: ((ax * t + bx) * t + cx) * t; sy = lambda t: ((ay * t + by) * t + cy) * t
    def f(x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        lo, hi, t = 0.0, 1.0, x
        for _ in range(40):
            v = sx(t)
            if abs(v - x) < 1e-6: break
            lo, hi = (t, hi) if v < x else (lo, t); t = (lo + hi) / 2
        return sy(t)
    return f


EOUT = bezier(.22, 1, .36, 1)
count_ticks, last = [], 0
for i in range(int(1.2 * 1000)):
    lt = 2.35 + i / 1000
    v = round(33 * EOUT(min(1, (lt - 2.35) / 1.15)))
    if v != last: count_ticks.append(SC['s3'] + lt); last = v

# ---------------- events: (time, sound, gain dB, pan 0..1, reverb send) ----------------
E = []
add = lambda t, snd, g, pan=.5, rv=.12: E.append((t, snd, g, pan, rv))
W = lambda: whoosh(.55, 600, 3400)
# scene 1
add(0.04, impact(), -6, .5, .15)
add(0.02, whoosh(.85, 300, 2600, .55), -14, .35)
add(SC['s1'] + TURN, whoosh(.45, 900, 3000), -19, .6)
add(SC['s1'] + TURN + .45, riser(.7), -17, .5, .1)
add(SC['s1'] + TURN + .8, scan(.6), -21, .45)
add(SC['s1'] + TURN + 1.4, scan(.6), -22, .55)
# scene 2 (flatten + checkpoints)
add(SC['s2'] - .12, W(), -18, .5)
for i, f in enumerate([880, 988, 1109, 1319]):
    add(SC['s2'] + .95 + i * .4, pop(f), -15, .58, .15)
# transitions with the orange streak
for k in ['s3', 's4', 's5', 's6', 's7', 's8']:
    add(SC[k] - .32, whoosh(.6, 700, 4200, .5), -16, .5, .1)
# scene 3: scoop drop, thud, count, beep, bracket
add(SC['s3'] + 1.85, whoosh(.45, 3000, 600, .7), -21, .5)
add(SC['s3'] + 2.30, thud(), -8, .5, .08)
for c in count_ticks: add(c, tick(4200 + rng.uniform(-150, 150)), -24, .55, .03)
add(SC['s3'] + 3.52, beep(), -19, .55, .1)
add(SC['s3'] + 3.95, lock(), -17, .5, .1)
# scene 4: cards, bigger scoop, ring fill, winner
add(SC['s4'] + .55, pop(660), -18, .35)
add(SC['s4'] + .70, pop(740), -18, .65)
add(SC['s4'] + 3.70, pop(988), -19, .65)
add(SC['s4'] + 6.40, fill(1.6), -22, .5, .15)
add(SC['s4'] + 8.75, success(), -13, .4, .25)
add(SC['s4'] + 10.6, pop(784), -21, .5)
# scene 5: sugar cubes + warning
for i in range(6):
    add(SC['s5'] + .9 + .42 + i * .16, clink(11 + i), -13 - (i % 3), .35 + .06 * i, .12)
add(SC['s5'] + 4.10, alert(), -19, .5, .15)
# scene 6: list, marker box, amino tags
add(SC['s6'] + .5, whoosh(.5, 2400, 900, .4), -24, .5)
add(SC['s6'] + 1.90, marker(), -18, .45, .08)
for i, f in enumerate([740, 880, 988]):
    add(SC['s6'] + 3.85 + i * .1, pop(f), -20, .35 + .15 * i)
# scene 7: genuine ticks
for i, (tt, f) in enumerate(zip([1.0, 1.9, 2.9], [880, 988, 1175])):
    add(SC['s7'] + tt, confirm(f), -14, .5, .2)
# scene 8: type LABEL, post, reply, end card
for k in range(5): add(SC['s8'] + .75 + k * .12, tap(30 + k), -15, .5, .04)
add(SC['s8'] + 1.47, tap(40), -13, .5, .04)
add(SC['s8'] + 1.55, whoosh(.3, 1500, 5000, .4), -23, .6)
add(SC['s8'] + 1.65, pop(1046), -20, .5)
add(SC['s8'] + 2.25, ping(), -12, .55, .25)
add(SC['s8'] + 3.15, whoosh(.55, 3000, 700, .45), -18, .5)
add(SC['s8'] + 3.50, shimmer(), -15, .5, .3)
add(SC['s8'] + 3.55, bloom(), -11, .5, .05)
add(SC['s8'] + 4.50, pop(1175), -23, .5)

# ---------------- render bus ----------------
N = int(DUR * SR) + SR
dry = np.zeros((N, 2)); send = np.zeros((N, 2))
for t0, snd, g, pan, rv in E:
    x = snd if snd.ndim == 2 else np.stack([snd * np.sqrt(1 - pan) * 1.414, snd * np.sqrt(pan) * 1.414], 1)
    x = x * db(g)
    s = int(t0 * SR); e = min(N, s + len(x))
    dry[s:e] += x[:e - s]; send[s:e] += x[:e - s] * rv
# reverb: decaying stereo noise IR, band-limited
tt = T(1.3)
ir = np.stack([lp(hp(rng.standard_normal(len(tt)), 250), 7000) * np.exp(-tt / .32) for _ in range(2)], 1)
ir /= np.sqrt(np.sum(ir ** 2, 0, keepdims=True))
wet = np.stack([signal.fftconvolve(send[:, c], ir[:, c])[:N] for c in range(2)], 1) * .9
bus = (dry + wet)[:int(DUR * SR)]
peak = np.max(np.abs(bus))
print(f"events {len(E)}, count ticks {len(count_ticks)}, bus peak {20*np.log10(peak):.1f} dBFS")
wavfile.write(sys.argv[1], SR, bus.astype(np.float32))
