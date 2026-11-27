#!/usr/bin/env python3
"""
One timeline for the whole edit (SKILL.md §9). An edit.json lists every track; this script checks it
against the White Glass rules, draws it like an editor's timeline, and renders the reel in the right
order with the tested scripts.

    python3 timeline.py check edit.json            # rules + edit.timeline.png (add --motion for gesture moments)
    python3 timeline.py edit edit.json --motion    # edit.editor.html: drag and trim the edit before the final render;
                                                   #   only timing and content change, the style is locked
    python3 timeline.py render edit.json           # build the reel: grade → b-roll → effects → blur → overlays
                                                   #   → captions → end card → SFX → qa.py
    python3 timeline.py export edit.json           # edit.otio + edit.srt: open the edit as a real timeline in
                                                   #   DaVinci Resolve (File > Import > Timeline), Premiere or Kdenlive

edit.json (paths are relative to the file; every track is optional):
{
  "source": "take.mp4",                    the speaker's take (any size; reframed to 1080x1920, 30 fps)
  "out": "final.mp4",
  "grade": true,                           the soft studio grade (footage-editing.md §2)
  "words": "words.json",                   word timings, for captions and b-roll on words
  "broll":    [{"start": 3.2, "end": 5.0, "file": "broll/shelf-pan-01.mp4", "transition": "white"},
               {"start": 8.0, "end": 11.2, "template": "motion-kit.html?scene=wheel&pick=Creatine"}],   a motion-kit beat
  "effects":  [{"effect": "orbit", "start": 6, "end": 9.5, "words": "Whey,Creatine"},
               {"effect": "escape", "start": 1, "end": 4, "matte": "wall"}],
  "overlays": [{"template": "chat-takeover.html?bottom=560", "start": 10}],   "glass": "flat" keeps the old opaque panels; "glass_strength": 0-1 (0 opaque, 0.9 clear default, 1 clear); "glass_lens": 0.12 default, 0.35 = a magnifier
  "captions": {"position": "auto", "keywords": ["protein"], "blur": true},   "max_words": 3 by default with auto
  "sfx":      [{"t": 4.9, "sfx": "thud"}],
  "endcard":  {"template": "reel-9x16.html", "from": 8.15},
  "motion_blur": 4                         sub-frames per frame for rendered graphics (render.cjs --blur); 1 = off
}
Rules checked: no b-roll in the 1.5 s hook; b-roll shots 1-4 s with 1 s of face between; effects need
the speaker (not over b-roll), at least 1.55 s, each kind once; overlays don't overlap; everything
inside the take; and a rhythm note when the picture doesn't change for more than 6 s (no b-roll, effect,
overlay or beat). Needs everything the individual scripts need, plus Pillow (and opentimelineio for export).
"""
import argparse
import numpy as np
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SK = HERE.parent
PY = sys.executable
sys.path.insert(0, str(HERE))
import encode  # noqa: E402  (high-quality encodes: WORK between steps, FINAL for delivery)
GRADE = "eq=brightness=0.02:contrast=0.96:saturation=0.92,colorbalance=rh=-0.01:bh=0.015"
TONEMAP = "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,"
HOOK, MIN_SHOT, MAX_SHOT, MIN_GAP, FX_MIN = 1.5, 1.0, 4.0, 1.0, 1.55
EFFECTS = ("orbit", "escape", "behind", "sticky", "wipe", "pullback", "scatter", "bgswap")   # fx.py (§4 G, H, K)
RHYTHM_GAP = 6.0     # measured: the references change the picture every 1-2.5 s (motion pieces), 4-6 s (talking heads)


def bname(b):
    """A b-roll's display name: the file, or the motion-kit scene it renders."""
    if b.get("template"):
        page, _, q = b["template"].partition("?")
        scene = dict(x.split("=", 1) for x in q.split("&") if "=" in x).get("scene")
        return page.replace(".html", "") + (f":{scene}" if scene else "")
    return Path(b["file"]).name


def die(msg):
    sys.exit(msg)


def run(cmd, what):
    print(f"→ {what}")
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        die(f"{what} failed:\n{(r.stdout + r.stderr)[-2500:]}")
    return r.stdout


def probe(path):
    if not Path(path).is_file():
        die(f"File not found: {path}")
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,color_transfer:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True)
    try:
        info = json.loads(r.stdout)
        dur = float(info["format"]["duration"])
    except (json.JSONDecodeError, KeyError, ValueError):
        die(f"Could not read {path}. Is it a video file?")
    st = info.get("streams", [])
    return {"dur": dur, "audio": any(s.get("codec_type") == "audio" for s in st),
            "hdr": any(s.get("color_transfer") in ("arib-std-b67", "smpte2084") for s in st)}


