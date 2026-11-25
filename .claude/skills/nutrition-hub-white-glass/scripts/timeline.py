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

edit.json (paths are relative to the file; every track is optional):
{
  "source": "take.mp4",                    the speaker's take (any size; reframed to 1080x1920, 30 fps)
  "out": "final.mp4",
  "grade": true,                           the soft studio grade (footage-editing.md §2)
  "words": "words.json",                   word timings, for captions and b-roll on words
  "broll":    [{"start": 3.2, "end": 5.0, "file": "broll/shelf-pan-01.mp4", "transition": "white"}],
  "effects":  [{"effect": "orbit", "start": 6, "end": 9.5, "words": "Whey,Creatine"},
               {"effect": "escape", "start": 1, "end": 4, "matte": "wall"}],
  "overlays": [{"template": "chat-takeover.html?bottom=560", "start": 10}],
  "captions": {"position": "auto", "keywords": ["protein"], "blur": true},
  "sfx":      [{"t": 4.9, "sfx": "thud"}],
  "endcard":  {"template": "reel-9x16.html", "from": 8.15}
}
Rules checked: no b-roll in the 1.5 s hook; b-roll shots 1-4 s with 1 s of face between; effects need
the speaker (not over b-roll), at least 1.55 s, each kind once; overlays don't overlap; everything
inside the take. Needs everything the individual scripts need, plus Pillow.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SK = HERE.parent
PY = sys.executable
GRADE = "eq=brightness=0.02:contrast=0.96:saturation=0.92,colorbalance=rh=-0.01:bh=0.015"
TONEMAP = "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,"
HOOK, MIN_SHOT, MAX_SHOT, MIN_GAP, FX_MIN = 1.5, 1.0, 4.0, 1.0, 1.55


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
        b["_file"] = str((base / b["file"]).resolve())
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
        tag = f"b-roll {b['start']:.2f}-{b['end']:.2f} ({Path(b['file']).name})"
        if not Path(b["_file"]).is_file():
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
        if f.get("effect") not in ("orbit", "escape"):
            bad("FAIL", f"{tag}: effect must be orbit or escape")
        if f["end"] - f["start"] < FX_MIN or f["end"] > D or f["start"] < 0:
            bad("FAIL", f"{tag}: needs at least {FX_MIN} s inside the take")
        if any(b["start"] < f["end"] and f["start"] < b["end"] for b in br):
            bad("FAIL", f"{tag}: overlaps b-roll; effects follow the speaker, who isn't on screen then")
        if f.get("effect") == "escape" and not f.get("matte"):
            bad("FAIL", f"{tag}: the frame escape needs \"matte\": \"wall\" or a matte video")
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
    ink, slate, mist, ice, orange = "#202B38", "#596879", "#8290A0", "#EAF0F6", "#F0782B"
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
        block(1, b["start"], b["end"], f"{Path(b['file']).stem} · {b.get('transition', 'cut')}", ice, outline="#C9D5E2")
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
                  if p.suffix.lower() in (".mp4", ".mov", ".m4v", ".jpg", ".jpeg", ".png", ".webp")} | {b["file"] for b in e.get("broll", [])})
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


