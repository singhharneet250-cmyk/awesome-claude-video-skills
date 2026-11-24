#!/usr/bin/env python3
"""
White Glass captions: word timings -> libass captions (and an optional .srt sidecar).

    python3 captions.py words.json --out captions.ass
    python3 captions.py words.json --out captions.ass --srt captions.srt --keywords creatine,protein
    python3 captions.py cues.srt   --out captions.ass            # sentence-level cues (less exact)

Then burn in:
    ffmpeg -i in.mp4 -vf "ass=captions.ass:fontsdir=/usr/share/fonts/opentype/inter" -c:a copy out.mp4

Input (any of):
  - Whisper / faster-whisper JSON with word timestamps: {"segments": [{"words": [{"word", "start", "end"}]}]}
  - a flat list of words: [{"word" or "text", "start", "end"}] in seconds
  - Remotion captions: [{"text", "startMs", "endMs"}]
  - an .srt file (sentence-level; words are spread over each cue by length, so check the sync)

Rules applied (SKILL.md section 6):
  - at most 2 lines, about 28 characters per line
  - each caption on screen 1-3 s; a new caption starts at a pause or a sentence end
  - one key word per caption goes signal orange: a number with its unit first, then a word from
    --keywords; if neither is present the caption stays ink (never a random word)
  - graphite ink on an opaque white box, style copied from reference/captions.ass
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
STYLE_FILE = SKILL / "reference" / "captions.ass"

ORANGE = r"{\c&H2B78F0&}"
INK = r"{\c&H382B20&}"

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
        if not tokens:
            continue
        total = sum(len(t) + 1 for t in tokens)
        t0 = start
        for tok in tokens:
            d = (end - start) * (len(tok) + 1) / total
            words.append({"text": tok, "start": t0, "end": t0 + d})
            t0 += d
    return words


def ends_sentence(word: str) -> bool:
    return word.rstrip("\"')”’").endswith((".", "?", "!"))


def phrases(words):
    """Split at sentence ends and at pauses: a caption never spans either."""
    runs, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] >= PAUSE_BREAK or ends_sentence(cur[-1]["text"])):
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
    for i, t in enumerate(tokens):
        if t.strip(".,!?;:\"'()“”’").lower() in keywords:
            return i, i + 1
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


def render_ass_text(tokens, span):
    lines = wrap(tokens)
    out_lines, idx = [], 0
    for line in lines:
        parts = []
        for t in line:
            word = ass_escape(t)
            if span and idx == span[0]:
                word = ORANGE + word
            if span and idx == span[1] - 1:
                core = word.rstrip(".,!?;:\"')”’")
                word = core + INK + word[len(core):]
            parts.append(word)
            idx += 1
        out_lines.append(" ".join(parts))
    return r"\N".join(out_lines)


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
    args = ap.parse_args()

    keywords = {k.strip().lower() for k in args.keywords.split(",") if k.strip()}
    words, from_srt = load_words(args.input)
    caps = fix_timing(group(words))

    events, srt_blocks, highlighted = [], [], 0
    for n, (start, end, cap) in enumerate(caps, 1):
        tokens = [w["text"] for w in cap]
        span = key_span(tokens, keywords)
        highlighted += bool(span)
        s, e = max(0.0, start + args.offset), max(0.0, end + args.offset)
        events.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},NH-Caption,,0,0,0,,{render_ass_text(tokens, span)}")
        srt_blocks.append(f"{n}\n{srt_stamp(s)} --> {srt_stamp(e)}\n" + "\n".join(" ".join(l) for l in wrap(tokens)))

    args.out.write_text(style_header() + "\n".join(events) + "\n", encoding="utf-8")
    if args.srt:
        args.srt.write_text("\n\n".join(srt_blocks) + "\n", encoding="utf-8")

    longest = max((len(" ".join(w["text"] for w in c)) for _, _, c in caps), default=0)
    durs = [e - s for s, e, _ in caps]
    print(f"{len(caps)} captions → {args.out}" + (f" and {args.srt}" if args.srt else ""))
    print(f"  duration {min(durs):.2f}–{max(durs):.2f} s, longest {longest} chars, {highlighted} with an orange key word")
    if from_srt:
        print("  note: input was sentence-level SRT, so word timing is estimated. Check the sync on a preview.")
    if highlighted < len(caps):
        print(f"  {len(caps) - highlighted} captions have no number or keyword: pass --keywords to highlight claim words.")


if __name__ == "__main__":
    main()