def page_duration(template):
    """Read window.__duration from a template page (headless), so overlays and the end card can be checked."""
    page, _, query = template.partition("?")
    path = SK / "templates" / page
    if not path.is_file():
        die(f"Template not found: templates/{page}")
    js = ("const {chromium}=require('playwright');(async()=>{const b=await chromium.launch({args:['--allow-file-access-from-files']});"
          "const p=await b.newPage({viewport:{width:1080,height:1920}});"
          f"await p.goto('file://{path}{'?' + query if query else ''}');"
          "await p.waitForFunction(()=>window.__duration,null,{timeout:20000}).catch(()=>{});"
          "console.log(await p.evaluate(()=>window.__duration||0));await b.close();})();")
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True).stdout.strip().splitlines()
    try:
        return float(out[-1])
    except (IndexError, ValueError):
        die(f"Could not read the length of templates/{page}.")


def load(path):
    path = Path(path).resolve()
    try:
        e = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as err:
        die(f"Could not read {path}: {err}")
    if "source" not in e:
        die("edit.json needs a \"source\": the speaker's take.")
    base = path.parent
    e["_base"], e["_path"] = base, path
    e["_src"] = (base / e["source"]).resolve()
    for b in e.get("broll", []):
        if b.get("template"):
            b["_file"] = None                   # rendered by timeline.py render / export
        elif b.get("file"):
            b["_file"] = str((base / b["file"]).resolve())
        else:
            die(f"b-roll at {b.get('start')} s needs a \"file\" or a \"template\" (a motion-kit beat).")
    if e.get("words"):
        e["_words"] = (base / e["words"]).resolve()
    return e


def check(e, motion=False):
    info = probe(e["_src"])
    D = info["dur"]
    issues = []

    def bad(level, msg):
        issues.append((level, msg))

    br = sorted(e.get("broll", []), key=lambda b: b["start"])
    for i, b in enumerate(br):
        tag = f"b-roll {b['start']:.2f}-{b['end']:.2f} ({bname(b)})"
        if b.get("template"):
            b["_dur"] = page_duration(b["template"])
            if b["end"] - b["start"] > b["_dur"] + 0.05:
                bad("WARN", f"{tag}: the beat lasts {b['_dur']:.2f} s, so its last frame holds; shorten the slot or add &hold=")
        elif not Path(b["_file"]).is_file():
            bad("FAIL", f"{tag}: file not found")
        if b["start"] < HOOK:
            bad("FAIL", f"{tag}: inside the {HOOK:g} s hook, which shows the speaker")
        if not MIN_SHOT <= b["end"] - b["start"] <= MAX_SHOT:
            bad("WARN" if b["end"] - b["start"] > MAX_SHOT else "FAIL", f"{tag}: {b['end'] - b['start']:.2f} s (shots are 1-4 s)")
        if b["end"] > D:
            bad("FAIL", f"{tag}: ends after the take ({D:.2f} s)")
        if i and b["start"] - br[i - 1]["end"] < MIN_GAP:
            bad("FAIL", f"{tag}: less than {MIN_GAP:g} s of the speaker after the previous shot")
    share = sum(b["end"] - b["start"] for b in br) / D if D else 0
    if share > 0.45:
        bad("WARN", f"b-roll covers {share:.0%} of the take (keep it under about 45%)")
    seen = {}
    for f in e.get("effects", []):
        tag = f"{f.get('effect')} {f['start']:.2f}-{f['end']:.2f}"
        if f.get("effect") not in EFFECTS:
            bad("FAIL", f"{tag}: effect must be one of {', '.join(EFFECTS)}")
        if f["end"] - f["start"] < FX_MIN or f["end"] > D or f["start"] < 0:
            bad("FAIL", f"{tag}: needs at least {FX_MIN} s inside the take")
        if any(b["start"] < f["end"] and f["start"] < b["end"] for b in br):
            bad("FAIL", f"{tag}: overlaps b-roll; effects follow the speaker, who isn't on screen then")
        if f.get("effect") in ("escape", "bgswap", "behind") and f.get("matte") in (None, "head"):
            bad("FAIL", f"{tag}: needs \"matte\": \"wall\" or a cut-out / matte video")
        if f.get("effect") == "sticky" and not f.get("text"):
            bad("FAIL", f"{tag}: a sticker needs \"text\"")
        if f.get("effect") == "scatter" and len([w for w in str(f.get("words", "")).split(",") if w.strip()]) != 2:
            bad("FAIL", f"{tag}: depth scatter needs two words, e.g. \"words\": \"Label,first\"")
        for key in ("bg", "before", "matte"):
            v = f.get(key)
            if v and v not in ("wall", "head", "stage", "blur") and not (e["_base"] / v).is_file():
                bad("FAIL", f"{tag}: {key} file not found: {v}")
        seen[f.get("effect")] = seen.get(f.get("effect"), 0) + 1
    for k, n in seen.items():
        if n > 1:
            bad("WARN", f"{k} is used {n} times; use each effect at most once per reel")
    ov = []
    for o in e.get("overlays", []):
        d = page_duration(o["template"])
        o["_dur"] = d
        ov.append((o["start"], o["start"] + d, o["template"]))
        if o["start"] + d > D + 0.05:
            bad("WARN", f"overlay {o['template']} runs to {o['start'] + d:.2f} s, past the take ({D:.2f} s); it is cut there")
    ov.sort()
    for a, b in zip(ov, ov[1:]):
        if b[0] < a[1]:
            bad("FAIL", f"overlays overlap: {a[2]} until {a[1]:.2f} s and {b[2]} from {b[0]:.2f} s")
    events = sorted({0.0, D} | {x for b in br for x in (b["start"], b["end"])} | {f["start"] for f in e.get("effects", [])}
                    | {x for a, b, _ in ov for x in (a, min(b, D))})
    for a, b in zip(events, events[1:]):
        if b - a > RHYTHM_GAP:
            bad("WARN", f"{b - a:.1f} s with no new picture ({a:.1f}-{b:.1f} s): add a b-roll, an effect, an overlay or a "
                        "motion-kit beat (the references change the picture every 1-2.5 s; a talking head every 4-6 s)")
    for s in e.get("sfx", []):
        if not 0 <= s["t"] < D:
            bad("FAIL", f"SFX {s.get('sfx')} at {s['t']} s is outside the take")
    if e.get("captions") and not e.get("_words"):
        bad("FAIL", "captions need \"words\": word timings (Whisper, WhisperAI, or a timed transcript)")
    if e.get("endcard"):
        e["endcard"]["_dur"] = page_duration(e["endcard"]["template"]) - float(e["endcard"].get("from", 0))
    moments = []
    if motion:
        r = subprocess.run([PY, HERE / "motion_track.py", e["_src"], "--json", e["_base"] / "motion.json"], capture_output=True, text=True)
        if r.returncode == 0:
            moments = json.loads((e["_base"] / "motion.json").read_text())["moments"]
    png = e["_path"].with_suffix(".timeline.png")
    draw(e, D, br, ov, moments, png)
    return D, info, issues, png