def render(e):
    D, info, issues, png = check(e)
    for lvl, msg in issues:
        print(f"{lvl}  {msg}")
    if any(lvl == "FAIL" for lvl, _ in issues):
        die("Fix the FAIL lines in edit.json first.")
    base = e["_base"]
    work = base / "timeline_work"
    work.mkdir(exist_ok=True)
    cur = work / "01_graded.mp4"
    vf = (TONEMAP if info["hdr"] else "") + "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30," + \
        (GRADE + "," if e.get("grade", True) else "") + "setsar=1"
    run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", e["_src"], "-vf", vf, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
         *(["-c:a", "aac", "-b:a", "192k"] if info["audio"] else []), cur], "reframe and grade")
    cues = []                                   # (file, offset) for sfx.py
    if e.get("broll"):
        spec = work / "broll.json"
        spec.write_text(json.dumps([{k: v for k, v in b.items() if not k.startswith("_")} | {"file": b["_file"]} for b in e["broll"]]))
        nxt = work / "02_broll.mp4"
        run([PY, HERE / "broll.py", cur, nxt, "--spec", spec, "--plan-out", work / "broll_plan.json"], "b-roll cutaways")
        cur = nxt
    for i, f in enumerate(sorted(e.get("effects", []), key=lambda f: f["start"])):
        nxt = work / f"03_fx{i}_{f['effect']}.mp4"
        cmd = [PY, HERE / "fx.py", f["effect"], cur, nxt, "--at", f"{f['start']}-{f['end']}"]
        for k in ("words", "matte", "tilt", "spheres", "radius", "stage"):
            if k in f:
                cmd += [f"--{k}", f[k] if k != "matte" or f[k] in ("wall", "head") else str((base / f[k]).resolve())]
        run(cmd, f"{f['effect']} {f['start']}-{f['end']} s")
        cues.append((nxt.with_suffix(".sfx.json"), 0))
        cur = nxt
    cap = e.get("captions")
    ass = None
    if cap:
        ass = work / "captions.ass"
        cmd = [PY, HERE / "captions.py", e["_words"], "--out", ass, "--match", cur, "--position", cap.get("position", "auto")]
        if cap.get("keywords"):
            cmd += ["--keywords", ",".join(cap["keywords"])]
        if cap.get("blur"):
            cmd += ["--plan-out", work / "caption_plan.json"]
        run(cmd, "captions")
        if cap.get("blur"):
            nxt = work / "04_blur.mp4"
            run([PY, HERE / "bottom_blur.py", cur, nxt, "--plan", work / "caption_plan.json"], "bottom blur band (only when needed)")
            cur = nxt
    if e.get("overlays"):
        nxt = work / "05_overlays.mp4"
        inputs, chain, last = ["-i", cur], [], "0:v"
        for i, o in enumerate(e["overlays"]):
            mov = work / f"overlay{i}.mov"
            run(["node", HERE / "render.cjs", SK / "templates" / o["template"], "--transparent", "--out", mov], f"render overlay {o['template']}")
            if mov.with_suffix(".sfx.json").is_file():
                cues.append((mov.with_suffix(".sfx.json"), o["start"]))
            inputs += ["-itsoffset", str(o["start"]), "-i", mov]
            chain.append(f"[{last}][{i + 1}:v]overlay=0:0:eof_action=pass[o{i}]")
            last = f"o{i}"
        run(["ffmpeg", "-y", "-v", "error", "-nostdin", *inputs, "-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "0:a?",
             "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", nxt], "composite overlays")
        cur = nxt
    if ass:
        nxt = work / "06_captions.mp4"
        esc = str(ass).replace(":", r"\:")
        run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", cur, "-vf", f"ass={esc}:fontsdir={SK / 'assets' / 'fonts'}",
             "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", nxt], "burn captions")
        cur = nxt
    if e.get("endcard"):
        ec = e["endcard"]
        card = work / "endcard.mp4"
        run(["node", HERE / "render.cjs", SK / "templates" / ec["template"], "--from", str(ec.get("from", 0)), "--out", card], "render end card")
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
             "-map", "[v]", "-map", "[a2]", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", nxt],
            "append the end card (dip to white)")
        cur = nxt
    out = (base / e.get("out", "final.mp4")).resolve()
    cmd = [PY, HERE / "sfx.py", cur, out]
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
        run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", cur, "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-2:LRA=11,aresample=48000",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], "loudness")
    else:
        shutil.copy(cur, out)
    qa = subprocess.run([PY, HERE / "qa.py", out], capture_output=True, text=True)
    print(qa.stdout.strip())
    print(f"\nwrote {out}\ntimeline: {png}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["check", "edit", "render"]); ap.add_argument("edit")
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
    render(e)


if __name__ == "__main__":
    main()
