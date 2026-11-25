---
name: nutrition-hub-white-glass
description: Brand and motion system for Nutrition Hub Khanna (the "White Glass Motion System"). Use for EVERY video edit or video graphic made for Nutrition Hub, whatever the tool (ffmpeg, HTML/Playwright, HyperFrames, Remotion, IT Reelsmaker, Motion Reel, CapCut, ManyMotions, Clipzi, OpusClip, Picsart and so on). That includes reels, shorts, product films, supplement explainers, captions, title cards, data callouts, lower thirds, thumbnails and end cards. Holds the original logo file (always use it, never redraw it), the palette, type, glass components, motion timings, caption style, footage grade, a tested render pipeline, realistic 3D molecule and product-hero templates, a caption generator, an automated delivery QA, and which companion skill or plugin to use for each job (this skill wins wherever they disagree).
---

# Nutrition Hub Khanna: White Glass Motion System

A premium, science-led visual language for supplement education, product films and
high-retention fitness reels. **Clarity first. Depth second. Accent with intent.**
White-on-white layers, translucent surfaces, restrained orange highlights and precise
3D graphics. Keep every frame clean, legible and editorial.

`reference/playbook.png` is the source playbook. Look at it when in doubt. Everything
marked *(derived)* below adapts the playbook to video. Unmarked values come straight from it.

## 1. Logo: always the original file

- **File:** `assets/logo/nutrition-hub-logo.png`. This is the original Nutrition Hub logo
  as supplied by the owner: a 1508×1043 transparent PNG with a 3D gold and red
  "NUTRITION HUB" wordmark and "KHANNA" underneath.
  - sha256 `1ceaeb7a9ca284fa859de4009237dc52d1827656518150a81f4de6922c20e28d`.
    Check it with `sha256sum` before you deliver.
- **Use only this file.** Never redraw, trace, vectorise, re-type, recolour, restyle,
  crop, stretch, rotate or "glass-ify" it, and never add a glow, stroke, shadow or outline.
  Its glow and shadow are already baked in. Never generate a logo with AI, and never
  screen-grab one from another image.
- The orange rounded-square "A" icon in `playbook.png` is **not** the logo. Never use it.
- If the file is missing or won't load, **stop and ask the user for the original.** Don't
  ship with a stand-in. `scripts/render.cjs` refuses to render when the logo fails to load.
- The logo already says "NUTRITION HUB · KHANNA", so don't set the brand name again beside it.
- The logo's gold and red belong to the logo only. Never sample them into graphics,
  type or captions. The system palette stays white, ice, ink and orange.
- **Placement** *(derived)*: on porcelain or ice backgrounds, or on a near-opaque white
  glass plate over footage. Never on orange, and never straight on busy footage.
  - Clear space: at least the height of the "KHANNA" line on every side.
  - Size by width. On a 1080-wide canvas: corner bug 280–340 px, end card 720–860 px.
    On 16:9 (1920×1080): end card 640–760 px.
  - The PNG has transparent padding (about 14% at the top and 4% at the bottom).
    Compensate with negative margins (see `templates/reel-9x16.html`), never by editing the file.
- **Logo motion:** glass reveal only (opacity plus scale 0.96→1). Never spin, bounce,
  float, flip or slam the logo.

## 2. Palette: a controlled, luminous palette

| Token | Hex | Role | Share of frame |
|---|---|---|---|
| Porcelain white | `#FFFFFF` | Canvas | 55% |
| Ice mist | `#EAF0F6` | Depth, panels, gradient floor | 20% |
| Graphite ink | `#202B38` | Type | 15% |
| Signal orange | `#F0782B` | Accent: fills, shapes, icons | 10% |

Supporting tones sampled from the playbook:

| Token | Hex | Use |
|---|---|---|
| Orange as text | `#E66D2A` | Kickers and units only. Bold, 28 px or larger. |
| Orange gradient | `#FDAA62 → #F0782B → #EF732D` | Pills, check badges, bars |
| Slate | `#596879` | Body copy, source notes (5.7:1 on white) |
| Mist grey | `#8290A0` | Labels and meta only (3.3:1, so never essential info) |

- Use orange sparingly: key metrics, active states and call-to-action details.
  Allow **one orange focal point per frame** *(derived)*.
- No other hues: no greens, blues, neons or black backgrounds. The logo is the only exception.
- White text on signal orange fails contrast, so don't use it for words. Calls to action
  are ink text on a white chip with an orange dot.