def draw(e, D, br, ov, moments, out):
    from PIL import Image, ImageDraw, ImageFont
    end = e.get("endcard", {}).get("_dur", 0)
    total = D + max(0, end - 0.4)
    W, left, right, row, top = 1800, 210, 40, 74, 92
    rows = ["Speaker", "B-roll", "Effects", "Overlays", "Captions", "SFX", "Moments"]
    H = top + row * len(rows) + 60
    im = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(im)

    def font(size, bold=False):
        for f in (("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf" if bold else "/usr/share/fonts/opentype/inter/Inter-Regular.otf"),
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            if Path(f).is_file():
                return ImageFont.truetype(f, size)
        return ImageFont.load_default()
    f12, f14, f18, f24 = font(13), font(15), font(18, True), font(26, True)
    X = lambda t: left + (W - left - right) * t / total
    ink, slate, mist, ice, orange = "#202B38", "#596879", "#8290A0", "#EAF0F6", "#D30204"
    d.text((24, 22), f"Edit timeline · {Path(e['source']).name} · {total:.1f} s", font=f24, fill=ink)
    for t in range(0, int(total) + 1):
        x = X(t)
        d.line((x, top - 10, x, H - 50), fill="#EEF2F6" if t % 5 else "#DCE3EA", width=1)
        if t % (1 if total <= 20 else 5) == 0:
            d.text((x - 6, H - 44), f"{t}s", font=f12, fill=mist)
    d.rectangle((X(0), top - 14, X(HOOK), top - 8), fill=orange)
    d.text((X(0) + 4, top - 34), "hook: speaker only", font=f12, fill=orange)

    def block(r, a, b, label, fill, fg=ink, outline=None):
        y = top + r * row
        d.rounded_rectangle((X(a), y + 10, max(X(b), X(a) + 4), y + row - 10), 10, fill=fill, outline=outline, width=2)
        if X(b) - X(a) > 40:
            d.text((X(a) + 8, y + row / 2 - 9), label, font=f14, fill=fg)
    for r, name in enumerate(rows):
        y = top + r * row
        d.line((24, y + row, W - right, y + row), fill="#F1F4F8")
        d.text((24, y + row / 2 - 11), name, font=f18, fill=ink)
    block(0, 0, D, Path(e["source"]).name, "#DCE3EA")
    if end:
        block(0, D - 0.4, total, "end card + logo", ice, outline=orange)
    for b in br:
        block(1, b["start"], b["end"], f"{bname(b)} · {b.get('transition', 'cut')}", ice, outline=orange if b.get("template") else "#C9D5E2")
    for f in e.get("effects", []):
        block(2, f["start"], f["end"], f"{f['effect']}" + (f" · {f['words']}" if f.get("words") else ""), orange, fg="#FFFFFF")
    for a, b, tpl in ov:
        block(3, a, min(b, D), tpl.split("?")[0].replace(".html", ""), "#596879", fg="#FFFFFF")
    if e.get("_words") and Path(e["_words"]).is_file():
        sys.path.insert(0, str(HERE))
        from captions import load_words
        words, _ = load_words(Path(e["_words"]))
        y = top + 4 * row
        for w in words:
            if w["start"] < D:
                d.rectangle((X(w["start"]), y + 22, X(min(w["end"], D)), y + row - 22), fill="#C9D5E2")
        cap = e.get("captions", {})
        d.text((X(0) + 6, y + 4), f"captions · {cap.get('position', 'auto')}" + (" · blur band when needed" if cap.get("blur") else ""), font=f12, fill=slate)
    sfx_marks = [(s["t"], s["sfx"]) for s in e.get("sfx", [])] + \
                [(b["start"], "swish") for b in br if b.get("transition") in ("white", "flash")] + \
                [(f["start"] + 0.25, "whoosh") for f in e.get("effects", [])]
    for t, name in sorted(sfx_marks):
        x, y = X(t), top + 5 * row + row / 2
        d.polygon([(x, y - 9), (x + 9, y), (x, y + 9), (x - 9, y)], fill=orange)
        d.text((x + 12, y - 8), name, font=f12, fill=slate)
    for k, m in enumerate(moments):
        x, y = X(m["t"]), top + 6 * row + row / 2 - 8
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=ink if m["type"] == "gesture" else slate)
        d.text((x - 20, y + 8 + 14 * (k % 2)), m["type"].replace("_", " "), font=f12, fill=mist)   # alternate rows so labels don't collide
    im.save(out)


