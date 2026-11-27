#!/usr/bin/env python3
"""
White Glass captions: word timings -> libass captions (and an optional .srt sidecar).

    python3 captions.py words.json --out captions.ass
    python3 captions.py words.json --out captions.ass --srt captions.srt --keywords creatine,protein
    python3 captions.py cues.srt   --out captions.ass            # sentence-level cues (less exact)

Then burn in:
    ffmpeg -i in.mp4 -vf "ass=captions.ass:fontsdir=<skill>/assets/fonts" -c:a copy out.mp4   (Inter from the system fonts)

Input (any of):
  - Whisper / faster-whisper JSON with word timestamps: {"segments": [{"words": [{"word", "start", "end"}]}]}
  - a flat list of words: [{"word" or "text", "start", "end"}] in seconds
  - Remotion captions: [{"text", "startMs", "endMs"}]
  - an .srt file (sentence-level; words are spread over each cue by length, so check the sync; a cue is never
    merged with the next, so hand-written cues keep their phrases)

Rules applied (SKILL.md section 6):
  - at most 2 lines, about 28 characters per line
  - each caption on screen 1-3 s; a new caption starts at a pause or a sentence end
  - one key word per caption goes signal orange: a number with its unit first, then a word from
    --keywords; if neither is present the caption stays one colour (never a random word)
  - bare words, no box or pill: white with a soft shadow over footage (default), or ink with a
    soft white glow on light walls (--style ink); styles copied from reference/captions.ass
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
STYLE_FILE = SKILL / "reference" / "captions.ass"

BLUR = r"{\blur6}"              # softens the shadow border; the words themselves stay sharp
ORANGE = r"{\c&H0402D3&}"
RESET = r"{\r\blur6}"          # back to the style colour; {\r} also clears blur, so re-apply it
STYLES = {"footage": "NH-Caption", "ink": "NH-Caption-Ink", "strong": "NH-Caption-Strong"}
# vertical position: event MarginV (distance from the frame bottom to the caption bottom, on 1920)
POSITIONS = {"bottom": 520,   # §6 default: text bottom at y 1400 (73%)
             "mic": 731,      # R6 desk/mic shoots: caption centred about 58%, above a bottom blur band
             "chest": 885,    # R5 chest line: caption centred about 50%
             "top": 1590,     # text bottom at y 330, just under the top safe line: for edits where big words behind
                              # the head or a frame break fill the space around it (owner's IMG_0371 hook, 2026-11-27)
             "low": 428}      # text bottom at y 1492, just above the bottom safe line: under a chest print, inside a frame
                              # break. In an .srt a cue can pick its own position: start its text with {top} or {low}
# typeface accent (R6): one word per caption in Instrument Serif Italic, same colour as the caption
SERIF = r"{\fnInstrument Serif\b0\i1\fs80}"
SERIF_WORDS = set()

LINE_CHARS = 28
MAX_CHARS = 2 * LINE_CHARS
MIN_DUR, MAX_DUR = 1.0, 3.0
PAUSE_BREAK = 0.35   # a gap this long between words starts a new caption
BRIDGE_GAP = 0.30    # a gap this short between captions is bridged (no flicker)

UNITS = {
    "g", "gm", "gms", "gram", "grams", "mg", "mcg", "µg", "ug", "kg", "kgs", "lb", "lbs",
    "kcal", "cal", "calories", "%", "percent", "ml", "l", "litre", "litres", "liter", "liters",
    "iu", "x", "times", "min", "mins", "minutes", "sec", "seconds", "hours", "hrs", "days",
    "weeks", "months", "reps", "sets", "servings", "scoops", "scoop", "per", "a",
}
NUMBER_WORDS = {
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "fifteen", "twenty", "thirty", "forty", "fifty", "hundred", "thousand",
    "half", "double", "triple",
}
WEAK_ENDS = {"and", "or", "but", "the", "a", "an", "of", "to", "in", "on", "with", "for", "your", "is", "are"}
NUM_RE = re.compile(r"^[~≈<>]?\d[\d.,]*(?:[–\-/]\d[\d.,]*)?(?:%|g|mg|mcg|kg|ml|x|k)?$", re.I)


def load_words(path: Path):
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        sys.exit(f"Input not found: {path}")
    except IsADirectoryError:
        sys.exit(f"Input is a folder, not a file: {path}")
    except UnicodeDecodeError:
        sys.exit(f"{path} is not UTF-8 text. Export the transcript as UTF-8 JSON or .srt.")
    if not text.strip():
        sys.exit(f"{path} is empty: no words to caption.")
    if path.suffix.lower() == ".srt":
        words = words_from_srt(text)
        if not words:
            sys.exit(f"No subtitle cues found in {path}. Each cue needs a '00:00:01,000 --> 00:00:02,500' line followed by text.")
        return words, True
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        sys.exit(f"{path} is not valid JSON (line {e.lineno}, column {e.colno}: {e.msg}). "
                 "Pass word timings as JSON, or a subtitle file ending in .srt.")
    if isinstance(data, dict):
        if "segments" in data:
            raw = [w for seg in data["segments"] for w in seg.get("words", [])]
        elif "words" in data:
            raw = data["words"]
        else:
            sys.exit("JSON has no 'segments' or 'words'. See the header of this script for accepted shapes.")
    else:
        raw = data
    if not isinstance(raw, list):
        sys.exit("Expected a list of words. See the header of this script for accepted shapes.")
    words = []
    for n, w in enumerate(raw, 1):
        if not isinstance(w, dict):
            sys.exit(f"Word {n} is not an object with text and timings: {w!r}")
        t = str(w.get("word") or w.get("text") or "").strip()
        if not t:
            continue
        try:
            if "startMs" in w:
                s, e = float(w["startMs"]) / 1000, float(w["endMs"]) / 1000
            else:
                s, e = float(w["start"]), float(w["end"])
        except (KeyError, TypeError, ValueError):
            sys.exit(f"Word {n} ({t!r}) needs numeric start and end times "
                     "('start'/'end' in seconds or 'startMs'/'endMs').")
        words.append({"text": t, "start": s, "end": max(e, s + 0.05)})
    if not words:
        sys.exit("No words found in the input.")
    words.sort(key=lambda w: w["start"])
    return words, False


def srt_time(t: str) -> float:
    h, m, rest = t.strip().replace(".", ",").split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def words_from_srt(text: str):
    words = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l for l in block.strip().splitlines() if l.strip()]
        timing = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if timing is None:
            continue
        try:
            a, b = lines[timing].split("-->")
            start, end = srt_time(a), srt_time(b.split()[0])
        except (ValueError, IndexError):
            sys.exit(f"Bad .srt timing line: {lines[timing].strip()!r} "
                     "(expected '00:00:01,000 --> 00:00:02,500').")
        tokens = " ".join(lines[timing + 1:]).split()
        pos = None
        if tokens and re.fullmatch(r"\{(\w+)\}", tokens[0]):   # {top} / {low} / ...: this cue's own position
            pos = tokens.pop(0)[1:-1]
            if pos not in POSITIONS:
                sys.exit(f"Unknown caption position {{{pos}}} in the .srt (use {', '.join(sorted(POSITIONS))}).")
        if not tokens:
            continue
        total = sum(len(t) + 1 for t in tokens)
        t0 = start
        for tok in tokens:
            d = (end - start) * (len(tok) + 1) / total
            words.append({"text": tok, "start": t0, "end": t0 + d, **({"pos": pos} if pos else {})})
            t0 += d
        words[-1]["cue_end"] = True          # an .srt cue is a caption the author chose: never merged with the next
    return words


def ends_sentence(word: str) -> bool:
    return word.rstrip("\"')”’").endswith((".", "?", "!"))


def phrases(words):
    """Split at sentence ends and at pauses: a caption never spans either."""
    runs, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] >= PAUSE_BREAK or ends_sentence(cur[-1]["text"]) or cur[-1].get("cue_end")):
            runs.append(cur)
            cur = []
        cur.append(w)
    if cur:
        runs.append(cur)
    return runs


def chunk_cost(ws, nxt=None):
    chars = len(" ".join(w["text"] for w in ws))
    dur = ws[-1]["end"] - ws[0]["start"]
    if len(ws) > 1 and (chars > MAX_CHARS or dur > MAX_DUR):
        return float("inf")
    cost = 10.0                                   # fewer captions is better
    if len(ws) == 1:
        cost += 15                                # no one-word orphans
    cost += max(0, 24 - chars) * 0.3              # balanced: avoid short stubs
    if dur < MIN_DUR:
        cost += 5
    if not ws[-1]["text"].rstrip("\"')”’").endswith((",", ";", ":", ".", "?", "!")):
        cost += 3                                 # prefer breaking after punctuation
    if ws[-1]["text"].lower() in WEAK_ENDS and nxt is not None:
        cost += 4                                 # don't leave "and", "the", "of" hanging
    if nxt is not None and is_number(ws[-1]["text"], nxt["text"]) and is_unit(nxt["text"]):
        cost += 50                                # never split "3 g" or "two grams" across captions
    return cost


def split_phrase(ws):
    """Best split of one phrase into captions (dynamic programming over break points)."""
    n = len(ws)
    best = [0.0] + [float("inf")] * n
    back = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(max(0, j - 40), j):
            c = best[i] + chunk_cost(ws[i:j], ws[j] if j < n else None)
            if c < best[j]:
                best[j], back[j] = c, i
    out, j = [], n
    while j > 0:
        out.append(ws[back[j]:j])
        j = back[j]
    return out[::-1]


def group(words):
    """Captions of <= MAX_CHARS and <= MAX_DUR, balanced, never across a sentence end or pause."""
    return [c for run in phrases(words) for c in split_phrase(run)]


def split_words(cap, n):
    """Short captions (R5/R6 style): at most n words each, never splitting a number from its unit."""
    out, cur = [], []
    for k, w in enumerate(cap):
        cur.append(w)
        nxt = cap[k + 1]["text"] if k + 1 < len(cap) else ""
        if len(cur) >= n and not (is_number(w["text"], nxt) and is_unit(nxt)):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def fix_timing(caps):
    out = []
    for i, c in enumerate(caps):
        start, end = c[0]["start"], c[-1]["end"]
        nxt = caps[i + 1][0]["start"] if i + 1 < len(caps) else None
        if end - start < MIN_DUR:
            end = start + MIN_DUR
        if nxt is not None:
            if nxt - end <= BRIDGE_GAP:
                end = nxt
            end = min(end, nxt)
        out.append((start, end, c))
    return out


def is_number(tok: str, nxt: str = "") -> bool:
    core = tok.strip(".,!?;:\"'()“”’").lower()
    if NUM_RE.match(core):
        return True
    # a spelled-out number only counts with a unit after it ("two grams", not "one of the")
    return core in NUMBER_WORDS and is_unit(nxt) and nxt.lower().strip(".,") not in {"a", "per"}


def is_unit(tok: str) -> bool:
    return tok.strip(".,!?;:\"'()“”’").lower() in UNITS


def key_span(tokens, keywords):
    """Indices [i, j) of the one word (or number + unit) to colour orange, or None."""
    for i, t in enumerate(tokens):
        if is_number(t, tokens[i + 1] if i + 1 < len(tokens) else ""):
            j = i + 1
            # take a following unit ("3–5 g", "20 grams a day" -> "20 grams")
            if j < len(tokens) and is_unit(tokens[j]) and tokens[j].lower().strip(".,") not in {"a", "per"}:
                j += 1
            return i, j
    # a keyword can be several words ("Vitamin D"), and a transcript may join them with a no-break space
    norm = lambda t: t.replace("\xa0", " ").strip(".,!?;:\"'()“”’").lower()
    for i in range(len(tokens)):
        for n in (3, 2, 1):
            if i + n <= len(tokens) and " ".join(norm(x) for x in tokens[i:i + n]) in keywords:
                return i, i + n
    return None


def wrap(tokens):
    """Balanced 1-2 lines; returns a list of token lists."""
    text = " ".join(tokens)
    if len(text) <= LINE_CHARS or len(tokens) == 1:
        return [tokens]
    best, best_score = None, None
    for k in range(1, len(tokens)):
        a, b = " ".join(tokens[:k]), " ".join(tokens[k:])
        over = max(0, len(a) - LINE_CHARS) + max(0, len(b) - LINE_CHARS)
        pair = is_number(tokens[k - 1], tokens[k]) and is_unit(tokens[k])   # keep "24 gram" on one line
        weak = tokens[k - 1].lower() in WEAK_ENDS
        score = (pair, over, abs(len(a) - len(b)) + 4 * weak)
        if best_score is None or score < best_score:
            best, best_score = k, score
    return [tokens[:best], tokens[best:]]


def ass_escape(s: str) -> str:
    return s.replace("\\", "＼").replace("{", "(").replace("}", ")")


# Gradient captions (owner, 2026-11-26: "gradient colour scheme for overall things"). Subtitles can't fill text with a
# gradient, so each caption is drawn in BANDS horizontal strips (\clip), each in the colour of the ramp at that height:
# together they make a true top-to-bottom gradient, and the shadow, drawn whole in every strip, stays seamless.
BANDS = 6
RAMPS = {"footage": ("#FFFFFF", "#FFFFFF", "#D6E3F2"),          # white to cool ice
         "strong": ("#FFFFFF", "#FFFFFF", "#D6E3F2"),
         "ink": ("#46668C", "#202B38", "#121922")}             # = the ink type gradient


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def ramp_at(stops, k):
    """stops: 3 hex colours at 0, 0.55 and 1; k: 0 top … 1 bottom."""
    a, b, c = (_rgb(x) for x in stops)
    if k < 0.55:
        f, x, y = k / 0.55, a, b
    else:
        f, x, y = (k - 0.55) / 0.45, b, c
    return [round(x[i] + (y[i] - x[i]) * f) for i in range(3)]


def ass_colour(rgb):
    return "&H00%02X%02X%02X&" % (rgb[2], rgb[1], rgb[0])


def key_ramp(acc):
    r = _rgb(acc)
    light = "#%02X%02X%02X" % tuple(round(c + (255 - c) * 0.32) for c in r)
    deep = "#%02X%02X%02X" % tuple(round(c * 0.84) for c in r)
    return (light, acc, deep)


def gradient_events(start, end, style_name, margin_v, text, top, line_h, n_lines, base, key):
    """The caption as strips (\\clip), each in the colour of the ramp at its height. The ramp repeats on every line,
    like the gradient type in the graphics. Each strip is on its own layer at a fixed position: libass would otherwise
    stack same-time captions upward."""
    edges, ks = [0], []
    for j in range(n_lines):
        y0 = top + j * line_h + line_h * 0.12                   # the glyphs, not the line gap
        y1 = top + (j + 1) * line_h - line_h * 0.06
        for i in range(BANDS):
            if i or j:
                edges.append(round(y0 + (y1 - y0) * i / BANDS))   # a new line starts at its own glyph top: descenders above keep their colour
            ks.append((i + 0.5) / BANDS)
    edges.append(1920)
    out = []
    for i, k in enumerate(ks):
        bc, kc = ass_colour(ramp_at(base, k)), ass_colour(ramp_at(key, k))
        t = text.replace(ORANGE, "{\\c" + kc + "}")
        t = re.sub(r"\{\\r\\blur6", lambda m: "{\\r\\blur6\\1c" + bc, t)
        pin = "" if "\\pos(" in t else "\\an2\\pos(540," + str(1920 - margin_v) + ")"
        out.append(f"Dialogue: {i},{start},{end},{style_name},,0,0,{margin_v},,"
                   + "{" + pin + "\\clip(0," + str(edges[i]) + ",1080," + str(edges[i + 1]) + ")\\1c" + bc + "}" + t)
    return out


def render_ass_text(tokens, span, lines=None, fs=62):
    lines = lines or wrap(tokens)
    reset = RESET if fs == 62 else RESET[:-1] + f"\\fs{fs}}}"
    serif = SERIF if fs == 62 else SERIF.replace("\\fs80", f"\\fs{round(fs * 1.3)}")
    out_lines, idx, serif_used = [], 0, False
    for line in lines:
        parts = []
        for t in line:
            word = ass_escape(t)
            if span and idx == span[0]:
                word = ORANGE + word
            if span and idx == span[1] - 1:
                core = word.rstrip(".,!?;:\"')”’")
                word = core + reset + word[len(core):]
            elif not (span and span[0] <= idx < span[1]) and not serif_used and \
                    t.lower().strip(".,!?;:\"'()”’") in SERIF_WORDS:
                core = word.rstrip(".,!?;:\"')”’")
                word = serif + core + reset + word[len(core):]
                serif_used = True
            parts.append(word)
            idx += 1
        out_lines.append(" ".join(parts))
    return (BLUR if fs == 62 else BLUR[:-1] + f"\\fs{fs}}}") + r"\N".join(out_lines)


def ass_time(t: float) -> str:
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def srt_stamp(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def style_header() -> str:
    text = STYLE_FILE.read_text(encoding="utf-8")
    head = text.split("[Events]")[0].rstrip()
    return head + "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, required=True, help="output .ass")
    ap.add_argument("--srt", type=Path, help="also write a plain .srt sidecar")
    ap.add_argument("--keywords", default="", help="comma-separated claim words to highlight when a caption has no number")
    ap.add_argument("--offset", type=float, default=0.0, help="shift every caption by this many seconds")
    ap.add_argument("--flat", action="store_true", help="solid caption colours (default: top-to-bottom brand gradients)")
    ap.add_argument("--style", choices=sorted(STYLES), default=None,
                    help="footage: white words with a soft shadow (default); strong: white with a stronger shadow for busy light-and-dark backgrounds; ink: dark words for light walls and the white stage")
    ap.add_argument("--match", metavar="VIDEO", help="match the caption colours to this video: base white/ink from its caption zone, key-word colour from its own strongest colour (scripts/caption_colors.py)")
    ap.add_argument("--accent", metavar="#RRGGBB", help="key-word colour (overrides --match); default Logo Red: #FC2B16 over footage, #C40205 on light walls")
    ap.add_argument("--position", choices=sorted(POSITIONS) + ["auto"], default="bottom",
                    help="bottom (default, y about 73%%), mic (about 58%%, R6), chest (about 50%%, R5), or auto: the vacant space around the person in the --match video (left, right, above, chest or the bottom band; scripts/layout_plan.py)")
    ap.add_argument("--avoid", default="", metavar="T0-T1:X0,Y0,X1,Y1;...",
                    help="--position auto: areas (1080x1920 pixels) captions must not cover while overlays show; timeline.py fills it in")
    ap.add_argument("--prefer", choices=["left", "right", "top", "chest", "bottom"], default=None,
                    help="with --position auto: favour one slot when it fits, e.g. bottom to use the blur band for captions")
    ap.add_argument("--plan-out", type=Path, metavar="PLAN.json",
                    help="with --position auto: write where each caption went and when the bottom blur band is needed (for bottom_blur.py --plan)")
    ap.add_argument("--max-words", type=int, choices=[1, 2, 3], default=None,
                    help="short captions of 1-3 words on the voice (R5/R6 style); pairs well with --position auto, mic or chest")
    ap.add_argument("--serif-words", default="",
                    help="comma-separated words to set in Instrument Serif Italic in the caption colour (R6 typeface accent, at most one per caption)")
    args = ap.parse_args()

    global ORANGE, SERIF_WORDS
    SERIF_WORDS = {w.strip().lower() for w in args.serif_words.split(",") if w.strip()}
    for flag, val in (("--accent", args.accent),):
        if val and not re.fullmatch(r"#[0-9A-Fa-f]{6}", val):
            sys.exit(f"{flag} must look like #D30204, not {val!r}")
    scheme, person = None, None
    if args.position == "auto" and not args.match:
        sys.exit("--position auto needs --match VIDEO (the video the captions go on).")
    if args.match:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from caption_colors import analyse, is_light_at, is_busy_at, clashes_at
        zone = args.position
        if args.position == "auto":
            from layout_plan import Planner
            avoid = []
            for part in filter(None, args.avoid.split(";")):
                tt, box = part.split(":")
                t0, t1 = (float(v) for v in tt.split("-"))
                avoid.append((t0, t1, *(float(v) for v in box.split(","))))
            person = Planner(args.match, prefer=args.prefer, avoid=avoid)
            if person.person.get("person"):
                zone = (0.30, 0.78)                       # captions can go anywhere around the person
            else:
                print("  note: no person found in the video, so captions use the fixed bottom position.")
                args.position, zone, person = "bottom", "bottom", None
        scheme = analyse(args.match, zone=zone)

    def pick(start, end):
        """(style key, key-word colour) for one caption."""
        if args.style:
            style = args.style
        elif scheme is None:
            style = "footage"
        elif scheme["base"] == "ink":
            style = "ink"
        elif scheme["base"] == "mixed" and is_light_at(scheme, start, end):
            style = "ink"                       # mixed video: follow what is behind this caption
        else:
            style = "strong" if is_busy_at(scheme, start, end) else "footage"
        if args.accent:
            acc = args.accent
        elif scheme and clashes_at(scheme, start, end):
            acc = "#C40205" if style == "ink" else "#FC2B16"     # its own colour is right behind it: use Logo Red
        elif scheme:
            acc = scheme["accent_deep"] if style == "ink" else scheme["accent_bright"]
        else:
            acc = "#C40205" if style == "ink" else "#FC2B16"
        return style, acc.upper()

    keywords = {" ".join(k.replace("\xa0", " ").split()).lower() for k in args.keywords.split(",") if k.strip()}
    words, from_srt = load_words(args.input)
    groups = group(words)
    if args.max_words:
        groups = [c for g in groups for c in split_words(g, args.max_words)]
    caps = fix_timing(groups)

    events, srt_blocks, highlighted = [], [], 0
    own_schemes = {}
    used = {"footage": 0, "ink": 0, "strong": 0}; accents = set(); placed = []
    for n, (start, end, cap) in enumerate(caps, 1):
        tokens = [w["text"] for w in cap]
        span = key_span(tokens, keywords)
        highlighted += bool(span)
        s, e = max(0.0, start + args.offset), max(0.0, end + args.offset)
        own = cap[0].get("pos")
        style, acc = pick(s, e)
        if own and args.match and not args.style:          # colours from the band this cue sits in
            if own not in own_schemes:
                own_schemes[own] = analyse(args.match, zone=own)
            sc = own_schemes[own]
            style = "ink" if sc["base"] == "ink" or (sc["base"] == "mixed" and is_light_at(sc, s, e)) else \
                "strong" if is_busy_at(sc, s, e) else "footage"
            if not args.accent:
                acc = ("#C40205" if style == "ink" else "#FC2B16") if clashes_at(sc, s, e) else \
                    (sc["accent_deep"] if style == "ink" else sc["accent_bright"])
                acc = acc.upper()
        slot = person.place(tokens, s, e) if person and not own else None
        if slot and not args.style:
            # the slot's own background decides the word colour: ink on light, strong shadow on busy
            style = "ink" if slot["light"] else "strong" if slot["busy"] else "footage"
            if not args.accent:
                if scheme and clashes_at(scheme, s, e):
                    acc = "#C40205" if style == "ink" else "#FC2B16"
                elif scheme:
                    acc = scheme["accent_deep"] if style == "ink" else scheme["accent_bright"]
                acc = acc.upper()
        ORANGE = "{\\c&H00" + acc[5:7] + acc[3:5] + acc[1:3] + "&}"
        used[style] += 1
        if span: accents.add(acc)
        margin_v = POSITIONS.get(own or args.position, POSITIONS["bottom"])
        if slot:
            text = "{\\an5\\pos(" + f"{slot['x']},{slot['y']}" + ")}" + render_ass_text(tokens, span, slot["lines"], slot["fs"])
            placed.append(slot)
        else:
            text = render_ass_text(tokens, span)
        if args.flat:
            events.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},{STYLES[style]},,0,0,{margin_v},,{text}")
        else:                                   # the caption's text box, top to bottom, for the gradient strips
            if slot:
                n_lines, fs_ = len(slot["lines"]), slot["fs"]
                top = slot["y"] - n_lines * fs_ * 1.2 / 2
            else:
                n_lines, fs_ = len(wrap(tokens)), 62
                top = 1920 - margin_v - n_lines * fs_ * 1.2
            events += gradient_events(ass_time(s), ass_time(e), STYLES[style], margin_v, text,
                                      top, fs_ * 1.2, n_lines, RAMPS[style], key_ramp(acc))
        srt_blocks.append(f"{n}\n{srt_stamp(s)} --> {srt_stamp(e)}\n" + "\n".join(" ".join(l) for l in wrap(tokens)))

    args.out.write_text(style_header() + "\n".join(events) + "\n", encoding="utf-8")
    if args.srt:
        args.srt.write_text("\n\n".join(srt_blocks) + "\n", encoding="utf-8")

    longest = max((len(" ".join(w["text"] for w in c)) for _, _, c in caps), default=0)
    durs = [e - s for s, e, _ in caps]
    print(f"{len(caps)} captions → {args.out}" + (f" and {args.srt}" if args.srt else ""))
    print(f"  colours: {used['footage']} white, {used['strong']} white with a strong shadow, {used['ink']} ink; key word {', '.join(sorted(accents)) or '-'}"
          + (f" (matched to {Path(args.match).name}: {scheme['source']})" if scheme else ""))
    if placed:
        from collections import Counter
        c = Counter(p["slot"] for p in placed)
        print("  placement: " + ", ".join(f"{k} {v}" for k, v in c.most_common()) + " (vacant space around the person)")
        band = person.band_plan()
        if band["windows"]:
            print(f"  blur band needed: {len(band['windows'])} window(s), " + ", ".join(f"{a:.1f}–{b:.1f} s" for a, b in band["windows"]))
        else:
            print("  blur band: not needed (no caption sits on a busy bottom)")
        if args.plan_out:
            import json
            args.plan_out.write_text(json.dumps({**band, "captions": [{k: p[k] for k in ("slot", "x", "y", "fs", "blur")} for p in placed]}, indent=1))
            print(f"  plan → {args.plan_out} (use: bottom_blur.py in.mp4 out.mp4 --plan {args.plan_out})")
    elif args.plan_out:
        import json
        args.plan_out.write_text(json.dumps({"windows": [], "band_top": None, "captions": []}))
    print(f"  duration {min(durs):.2f}–{max(durs):.2f} s, longest {longest} chars, {highlighted} with a coloured key word")
    if from_srt:
        print("  note: input was sentence-level SRT, so word timing is estimated. Check the sync on a preview.")
    if highlighted < len(caps):
        print(f"  {len(caps) - highlighted} captions have no number or keyword: pass --keywords to highlight claim words.")


if __name__ == "__main__":
    main()
