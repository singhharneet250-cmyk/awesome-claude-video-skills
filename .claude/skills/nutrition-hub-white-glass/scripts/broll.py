#!/usr/bin/env python3
"""
B-roll cutaways over a talking head (A-roll). The voice keeps running; only the picture cuts
away to the b-roll and back (SKILL.md section 4 F, reference/footage-editing.md §2b).

    # at set times: START-END=FILE, optionally @IN (where to start inside the b-roll file)
    python3 broll.py graded.mp4 out.mp4 --at 3.2-5.0=broll/shelf-pan-01.mp4 --at 9-11.4=broll/scoop-01.mp4@2.5

    # when a word is spoken: the b-roll starts on that word (word timings from Whisper etc.)
    python3 broll.py graded.mp4 out.mp4 --words words.json --map label=broll/label-closeup-01.mp4 --map scoop=broll/scoop-01.mp4

    # a spec file: [{"start", "end", "file", "in", "speed", "x", "y", "grade", "transition"}, ...]
    python3 broll.py graded.mp4 out.mp4 --spec broll.json

Options:
  --transition cut|white|soft   cut (default); white = 0.4 s dip to porcelain white into the b-roll
                                and back (R5); soft = 0.25 s dissolve. A spec entry can set its own.
  --len 2.2                     keyword mode: shot length in seconds (cut back at the nearest pause)
  --lead 0.1                    keyword mode: start this long before the word
  --hold-start 1.5              keep the face on screen for the hook (no b-roll before this)
  --plan-out plan.json          write the final placements; --dry-run prints them without rendering

Each b-roll is filled to the A-roll's frame (scale and centre-crop; "x"/"y" 0-1 move the crop),
conformed to its frame rate, and given the same soft studio grade as the footage. Stills
(.png .jpg .webp) get a slow 4% push-in; a cut-out PNG with transparency sits on an ice-mist
stage instead of being cropped. Stills are NOT graded, so label colours stay accurate; set
"grade": false for label close-up videos too. "speed": 0.5 plays a 60 fps clip in slow motion.
HDR phone clips (HLG/PQ) are tone-mapped to SDR.

Rules it enforces (SKILL.md §4 F): shots 1-4 s, at least 1 s of face between shots, no b-roll
in the hook, b-roll at most about 45% of the runtime (warning). Audio is copied unchanged.
Needs ffmpeg with zscale (for HDR clips only).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

GRADE = "eq=brightness=0.02:contrast=0.96:saturation=0.92,colorbalance=rh=-0.01:bh=0.015"
TONEMAP = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
           "zscale=t=bt709:m=bt709:r=tv")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
ICE_MIST = "0xEAF0F6"
MIN_SHOT, MAX_SHOT, MIN_GAP = 1.0, 4.0, 1.0
WHITE_DIP, SOFT_DIP = 0.4, 0.25
PUSH = 0.04          # stills: 4% slow push over the shot (not a zoom punch, §5)
MAX_SHARE = 0.45


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path, need_video=True):
    if not Path(path).is_file():
        sys.exit(f"File not found: {path}")
    r = run(["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type,width,height,r_frame_rate,color_transfer,pix_fmt:format=duration",
             "-of", "json", str(path)])
    try:
        info = json.loads(r.stdout)
    except json.JSONDecodeError:
        sys.exit(f"Could not read {path}. Is it a video or image file?")
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    if v is None and need_video:
        sys.exit(f"{path} has no picture.")
    num, _, den = (v.get("r_frame_rate") or "30/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    dur = info.get("format", {}).get("duration")
    return {"w": int(v["width"]), "h": int(v["height"]), "fps": fps, "rate": v.get("r_frame_rate") or "30/1",
            "dur": float(dur) if dur not in (None, "N/A") else None,
            "hdr": v.get("color_transfer") in ("arib-std-b67", "smpte2084"),
            "alpha": Path(path).suffix.lower() in IMAGE_EXT and has_alpha(path),
            "audio": any(s.get("codec_type") == "audio" for s in streams)}


def has_alpha(path):
    """True for a cut-out still: some pixels are see-through."""
    from PIL import Image
    with Image.open(path) as im:
        if im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info:
            return im.convert("RGBA").getchannel("A").getextrema()[0] < 250
    return False


def parse_at(text):
    m = re.fullmatch(r"\s*([\d.]+)\s*-\s*([\d.]+)\s*=\s*(.+?)(?:@([\d.]+))?\s*", text)
    if not m:
        sys.exit(f"--at {text!r}: write it as START-END=FILE or START-END=FILE@IN, e.g. 3.2-5.0=shelf.mp4@1.5")
    s, e, f, i = m.groups()
    return {"start": float(s), "end": float(e), "file": f, "in": float(i or 0)}


def norm(word):
    w = re.sub(r"[^\w%]+", "", word.lower().replace("’", "'").split("'")[0])
    return w


def keyword_cuts(words, mapping, length, lead):
    """One cut per spoken occurrence of a mapped word, in order; each file is used once."""
    queues = {k: list(v) for k, v in mapping.items()}
    cuts = []
    for n, w in enumerate(words):
        t = norm(w["text"])
        key = next((k for k in queues if queues[k] and (t == k or t in (k + "s", k + "es"))), None)
        if key is None:
            continue
        start = max(0.0, w["start"] - lead)
        # cut back at a pause between words, as close as possible to start + length
        target, best = start + length, None
        for a, b in zip(words[n:], words[n + 1:]):
            gap_mid = (a["end"] + b["start"]) / 2
            if gap_mid - start < MIN_SHOT * 1.5:
                continue
            if gap_mid - start > MAX_SHOT:
                break
            score = abs(gap_mid - target) - 0.6 * min(b["start"] - a["end"], 0.5)   # prefer real pauses
            if best is None or score < best[0]:
                best = (score, gap_mid)
        end = best[1] if best else start + length
        cuts.append({"start": round(start, 3), "end": round(end, 3), "file": queues[key].pop(0), "in": 0.0,
                     "why": f"'{w['text']}' at {w['start']:.2f} s"})
    return cuts


def plan(cuts, dur, hold_start, strict):
    """Apply the timing rules. Explicit cuts that break a hard rule stop the run; keyword cuts are skipped."""
    out, notes = [], []

    def bad(msg):
        if strict:
            sys.exit(msg)
        notes.append("skipped: " + msg)

    for c in sorted(cuts, key=lambda c: c["start"]):
        label = f"{c['start']:.2f}-{c['end']:.2f} {Path(c['file']).name}"
        if c["end"] <= c["start"]:
            bad(f"{label}: the end must come after the start."); continue
        if c["start"] < hold_start:
            if c["end"] - hold_start >= MIN_SHOT:
                notes.append(f"{label}: moved the start to {hold_start:.2f} s, so the hook shows the face")
                c["start"] = hold_start
            else:
                bad(f"{label}: falls in the hook (first {hold_start:g} s), which keeps the face on screen."); continue
        if c["end"] > dur:
            notes.append(f"{label}: trimmed to the end of the video ({dur:.2f} s)")
            c["end"] = dur
        if c["end"] - c["start"] < MIN_SHOT:
            bad(f"{label}: shorter than {MIN_SHOT:g} s, too short to read."); continue
        if c["end"] - c["start"] > MAX_SHOT:
            notes.append(f"{label}: longer than {MAX_SHOT:g} s; split it or go back to the face sooner")
        if out and c["start"] < out[-1]["end"] + MIN_GAP:
            bad(f"{label}: starts {c['start'] - out[-1]['end']:.2f} s after the previous b-roll; "
                f"leave at least {MIN_GAP:g} s of face between shots."); continue
        out.append(c)
    share = sum(c["end"] - c["start"] for c in out) / dur if dur else 0
    if share > MAX_SHARE:
        notes.append(f"b-roll covers {share:.0%} of the video; keep it under about {MAX_SHARE:.0%} so the speaker still leads")
    return out, notes


def broll_chain(k, c, src, W, H, fps, transition, src_fps):
    """Filter chain for input k: fill W x H, conform, grade, shift to its start time."""
    d = c["end"] - c["start"]
    speed = float(c.get("speed", 1.0))
    x, y = float(c.get("x", 0.5)), float(c.get("y", 0.5))
    still = Path(c["file"]).suffix.lower() in IMAGE_EXT
    grade = c.get("grade", not still)
    f = []
    if src["hdr"]:
        f.append(TONEMAP)
    if still:
        if src["alpha"]:   # cut-out: contain it on an ice-mist stage instead of cropping it
            f.append(f"scale={round(W * 0.78)}:{round(H * 0.62)}:force_original_aspect_ratio=decrease:flags=lanczos,format=rgba[p{k}];"
                     f"color=c={ICE_MIST}:s={W}x{H}:r={fps}:d={d + 1}[s{k}];"
                     f"[s{k}][p{k}]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:shortest=1")
        else:
            f.append(f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}:(iw-{W})*{x}:(ih-{H})*{y}")
        # slow push-in with sub-pixel sampling (zoompan rounds to whole pixels and judders)
        z = f"(2*(1+{PUSH}*on/{max(2, round(d * src_fps))}))"
        f.append(f"perspective=x0='W/2-W/{z}':y0='H/2-H/{z}':x1='W/2+W/{z}':y1='H/2-H/{z}':"
                 f"x2='W/2-W/{z}':y2='H/2+H/{z}':x3='W/2+W/{z}':y3='H/2+H/{z}':interpolation=cubic:eval=frame")
    else:
        f.append(f"setpts=(PTS-STARTPTS)/{speed}")
        f.append(f"fps={fps}")
        f.append(f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}:(iw-{W})*{x}:(ih-{H})*{y}")
    if grade:
        f.append(GRADE)
    f.append(f"setsar=1,trim=duration={d:.3f},setpts=PTS-STARTPTS")
    if transition == "soft":
        x_ = min(SOFT_DIP, d / 4)
        f.append(f"format=yuva420p,fade=t=in:st=0:d={x_}:alpha=1,fade=t=out:st={d - x_:.3f}:d={x_}:alpha=1")
    else:
        f.append("format=yuv420p")
    f.append(f"setpts=PTS+{c['start']:.3f}/TB")
    return f"[{k}:v]" + ",".join(f) + f"[b{k}]"


def build(aroll, out, cuts, default_transition, crf):
    A = probe(aroll)
    W, H, fps = A["w"] - A["w"] % 2, A["h"] - A["h"] % 2, A["rate"]   # exact rate, e.g. 30000/1001
    inputs = ["-i", str(aroll)]
    graph = [f"[0:v]fps={fps},format=yuv420p,setsar=1[v0]"]
    last, dips = "v0", []
    for k, c in enumerate(cuts, start=1):
        src = c["_probe"]
        d = c["end"] - c["start"]
        if Path(c["file"]).suffix.lower() in IMAGE_EXT:
            inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{d + 0.5:.3f}", "-i", c["file"]]
        else:
            inputs += ["-ss", f"{c.get('in', 0):.3f}", "-t", f"{d * float(c.get('speed', 1.0)) + 0.5:.3f}", "-i", c["file"]]
        t = c.get("transition", default_transition)
        graph.append(broll_chain(k, c, src, W, H, fps, t, A["fps"]))
        graph.append(f"[{last}][b{k}]overlay=0:0:eof_action=pass:enable='between(t,{c['start']:.3f},{c['end'] - 0.001:.3f})'[v{k}]")
        last = f"v{k}"
        if t == "white":
            dips += [c["start"], c["end"]]
    for j, at in enumerate(dips):   # dip to porcelain white, peaking on the cut
        h = WHITE_DIP / 2
        s = max(0.0, at - h)
        graph.append(f"color=c=white:s={W}x{H}:r={fps}:d={WHITE_DIP},format=yuva420p,"
                     f"fade=t=in:st=0:d={h}:alpha=1,fade=t=out:st={h}:d={h}:alpha=1,"
                     f"setpts=PTS+{s:.3f}/TB[w{j}]")
        graph.append(f"[{last}][w{j}]overlay=0:0:eof_action=pass:enable='between(t,{s:.3f},{at + h:.3f})'[d{j}]")
        last = f"d{j}"
    cmd = ["ffmpeg", "-y", "-nostdin", "-v", "error", *inputs, "-filter_complex", ";".join(graph),
           "-map", f"[{last}]", "-map", "0:a?", "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
           "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "copy", "-t", f"{A['dur']:.3f}", "-movflags", "+faststart", str(out)]
    r = run(cmd)
    if r.returncode:
        sys.exit("ffmpeg failed:\n" + r.stderr[-2000:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("aroll"); ap.add_argument("out")
    ap.add_argument("--at", action="append", default=[], metavar="START-END=FILE[@IN]")
    ap.add_argument("--spec")
    ap.add_argument("--words"); ap.add_argument("--map", action="append", default=[], metavar="WORD=FILE")
    ap.add_argument("--len", type=float, default=2.2); ap.add_argument("--lead", type=float, default=0.1)
    ap.add_argument("--transition", choices=["cut", "white", "flash", "soft"], default="cut")
    ap.add_argument("--hold-start", type=float, default=1.5)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--plan-out"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    transition = "white" if a.transition == "flash" else a.transition

    A = probe(a.aroll)
    if not A["dur"]:
        sys.exit(f"Could not read the length of {a.aroll}.")
    cuts = [parse_at(t) for t in a.at]
    if a.spec:
        try:
            spec = json.loads(Path(a.spec).read_text())
        except (OSError, json.JSONDecodeError) as e:
            sys.exit(f"Could not read the spec {a.spec}: {e}")
        spec = spec.get("cuts", spec) if isinstance(spec, dict) else spec
        for n, c in enumerate(spec, 1):
            if not all(k in c for k in ("start", "end", "file")):
                sys.exit(f"Spec entry {n} needs start, end and file: {c}")
            if c.get("transition") == "flash":
                c["transition"] = "white"
            cuts.append(dict(c))
    if a.map:
        if not a.words:
            sys.exit("--map needs --words (word timings), so it knows when each word is spoken.")
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from captions import load_words
        words, from_srt = load_words(Path(a.words))
        if from_srt:
            print("note: .srt timings are estimated per word, so check that each b-roll lands on its word")
        mapping = {}
        for m in a.map:
            key, sep, f = m.partition("=")
            if not sep or not key.strip() or not f.strip():
                sys.exit(f"--map {m!r}: write it as WORD=FILE, e.g. label=broll/label-closeup-01.mp4")
            mapping.setdefault(norm(key), []).append(f.strip())
        found = keyword_cuts(words, mapping, a.len, a.lead)
        unused = [f"{k} ({len(v)} file{'s' if len(v) > 1 else ''})" for k, v in mapping.items()
                  if len(v) > sum(1 for c in found if c["file"] in v)]
        if unused:
            print("not spoken (or spoken fewer times than files given): " + ", ".join(unused))
        cuts += found
    if not cuts:
        sys.exit("No b-roll to place. Give --at, --spec, or --words with --map.")
    for c in cuts:
        if Path(c["file"]).suffix.lower() in (".heic", ".heif"):
            sys.exit(f"{c['file']}: convert HEIC photos to JPG or PNG first.")
        c["_probe"] = probe(c["file"])
    notes = []
    for c in cuts:   # the b-roll file must be long enough after its in-point
        src, still = c["_probe"], Path(c["file"]).suffix.lower() in IMAGE_EXT
        if not still and src["dur"]:
            avail = (src["dur"] - c.get("in", 0)) / float(c.get("speed", 1.0))
            if avail < c["end"] - c["start"]:
                if avail < MIN_SHOT:
                    sys.exit(f"{c['file']}: only {avail:.2f} s left after the in-point {c.get('in', 0):g} s.")
                notes.append(f"{Path(c['file']).name}: only {avail:.2f} s available, shot ends at {c['start'] + avail:.2f} s")
                c["end"] = round(c["start"] + avail, 3)
    explicit = [c for c in cuts if "why" not in c]
    keyword = [c for c in cuts if "why" in c]
    placed, more = plan(explicit + keyword, A["dur"], a.hold_start, strict=bool(explicit) and not keyword)
    notes += more
    for c in placed:
        if c["_probe"]["hdr"]:
            notes.append(f"{Path(c['file']).name}: HDR clip, tone-mapped to SDR (film with HDR video off next time)")
    for n in notes:
        print("note: " + n)
    print(f"{len(placed)} b-roll shot{'s' if len(placed) != 1 else ''} over {Path(a.aroll).name} ({A['dur']:.2f} s):")
    for c in placed:
        t = c.get("transition", transition)
        extra = f", in {c.get('in', 0):g} s" if c.get("in") else ""
        extra += f", speed {c['speed']}" if c.get("speed", 1) != 1 else ""
        print(f"  {c['start']:6.2f}-{c['end']:6.2f}  {Path(c['file']).name}  ({t}{extra}){'  ' + c['why'] if 'why' in c else ''}")
    if a.plan_out:
        Path(a.plan_out).write_text(json.dumps([{k: v for k, v in c.items() if not k.startswith("_")} for c in placed], indent=2))
    if a.dry_run or not placed:
        return
    build(a.aroll, a.out, placed, transition, a.crf)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