def clean(obj):
    """edit.json without this script's private keys (those starting with _)."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [clean(v) for v in obj]
    return obj


def editor(e, motion=False):
    """A drag-and-drop timeline page for this edit: only timing and content can change, the style can't."""
    import base64
    D, info, issues, png = check(e, motion)
    every = max(0.5, round(D / 40, 2))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(e["_src"]), "-vf", f"fps=1/{every},scale=54:96:force_original_aspect_ratio=increase,crop=54:96",
                          "-c:v", "mjpeg", "-q:v", "6", "-f", "image2pipe", "-"], capture_output=True).stdout
    thumbs = ["data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8" + part).decode() for part in raw.split(b"\xff\xd8")[1:]]
    words = []
    if e.get("_words") and Path(e["_words"]).is_file():
        sys.path.insert(0, str(HERE))
        from captions import load_words
        words = [{"text": w["text"], "start": round(w["start"], 3), "end": round(w["end"], 3)} for w in load_words(Path(e["_words"]))[0]]
    moments = json.loads((e["_base"] / "motion.json").read_text())["moments"] if motion and (e["_base"] / "motion.json").is_file() else []
    lib = sorted({str(p.relative_to(e["_base"])) for p in (e["_base"] / "broll").glob("*")
                  if p.suffix.lower() in (".mp4", ".mov", ".m4v", ".jpg", ".jpeg", ".png", ".webp")} | {b["file"] for b in e.get("broll", []) if b.get("file")})
    sys.path.insert(0, str(HERE))
    from sfx import KIT
    data = {"name": Path(e["source"]).name, "D": round(D, 3), "endcard": round(e.get("endcard", {}).get("_dur", 0), 3),
            "edit": clean({k: v for k, v in e.items()}), "words": words, "moments": moments,
            "thumbs": {"every": every, "images": thumbs}, "library": lib,
            "overlayDur": {o["template"]: round(o["_dur"], 3) for o in e.get("overlays", [])}, "kit": list(KIT),
            "rules": {"hook": HOOK, "minShot": MIN_SHOT, "maxShot": MAX_SHOT, "minGap": MIN_GAP, "fxMin": FX_MIN, "maxShare": 0.45}}
    page = (SK / "templates" / "timeline-editor.html").read_text()
    out = e["_path"].with_suffix(".editor.html")
    out.write_text(page.replace("/*EDIT_DATA*/", json.dumps(data).replace("</", "<\\/")))
    return out, issues


def reframe(e, info, work):
    """The take at 1080x1920, 30 fps, with the soft studio grade (HDR tone-mapped): the base every track sits on."""
    cur = work / "01_graded.mp4"
    sp = encode.probe(e["_src"])
    vf = (TONEMAP if info["hdr"] else "") + encode.scale(1080, 1920, sp["w"], sp["h"]) + ",fps=30," + \
        (GRADE + "," if e.get("grade", True) else "") + "setsar=1"
    run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", e["_src"], "-vf", vf, *encode.WORK,
         *(encode.AUDIO if info["audio"] else []), cur], "reframe and grade")
    return cur


def media(work, kind, key, ext, blur=()):
    """A rendered file named by what made it (template, settings), so an old render is never picked up by mistake."""
    return work / f"{kind}-{hashlib.sha1((key + ' '.join(map(str, blur))).encode()).hexdigest()[:10]}{ext}"