- The stage background is a soft gradient from white (top left) to ice (bottom right),
  plus large faint white discs for depth (`.nh-stage`, `.nh-orb`).

## 3. Typography *(identified from the playbook as Inter)*

Inter only (installed here at `/usr/share/fonts/opentype/inter`; use Google Fonts elsewhere).
Sizes below are for a 1080×1920 canvas. Multiply by 0.85 for 1920×1080 (`.nh-landscape`).

| Style | Size / weight | Tracking | Colour |
|---|---|---|---|
| Display headline | 116 / 800, line-height 0.98 | −0.035em | ink |
| H2 | 72 / 800 | −0.028em | ink |
| Body | 40 / 500, line-height 1.45 | 0 | slate |
| Kicker | 28 / 700 UPPERCASE | +0.20em | orange text |
| Label / meta | 24 / 600 UPPERCASE | +0.14em | mist |
| Data metric | 150–220 / 800, tabular numbers | −0.02em | ink, unit in orange |
| Caption | 62 / 600 | 0 | ink on white box |

Headlines are short, sentence case and end in a full stop ("Creatine, explained simply.").

## 4. Graphic components

All of these are implemented in `assets/brand.css`.

- **A · Glass panels:** frosted information cards with an edge light, a soft shadow and an
  18–28 px radius (`.nh-glass`, `.nh-glass--sm`). Over footage they go near-opaque
  automatically (`.is-transparent`). **Every word over footage sits on a panel.**