def overlay_box(template, dur, work):
    """Where an overlay sits on screen: the union of its visible pixels in three stills (1080x1920), padded."""
    from PIL import Image
    box = None
    for k, f in enumerate((0.3, 0.6, 0.9)):
        png = media(work, "box", f"{template}@{f}", ".png")
        if not png.is_file():
            run(["node", HERE / "render.cjs", SK / "templates" / template, "--transparent", "--still", str(round(dur * f, 2)), "--out", png],
                f"measure where {template.split('?')[0]} sits")
        a = np.asarray(Image.open(png).convert("RGBA"))[..., 3]
        ys, xs = np.nonzero(a > 12)
        if len(xs):
            b = (xs.min(), ys.min(), xs.max(), ys.max())
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    return box


def render_beat(b, i, work, blur):
    beat = media(work, "beat", b["template"], ".mp4", blur)
    run(["node", HERE / "render.cjs", SK / "templates" / b["template"], "--out", beat, *blur], f"render beat {bname(b)}")
    b["_file"] = str(beat)
    return beat


def export(e, render_media=True):
    """The edit as an OpenTimelineIO timeline: V1 speaker (graded, 1080x1920) then the end card, V2 b-roll and beats,
    V3 overlays (ProRes 4444 with alpha), A1 the voice, A2 the SFX kit placed on every cue, effects as markers,
    captions as an .srt. DaVinci Resolve: File > Import > Timeline (.otio)."""
    try:
        import opentimelineio as otio
    except ImportError:
        die("export needs OpenTimelineIO: pip install opentimelineio")
    D, info, issues, png = check(e)
    for lvl, msg in issues:
        print(f"{lvl}  {msg}")
    work = e["_base"] / "timeline_work"
    work.mkdir(exist_ok=True)
    blur = ["--blur", str(int(e["motion_blur"]))] if int(e.get("motion_blur", 1)) > 1 else []
    R = 30
    RT = lambda t: otio.opentime.RationalTime(round(t * R), R)
    TR = lambda a, d: otio.opentime.TimeRange(RT(a), RT(d))

    def ref(path):
        p = Path(path) if path else None
        if p and p.is_file():
            return otio.schema.ExternalReference(target_url=p.resolve().as_uri(), available_range=TR(0, probe(p)["dur"]))
        return otio.schema.MissingReference()

    def lay(track, items):
        t = 0.0
        for start, dur, clip in sorted(items, key=lambda x: x[0]):
            if start > t + 1e-3:
                track.append(otio.schema.Gap(source_range=TR(0, start - t)))
            track.append(clip)
            t = start + dur

    graded = work / "01_graded.mp4"
    if render_media and not graded.is_file():
        reframe(e, info, work)
    tl = otio.schema.Timeline(name=f"{Path(e['source']).stem} · Nutrition Hub edit")
    v1 = otio.schema.Track(name="V1 Speaker", kind=otio.schema.TrackKind.Video)
    speaker = otio.schema.Clip(name=Path(e["source"]).name, media_reference=ref(graded), source_range=TR(0, D))
    speaker.markers.append(otio.schema.Marker(name="Hook: speaker only", marked_range=TR(0, HOOK), color=otio.schema.MarkerColor.RED))
    for f in e.get("effects", []):
        speaker.markers.append(otio.schema.Marker(name=f"Effect: {f['effect']}" + (f" ({f['words']})" if f.get("words") else ""),
                                                  marked_range=TR(f["start"], f["end"] - f["start"]), color=otio.schema.MarkerColor.RED,
                                                  metadata={"nutrition_hub": {k: v for k, v in f.items() if not k.startswith("_")}}))
    v1.append(speaker)
    ec = e.get("endcard")
    card = media(work, "endcard", f"{ec['template']}@{ec.get('from', 0)}", ".mp4", blur) if ec else None
    if ec:
        if render_media and not card.is_file():
            run(["node", HERE / "render.cjs", SK / "templates" / ec["template"], "--from", str(ec.get("from", 0)), "--out", card, *blur], "render end card")
        v1.append(otio.schema.Clip(name="End card (original logo)", media_reference=ref(card), source_range=TR(0, ec["_dur"])))
    v2 = otio.schema.Track(name="V2 B-roll and beats", kind=otio.schema.TrackKind.Video)
    items = []
    for i, b in enumerate(e.get("broll", [])):
        path = media(work, "beat", b["template"], ".mp4", blur) if b.get("template") else b["_file"]
        if b.get("template") and render_media and not Path(path).is_file():
            render_beat(b, i, work, blur)
        items.append((b["start"], b["end"] - b["start"], otio.schema.Clip(name=bname(b), media_reference=ref(path),
                      source_range=TR(float(b.get("in", 0)), b["end"] - b["start"]), metadata={"nutrition_hub": {"transition": b.get("transition", "cut")}})))
    lay(v2, items)
    v3 = otio.schema.Track(name="V3 Overlays", kind=otio.schema.TrackKind.Video)
    items = []
    for i, o in enumerate(e.get("overlays", [])):
        mov = media(work, "overlay", o["template"], ".mov", blur)
        if render_media and not mov.is_file():
            run(["node", HERE / "render.cjs", SK / "templates" / o["template"], "--transparent", "--out", mov, *blur], f"render overlay {o['template']}")
        items.append((o["start"], min(o["_dur"], D - o["start"]), otio.schema.Clip(name=bname({"template": o["template"]}), media_reference=ref(mov),
                      source_range=TR(0, min(o["_dur"], D - o["start"])))))
    lay(v3, items)
    a1 = otio.schema.Track(name="A1 Voice", kind=otio.schema.TrackKind.Audio)
    a1.append(otio.schema.Clip(name="Voice", media_reference=ref(graded), source_range=TR(0, D)))
    a2 = otio.schema.Track(name="A2 SFX", kind=otio.schema.TrackKind.Audio)
    kit = work / "sfx_kit"
    run([PY, HERE / "sfx.py", "--kit", kit], "export the SFX kit")
    meta = json.loads((kit / "kit.json").read_text())
    cues = [(s["t"], s["sfx"]) for s in e.get("sfx", [])] + [(b["start"], "swish") for b in e.get("broll", []) if b.get("transition") in ("white", "flash")]
    for i, b in enumerate(e.get("broll", [])):
        j = media(work, "beat", b["template"], ".sfx.json", blur) if b.get("template") else None
        if j and j.is_file():
            cues += [(b["start"] + c["t"], c["sfx"]) for c in json.loads(j.read_text())]
    for i, o in enumerate(e.get("overlays", [])):
        j = media(work, "overlay", o["template"], ".sfx.json", blur)
        if j.is_file():
            cues += [(o["start"] + c["t"], c["sfx"]) for c in json.loads(j.read_text())]
    if ec and card.with_suffix(".sfx.json").is_file():
        cues += [(D + c["t"], c["sfx"]) for c in json.loads(card.with_suffix(".sfx.json").read_text())]
    items, last = [], -1.0
    for t, name in sorted(cues):
        m = meta.get(name)
        if not m:
            continue
        wav = kit / m["file"]
        start = max(last, t - m["hit_seconds"])
        dur = probe(wav)["dur"]
        items.append((start, dur, otio.schema.Clip(name=f"{name} ({m['db_under_voice']} dB under voice)", media_reference=ref(wav), source_range=TR(0, dur))))
        last = start + dur
    lay(a2, items)
    tl.tracks.extend([v1, v2, v3, a1, a2])
    out = e["_path"].with_suffix(".otio")
    otio.adapters.write_to_file(tl, str(out))
    srt = None
    if e.get("_words") and Path(e["_words"]).is_file():
        sys.path.insert(0, str(HERE))
        from captions import load_words
        words = load_words(Path(e["_words"]))[0]
        lines, cur = [], []
        for w in words:
            if cur and (w["start"] - cur[-1]["end"] > 0.35 or len(cur) >= 3 or w["end"] - cur[0]["start"] > 1.4):
                lines.append(cur); cur = []
            cur.append(w)
        if cur:
            lines.append(cur)
        ts = lambda t: f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round(t % 1 * 1000)) % 1000:03d}"
        srt = e["_path"].with_suffix(".srt")
        srt.write_text("\n".join(f"{k + 1}\n{ts(l[0]['start'])} --> {ts(l[-1]['end'])}\n{' '.join(w['text'] for w in l)}\n" for k, l in enumerate(lines)))
    return out, srt, issues


def render(e):
    D, info, issues, png = check(e)
    for lvl, msg in issues:
        print(f"{lvl}  {msg}")
    if any(lvl == "FAIL" for lvl, _ in issues):
        die("Fix the FAIL lines in edit.json first.")
    base = e["_base"]
    work = base / "timeline_work"
    work.mkdir(exist_ok=True)
    cur = reframe(e, info, work)
    blur = ["--blur", str(int(e["motion_blur"]))] if int(e.get("motion_blur", 1)) > 1 else []
    cues = []                                   # (file, offset) for sfx.py
    if e.get("broll"):
        for i, b in enumerate(e["broll"]):
            if b.get("template"):               # a motion-kit beat: render it, keep its colours ungraded, keep its sounds
                beat = render_beat(b, i, work, blur)
                if beat.with_suffix(".sfx.json").is_file():
                    cues.append((beat.with_suffix(".sfx.json"), b["start"] - float(b.get("in", 0))))
        spec = work / "broll.json"
        spec.write_text(json.dumps([{k: v for k, v in b.items() if not k.startswith("_") and k != "template"} | {"file": b["_file"]}
                                    | ({"grade": False} if b.get("template") else {}) for b in e["broll"]]))
        nxt = work / "02_broll.mp4"
        run([PY, HERE / "broll.py", cur, nxt, "--spec", spec, "--plan-out", work / "broll_plan.json"], "b-roll cutaways")
        cur = nxt
    for i, f in enumerate(sorted(e.get("effects", []), key=lambda f: f["start"])):
        nxt = work / f"03_fx{i}_{f['effect']}.mp4"
        cmd = [PY, HERE / "fx.py", f["effect"], cur, nxt, "--at", f"{f['start']}-{f['end']}"]
        for k in ("words", "matte", "tilt", "spheres", "radius", "stage", "text", "badge", "anchor", "bg", "before", "mode", "top", "word", "word_at", "color"):
            if k in f:
                v = f[k]
                if k in ("matte", "bg", "before") and v not in ("wall", "head", "stage", "blur"):
                    v = str((base / v).resolve())
                cmd += [f"--{k.replace('_', '-')}", str(v)]
        if f["effect"] == "wipe" and "before" not in f:          # before = the same reframe without the grade
            raw = work / "00_ungraded.mp4"
            if not raw.is_file():
                run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", e["_src"], "-vf",
                     (TONEMAP if info["hdr"] else "") + encode.scale(1080, 1920, *(lambda p: (p["w"], p["h"]))(encode.probe(e["_src"]))) + ",fps=30,setsar=1",
                     *encode.WORK, "-an", raw], "ungraded reframe for before + after")
            cmd += ["--before", raw]
        run(cmd, f"{f['effect']} {f['start']}-{f['end']} s")
        cues.append((nxt.with_suffix(".sfx.json"), 0))
        cur = nxt
    cap = e.get("captions")
    ass = None
    if cap:
        ass = work / "captions.ass"
        cmd = [PY, HERE / "captions.py", e["_words"], "--out", ass, "--match", cur, "--position", cap.get("position", "auto")]
        avoid = []                              # captions never cover an overlay while it shows
        for o in e.get("overlays", []):
            box = overlay_box(o["template"], o["_dur"], work)
            if box:
                avoid.append(f"{o['start']:.2f}-{o['start'] + o['_dur']:.2f}:{box[0]},{box[1]},{box[2]},{box[3]}")
        if avoid and cap.get("position", "auto") == "auto":
            cmd += ["--avoid", ";".join(avoid)]
        mw = cap.get("max_words", 3 if cap.get("position", "auto") == "auto" else None)   # short captions fit beside the head
        if mw:
            cmd += ["--max-words", str(mw)]
        if cap.get("keywords"):
            cmd += ["--keywords", ",".join(cap["keywords"])]
        if cap.get("serif_words"):                 # one white serif accent word per caption (§3), e.g. on a red wall
            cmd += ["--serif-words", ",".join(cap["serif_words"])]
        if cap.get("blur"):
            cmd += ["--plan-out", work / "caption_plan.json"]
        run(cmd, "captions")
        if cap.get("blur"):
            nxt = work / "04_blur.mp4"
            run([PY, HERE / "bottom_blur.py", cur, nxt, "--plan", work / "caption_plan.json"], "bottom blur band (only when needed)")
            cur = nxt
    for i, o in sorted(enumerate(e.get("overlays", [])), key=lambda x: x[1]["start"]):
        tpl, nxt = SK / "templates" / o["template"], work / f"05_overlay{i}.mp4"
        if o.get("glass", "real") == "real":    # real glass: the footage is bent, frosted and lit under each panel (glass.py)
            mov, mask = media(work, "overlay", o["template"], ".glass.mov", blur), media(work, "overlay", o["template"], ".mask.mov", blur)
            run(["node", HERE / "render.cjs", tpl, "--transparent", "--real-glass", "--out", mov, *blur], f"render overlay {o['template']}")
            run(["node", HERE / "render.cjs", tpl, "--transparent", "--glass-mask", "--out", mask, *blur], "render its glass shapes")
            run([PY, HERE / "glass.py", cur, nxt, "--content", mov, "--mask", mask, "--at", str(o["start"]),
                 *(["--strength", str(o["glass_strength"])] if "glass_strength" in o else []),
                 *(["--lens", str(o["glass_lens"])] if "glass_lens" in o else [])], "real glass over the footage")
        else:                                   # "glass": "flat": the near-opaque panels, as rendered
            mov = media(work, "overlay", o["template"], ".mov", blur)
            run(["node", HERE / "render.cjs", tpl, "--transparent", "--out", mov, *blur], f"render overlay {o['template']}")
            run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", cur, "-itsoffset", str(o["start"]), "-i", mov, "-filter_complex",
                 "[0:v][1:v]overlay=0:0:eof_action=pass[v]", "-map", "[v]", "-map", "0:a?", *encode.WORK,
                 "-c:a", "copy", nxt], "composite overlay")
        if mov.with_suffix(".sfx.json").is_file():
            cues.append((mov.with_suffix(".sfx.json"), o["start"]))
        cur = nxt
    if ass:
        nxt = work / "06_captions.mp4"
        esc = str(ass).replace(":", r"\:")
        run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", cur, "-vf", f"ass={esc}:fontsdir={SK / 'assets' / 'fonts'}",
             *encode.WORK, "-c:a", "copy", nxt], "burn captions")
        cur = nxt
    if e.get("endcard"):
        ec = e["endcard"]
        card = media(work, "endcard", f"{ec['template']}@{ec.get('from', 0)}", ".mp4", blur)
        run(["node", HERE / "render.cjs", SK / "templates" / ec["template"], "--from", str(ec.get("from", 0)), "--out", card, *blur], "render end card")
        main_d, X = probe(cur)["dur"], 0.4
        off = round(main_d - X, 3)
        if card.with_suffix(".sfx.json").is_file():
            cues.append((card.with_suffix(".sfx.json"), off))
        card_d = probe(card)["dur"]
        has_a = probe(cur)["audio"]
        nxt = work / "07_endcard.mp4"
        audio_in = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"] if not has_a else []
        a_src = "[2:a]atrim=0:%s," % main_d if not has_a else "[0:a]"
        run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", cur, "-i", card, *audio_in, "-filter_complex",
             f"[0:v]fps=30,format=yuv420p,setsar=1[a];[1:v]fps=30,format=yuv420p,setsar=1[b];"
             f"[a][b]xfade=transition=fadewhite:duration={X}:offset={off}[v];"
             f"{a_src}afade=t=out:st={off}:d={X},apad=pad_dur={round(card_d - X, 3)},aresample=48000[a2]",
             "-map", "[v]", "-map", "[a2]", *encode.WORK, *encode.AUDIO, nxt],
            "append the end card (dip to white)")
        cur = nxt
    out = (base / e.get("out", "final.mp4")).resolve()
    mixed = work / "08_mixed.mp4"
    cmd = [PY, HERE / "sfx.py", cur, mixed]
    for f, o in cues:
        if Path(f).is_file():
            cmd += ["--cues", f"{f}@{o}"]
    if (work / "broll_plan.json").is_file():
        cmd += ["--broll", work / "broll_plan.json"]
    for s in e.get("sfx", []):
        cmd += ["--at", f"{s['t']}={s['sfx']}" + (f"@{s['gain']}" if "gain" in s else "")]
    if len(cmd) > 4:
        run(cmd, "sound effects and loudness")
    elif probe(cur)["audio"]:
        run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", cur, "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-2:LRA=11,alimiter=limit=0.75:attack=1:release=60:level=disabled,aresample=48000",
             *encode.AUDIO, mixed], "loudness")
    else:
        shutil.copy(cur, mixed)
    print("→ maximum-quality delivery encode (x264 High, CRF 2, slower)", flush=True)
    encode.deliver(mixed, out)
    qa = subprocess.run([PY, HERE / "qa.py", out, "--source", e["_src"]], capture_output=True, text=True)
    print(qa.stdout.strip())
    print(f"\nwrote {out}\ntimeline: {png}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["check", "edit", "render", "export"]); ap.add_argument("edit")
    ap.add_argument("--no-render", action="store_true", help="export: don't render missing media (they import offline)")
    ap.add_argument("--motion", action="store_true", help="check: add head and hand moments to the drawing")
    a = ap.parse_args()
    e = load(a.edit)
    if a.action == "check":
        D, info, issues, png = check(e, a.motion)
        print(f"{Path(e['source']).name}: {D:.2f} s take" + (", HDR (will be tone-mapped)" if info["hdr"] else ""))
        for lvl, msg in issues:
            print(f"{lvl}  {msg}")
        print(("no problems found" if not issues else f"{sum(1 for l, _ in issues if l == 'FAIL')} to fix, "
               f"{sum(1 for l, _ in issues if l == 'WARN')} to look at") + f"\ntimeline: {png}")
        sys.exit(1 if any(l == "FAIL" for l, _ in issues) else 0)
    if a.action == "edit":
        out, issues = editor(e, a.motion)
        print(f"timeline editor: {out}\nOpen it in a browser: drag and trim, then Copy edit.json and save it over {e['_path'].name}"
              f" (or paste it back to Claude). {len(issues)} rule note(s) now.")
        return
    if a.action == "export":
        out, srt, issues = export(e, render_media=not a.no_render)
        print(f"timeline: {out}" + (f"\ncaptions: {srt}" if srt else "") +
              "\nDaVinci Resolve: File > Import > Timeline, pick the .otio (media links to timeline_work/). "
              "Effects are markers on V1; render them with timeline.py render.")
        return
    render(e)


if __name__ == "__main__":
    main()