- **B · 3D science:** molecular science visuals with realistic materials and controlled
  detail. The SVG atom in `reel-9x16.html` is a stand-in; use a real 3D render:
  - **Small molecules** (creatine, caffeine, BCAAs, beta-alanine, carnitine, glutamine, arginine,
    citrulline, theanine, taurine, glycine, HMB, vitamin C, melatonin, curcumin):
    `templates/molecule-3d.html`. It is a physically based three.js studio (`assets/wg3d.js`): white
    ceramic carbon and hydrogen, frosted-glass heteroatoms, one orange accent atom, studio reflections,
    a soft contact shadow, and real-camera motion blur and depth of field with `?samples=8`. The
    atom positions are computed conformers from verified SMILES (`assets/molecules/`, checked for
    formula and stereochemistry by `scripts/make_molecule.py`, which also adds new molecules), so say
    "3D model: computed conformer" on screen. Elements are told apart by material and size, never
    by hue (no CPK blue nitrogen or red oxygen).
  - **Proteins and enzymes** from a real PDB or AlphaFold structure: the `molecular-film` skill
    (Blender Cycles, on a GPU machine).
  - **A generated still**, only when neither fits, from this prompt base: *"translucent frosted-glass and white ceramic molecular model, one signal
    orange (#F0782B) accent atom, seamless white studio, soft diffused key light, gentle
    reflections, shallow depth of field, high-key, clean editorial, minimal"*.
  - Avoid: neon, dark backgrounds, sci-fi HUDs, lens flares, clutter, glowing particles.
- **C · Data callouts:** evidence-led, with clear units, a source note and orange emphasis
  (`.nh-callout`, `.nh-metric`, `.nh-unit`, `.nh-source`, `.nh-callout__bar`).
  Keep text clear of the orange bar. The playbook sheet itself clips text into it, so don't repeat that.
- **D · Product hero:** product spotlight with accurate packaging and soft reflections. Use
  real product photos or renders only. Never AI-regenerate or alter a label, logo, claim
  or flavour. Show the front label square-on and legible, on a white sweep with soft shadow.
  `templates/product-hero-3d.html` stands the real cut-out photo on a 3D studio floor. Its pixels
  are drawn unlit and un-tonemapped, so the label stays exactly as photographed. The realism
  comes from the light around it: a silhouette shadow, a contact shadow, a satin floor
  reflection and a slow ±6° parallax orbit. It refuses a photo with a solid background.
- **Chips:** `● FROSTED GLASS` style tags and the CTA (`.nh-chip`, `.nh-chip--cta`).
- **Check badge:** orange gradient circle with a white tick (`.nh-check`) for fact lists.

## 5. Motion: physical, calm and intentional

| Primitive | Spec | Easing |
|---|---|---|
| 01 Glass reveal (`.nh-reveal`) | Opacity 0→100%, scale 96→100%, 0.6–0.9 s (default 0.75), edge-highlight sweep | ease-out `cubic-bezier(.22,1,.36,1)` |
| 02 3D float (`.nh-float`) | Y drift ±12 px, rotation ±3°, 2.0–3.0 s loop (default 2.6) | sine in-out `cubic-bezier(.37,0,.63,1)` |
| 03 Kinetic type (`.nh-type`) | Mask reveal per word, stagger 40–70 ms (default 55), 0.35–0.55 s each (default 0.45) | ease-out, **no bouncy overshoot** |
| Exit *(derived)* | Reverse of the reveal: opacity →0, scale →0.98, 0.3–0.45 s | ease-in `cubic-bezier(.64,0,.78,0)` |

- GSAP equivalents: `power3.out` or `expo.out` for reveals, `sine.inOut` for float. Never use `back`, `elastic` or `bounce`.
- Remotion: `Easing.bezier(.22,1,.36,1)`. For springs use `{damping: 200}` with `overshootClamping: true`.
- Put the reveal and the float on different elements (a wrapper and its child), because both animate `transform`.
- **Transitions between shots** *(derived)*: a straight cut by default, a 0.3–0.5 s soft
  dissolve, or a 0.3–0.5 s **dip to porcelain white** (ffmpeg `xfade=transition=fadewhite`).
- **Banned:** whip pans, glitch or RGB split, zoom punches, camera shake, flash frames,
  spins, bounces, light leaks, star wipes.
- **Pacing for high-retention reels** *(derived)*:
  - The hook headline is readable by 0.6 s.
  - Introduce a new visual beat every 1.5–3 s.
  - Hold any text for at least 1 s plus 0.25 s per word.
  - Leave scenes fully before the next one reveals. Never overlap two glass reveals of different beats.

## 6. Captions *(derived)*

- Inter SemiBold 62, graphite ink on an **opaque** white box. One key word per caption
  (a number, a unit or a claim word) goes signal orange. Don't use scale pops, bounces
  or black outlines.
- Keep each caption to 2 lines at most, about 28 characters per line, on screen for 1–3 s.
- The bottom of the caption box sits at about y 1400 on 1920, above the platform UI.
- Quick path: `python3 scripts/captions.py words.json --out captions.ass --srt captions.srt --keywords creatine,protein`
  turns word timings (Whisper / faster-whisper JSON, Remotion captions, or an `.srt`) into
  captions that follow every rule above, using the `reference/captions.ass` style. It never
  splits a number from its unit, highlights the number first and a `--keywords` claim word
  second, and leaves a caption all ink when it has neither. Burn in with
  `ffmpeg -vf "ass=captions.ass:fontsdir=/usr/share/fonts/opentype/inter"`.
- For rounded frosted plates, build the captions as an HTML overlay with `.nh-chip` styling
  and render it with `--transparent`.
- Source notes go in a glass callout (`templates/overlay-callout.html`), not in captions.
- **Talking-head kinetic captions** (one big key word plus small italic connector words, placed beside the head
  or in the top band) are specified in `reference/style-references.md` ("Captions: arrangement, font styles and
  placement"), measured from the owner's reference reels.

## 7. Formats and safe zones *(derived)*

- **9:16 reels, Shorts and TikTok:** 1080×1920 at 30 fps.
  - Keep text and logo inside x 72–1008, y 250–1500.
  - Nothing important in the bottom 420 px or the top 250 px.
- **16:9 product films and education:** 1920×1080. Use 96 px margins and `.nh-landscape`.
- **4:5 feed:** 1080×1350 with 72 px margins.
- **Export:** H.264 High, yuv420p, CRF 16–18, AAC 192 kb/s at 48 kHz, `+faststart`,
  loudness −14 LUFS with true peak −1.5 dBTP.

## 8. Content rules (evidence-led)

- Every number shows its **unit** and an on-screen **source note** ("Source: …").
- Never invent statistics, doses, studies or results. If the user gives no source, ask, or
  put `[SOURCE NEEDED]` in the draft and flag it.
- No cure, treat or guarantee claims, and no before-and-after promises. Keep the tone calm and factual.
- The copy in the templates is example content (the ISSN creatine position stand). Replace it.

## 9. Workflow for any video edit

1. **Read the brief and probe the footage:**
   `ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate:format=duration -of compact in.mp4`.
2. **Check that the logo exists and matches its sha256.** If not, ask for it.
3. **Plan beats:** hook (0–3 s), evidence or value, end card. Choose components from §4.
4. **Build graphics** by copying a template from `templates/` and editing only its `SCENE` object
   and copy. Keep `assets/brand.css` as the single source of truth.
   - `reel-9x16.html`: a full-frame branded reel (hook → data callout → logo end card).
   - `overlay-callout.html`: a transparent glass callout to lay over footage.
   - `molecule-3d.html`: a realistic 3D molecule (pick it with `?molecule=<id>`). Set the copy in `SCENE`.
   - `product-hero-3d.html`: the real product photo in a 3D studio (`?photo=/path/pack.png`).
5. **Render** (from this skill's folder):
   - Full video: `node scripts/render.cjs templates/reel-9x16.html --out out.mp4`
   - Overlay for footage: `node scripts/render.cjs templates/overlay-callout.html --transparent --out callout.mov`
   - End card only: `node scripts/render.cjs templates/reel-9x16.html --from 8.15 --out endcard.mp4`
   - QA still: `node scripts/render.cjs <page> --out frame.png --still 5.2`
   - 3D molecule: `node scripts/render.cjs "templates/molecule-3d.html?molecule=caffeine" --out caffeine.mp4`
   - 3D product hero: `node scripts/render.cjs "templates/product-hero-3d.html?photo=/abs/pack.png" --out hero.mp4`
   - Add `&samples=8` to either for the delivery look (motion blur and depth of field). On a
     CPU-only machine a draft runs at about 0.5 s per frame and `samples=8` at about 8×;
     with a GPU it is much faster. Add `--transparent` for an overlay that keeps the shadow.
   - Preview a 3D template in a browser through a local server, because ES modules don't load from
     `file://`: `python3 -m http.server -d . 8000`, then open `localhost:8000/templates/molecule-3d.html`.
6. **Edit the footage:** reframe, grade, composite, caption, transition, end card and
   loudness. Follow `reference/footage-editing.md`; every recipe in it has been tested.
7. **QA before you deliver.** Run `python3 scripts/qa.py out.mp4` (add `--graphics` for an
   all-graphics piece, `--expect <s>` for the planned length). It checks format, codec,
   audio, faststart, loudness, the logo hash, stray hues and black frames, writes a
   contact sheet, and exits 1 on any FAIL. Then look at the sheet and at full-size stills. Check that:
   - the logo is the original file, unaltered, with clear space and no name repeated beside it
   - the palette holds 55/20/15/10, there is one orange focal point, and no stray hues
   - no text is clipped, colliding with icons or bars, or outside the safe zones
   - motion has no overshoot, timings are within range, and beats don't overlap
   - every number has a unit and a source
   - the export specs match §7

## 10. Companion skills, plugins and connected tools

This skill decides **how it looks and moves**. The companions below do the heavy lifting.
Use the one that fits the job, load this skill first, and give the companion the brand
inputs in the last column.

| Job | Use | Give it |
|---|---|---|
| Raw talking-head phone take → finished 9:16 reel (cut retakes and pauses, word-timed subs, face-aware layout) | `it-reelsmaker` plugin | A brand profile: Inter, §2 palette, the original logo file, §6 caption style, §5 motion. Its subtitles off or restyled to §6 (or burn ours with `scripts/captions.py`). |
| Branded title cards, data callouts, lower thirds, end cards | This skill's `templates/` + `scripts/render.cjs` (first choice: tested and on-brand) | — |
| An editable HyperFrames project or the HyperFrames desktop app | `hyperframes` plugin (project plugin, `.claude/settings.json`) | `assets/brand.css` tokens; grade footage with §2 numbers via its `media-treatment`. Its skill sends a usage note to HeyGen once per run and asks first; say no to skip. |
| A project that is already in Remotion | `remotion` plugin | `Easing.bezier(.22,1,.36,1)`; springs `{damping: 200, overshootClamping: true}` |
| Product film or showreel rendered from code (no footage) | `motion-reel` plugin | Real product photos only (§4 D); palette, logo, §5 motion |
| A realistic 3D molecule (small molecule) | `templates/molecule-3d.html` (§4 B) | A molecule id; new ones via `scripts/make_molecule.py` |
| A realistic protein or enzyme film from a PDB / AlphaFold structure | `molecular-film` skill (Blender, GPU machine) | Its White Glass look constants; labels from our callouts |
| A realistic product hero shot | `templates/product-hero-3d.html` (§4 D) | The real cut-out product photo, never a regenerated one |
| Any step inside Blender or three.js (materials, glass, lighting, HDRI, depth of field, headless render) | `use-3d-software` skill | §2 palette and §5 motion as the targets |
| Photoreal B-roll with no product in it (powder pouring, a shaker, a gym, an athlete) | Runway, ManyMotions or Veo / Kling (`social-media-skills` ai-video router) | §4 B prompt base with high-key white light. Never for packaging, labels, logos, results or real people's bodies. Say it is AI-generated where the platform asks. |
| One-off ffmpeg operations | `reference/footage-editing.md` recipes first (tested), then the `ffmpeg-llm` plugin | — |
| Captions from a transcript | `scripts/captions.py` | Word timings from Whisper, IT Reelsmaker's transcription or the WhisperAI connector |
| Long video → short clips | Clipzi or OpusClip connectors | Logo, Inter, palette, a white-box caption preset with no pop |
| Licensed music and sound effects | Epidemic Sound connector | Calm, clean, under the voice by 18–22 dB |
| Fit a size cap (WhatsApp 16 MB, Gmail, Outlook) | `halfsize` skill (`--for whatsapp`), or the tested ffmpeg fallback in `reference/footage-editing.md` §9 | — |
| Hooks, scripts, captions for the post | `social-media-skills` (hook-writer, reels-script, caption-writer) | §8 content rules |
| Final check | `scripts/qa.py`, then §9.7 by eye | — |

**When a companion disagrees with this skill, this skill wins.** Take structure and
tooling from companions, never their look:

- **Look:** palette, Inter, glass components and the original logo file come from here.
  Ignore a companion's default theme, fonts, colours and style presets. Nutrition Hub
  type is fixed as Inter, so don't run a font-picking step for it.
- **Motion:** §5 overrides any motion advice. That means no zoom punches or snap-zooms,
  no whip pans, no pop, spring or bounce captions, no logo crash-ins from oversize, and no
  glitch or flash frames, even when a companion recommends them for retention. A slow
  push-in of up to about 5% over a whole shot is fine.
- **Captions:** §6 overrides karaoke, "Hormozi" and word-pop presets.
- **Pacing:** retention advice from companions is welcome when it fits §5 (hook readable by 0.6 s, a beat every 1.5–3 s, text holds).
- **Content:** §8 overrides any generated copy. No invented numbers, sources or results.
- **Sound:** licensed or synthesized only, finished at −14 LUFS.

In any app (ManyMotions, Clipzi, OpusClip, Picsart, CapCut, HyperFrames and so on): upload
`assets/logo/nutrition-hub-logo.png` as the logo, set Inter and the §2 colours, pick the
caption preset closest to "dark text on a white box with one orange word, no animation",
set transitions to cut, fade or dip-to-white, and run `scripts/qa.py` on the export.

## Files

```
SKILL.md                       this guide
assets/logo/nutrition-hub-logo.png   ORIGINAL logo (never modify)
assets/brand.css               tokens, components and motion primitives
templates/reel-9x16.html       full branded reel (edit the SCENE object)
templates/overlay-callout.html transparent glass callout for footage
templates/molecule-3d.html     realistic 3D molecule (ceramic + frosted glass, studio light, real-camera blur)
templates/product-hero-3d.html real product photo in a 3D studio (shadow, reflection, parallax)
assets/wg3d.js                 the 3D studio: PBR materials, light, shadow catcher, camera, builders
assets/molecules/              computed conformers of 17 supplement molecules (+ library.json of verified SMILES)
assets/vendor/three/           three.js r170 (MIT), vendored
scripts/make_molecule.py       SMILES → verified 3D molecule JSON (needs RDKit)
scripts/render.cjs             HTML → MP4 / ProRes 4444 / VP9-alpha / PNG (Playwright + ffmpeg)
scripts/captions.py            word timings / SRT → White Glass .ass captions (+ .srt sidecar)
scripts/qa.py                  automated delivery QA (specs, loudness, logo hash, hues, contact sheet)
reference/playbook.png         the original brand playbook sheet
reference/captions.ass         caption style for ffmpeg/libass
reference/footage-editing.md   tested ffmpeg recipes for real footage
reference/style-references.md  the owner's reference reels: techniques, caption layout and placement, open decisions
```
