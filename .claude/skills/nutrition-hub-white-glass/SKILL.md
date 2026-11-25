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
- No other hues: no greens, blues, neons or black backgrounds. Two exceptions: the logo, and a caption
  key word matched to the video's own colour (§6).
- **Alternate colour schemes** (owner request, 2026-11-25). `templates/hook-slam.html` also renders in
  three other schemes, chosen with `?scheme=`:
  - `mint`: white with green
  - `mustard`: cream with mustard
  - `navy-lime`: dark navy with lime
  Each keeps one accent colour, Inter plus the §3 accent faces, the motion rules and the original logo
  (on a white plate on navy, because the logo's KHANNA line is dark). White Glass stays the default.
  Use another scheme only when the owner asks or to match a video's colours, and keep one scheme per video.
- White text on signal orange fails contrast, so don't use it for words. Calls to action
  are ink text on a white chip with an orange dot.
- The stage background is a soft gradient from white (top left) to ice (bottom right),
  plus large faint white discs for depth (`.nh-stage`, `.nh-orb`).

## 3. Typography *(Inter from the playbook, plus two accent faces the owner approved)*

Inter for everything (installed here at `/usr/share/fonts/opentype/inter`; use Google Fonts elsewhere),
plus two accent faces approved on 2026-11-25. Both are bundled in `assets/fonts/` (SIL OFL 1.1) and
loaded by `assets/brand.css`.
Sizes below are for a 1080×1920 canvas. Multiply by 0.85 for 1920×1080 (`.nh-landscape`).

| Style | Size / weight | Tracking | Colour |
|---|---|---|---|
| Display headline | 116 / 800, line-height 0.98 | −0.035em | ink |
| H2 | 72 / 800 | −0.028em | ink |
| Body | 40 / 500, line-height 1.45 | 0 | slate |
| Kicker | 28 / 700 UPPERCASE | +0.20em | orange text |
| Label / meta | 24 / 600 UPPERCASE | +0.14em | mist |
| Data metric | 150–220 / 800, tabular numbers | −0.02em | ink, unit in orange |
| Caption | 62 / 700 | 0 | bare words: white with a soft shadow on footage, ink on light backgrounds |

Headlines are short, sentence case and end in a full stop ("Creatine, explained simply.").

**Accent serif: Instrument Serif Italic** (`.nh-accent`)
- One word per line, and at most one per beat, inside an Inter headline or kinetic line:
  "Protein isn't the whole *story.*".
- Always orange: #E66D2A as text on light backgrounds, #F0782B over footage.
- Set it 1.3× the Inter words around it (the serif runs small).
- Only in headlines and kinetic lines of 60 px or more. Never for numbers or units, captions,
  body copy, labels or source notes. Numbers stay Inter so they read instantly.
- **Exception, captions (R6 typeface accent, owner request 2026-11-25):** one word per caption may
  switch to Instrument Serif Italic **in the caption's own colour** (white or ink, not orange), at about 1.3×.
  Use `captions.py --serif-words carefully,really`. Never on the coloured key word or on a number.

**Condensed slam: Bebas Neue** (`.nh-slam-word`)
- One word or one number on its own line, in capitals, 200–320 px, ink or orange.
- At most one per beat and about one every 5 s, so it stays a hit.
- Never sentences, never on the same line as Inter, never in captions, and never with a unit
  ("33 g" stays an Inter data metric).
- In one frame, use either the slam word or the orange serif accent as the orange focal point, not both.

## 4. Graphic components

All of these are implemented in `assets/brand.css`.

- **A · Glass panels:** frosted information cards with an edge light, a soft shadow and an
  18–28 px radius (`.nh-glass`, `.nh-glass--sm`). Over footage they go near-opaque
  automatically (`.is-transparent`). **Every word over footage sits on a panel**, except caption
  words: those are bare, with no glass (§6).
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
- **E · Bottom blur band (R6, owner request 2026-11-25).** The lower frame melts into a progressive blur
  (sharp to about 64% of the height, full blur by 76%) and a fade (from 72% to about 85% at the bottom edge).
  Desk clutter disappears and captions and cards above it stand out.
  - Footage files: `python3 scripts/bottom_blur.py in.mp4 out.mp4` (dark fade, the R6 look).
  - White-stage pieces: add `--tone light` to fade to porcelain instead.
  - HTML templates: the `.nh-bottom-blur` element (`.is-light` for white).
  - Run it after the grade and **before** captions and cards, so they stay sharp.
  - **Only when needed** (owner request, 2026-11-25). Don't run the band for the whole video by default.
    - Give `bottom_blur.py` the plan from `captions.py --position auto --plan-out plan.json` (`--plan plan.json`).
      The band then fades in over 0.3 s just while captions sit in a busy bottom band, and fades out after.
    - For animations placed in the bottom band (pills, cards, lower thirds), add their windows with
      `--when 3.0-5.5,12-14`.
    - Run with neither `--plan` nor `--when`, it covers the whole video. `--auto` starts it just under
      the person.
  - **The bottom band as a placement zone:** captions (`--prefer bottom`) and animations can sit there.
    The blur switches on under them when the background there is busy; on calm ground, no blur is added.
- **F · B-roll cutaways (R5, owner request 2026-11-25).** The voice keeps running while the picture cuts
  away to what is being said, then back to the face. `scripts/broll.py` does it; what to film is in
  `reference/broll-shot-list.md`.
  - **Sources, in order:**
    1. The owner's own store footage.
    2. Graphic b-roll made here: a 3D molecule (§4 B), the product hero (§4 D), a real product or
       label photo (a still gets a slow 4% push; a cut-out sits on an ice-mist stage).
    3. Licensed stock.
    4. AI video only with the owner's OK, never showing products, labels, logos, results or real
       people's bodies, and disclosed where the platform asks.
  - **Timing:**
    - Start the b-roll on the word it shows (`--words` + `--map label=label-closeup-01.mp4`), or at set
      times (`--at 3.2-5.0=file`).
    - Shots last 1.5–3 s (4 s at most), with at least 1 s of face between shots.
    - No b-roll in the first 1.5 s (the hook shows the face). Keep b-roll under about 45% of the runtime.
    - The script enforces these.
  - **Transitions:** a cut by default. Use `--transition white` (a 0.4 s dip to porcelain white, peaking on
    the cut, R5) for a change of topic, or `soft` (a 0.25 s dissolve) for calm pieces. Never whip, zoom
    punch or glitch (§5).
  - **Look:**
    - B-roll gets the same soft studio grade as the face shots, conformed to the reel's size and
      frame rate.
    - Label close-ups and product photos are never graded (`"grade": false`; stills are off by
      default), so packaging stays accurate.
    - HDR phone clips are tone-mapped.
  - **Sound and captions:** the b-roll's own sound is dropped and the voice track is copied unchanged.
    Captions stay on during b-roll; run `captions.py --match` on the cut, so colours match the b-roll too.
  - **Order:** grade → b-roll → bottom blur band → captions → end card.
- **G · Orbit (R5, owner request 2026-11-25).** Ceramic spheres (one signal orange) burst out from behind the
  speaker's head onto a thin white ring, turn slowly (30°/s), then fold back behind the head.
  - Command: `scripts/fx.py orbit --at 3-6`.
  - A tilted ring (`--tilt 65`) is centred at the chin: its front half crosses the chest, its back half passes
    behind the head, and it never crosses the face.
  - Word chips (`--words "Whey,Creatine,Omega-3"`): up to 4 short words, Inter on frosted pills.
  - Occlusion: a head-and-shoulders matte from the face track hides what passes behind, and detected hands
    pass in front.
  - Use it for one signature beat per reel, 2.5–4 s.
- **H · Frame escape (owner request 2026-11-25).** The picture closes into a porcelain-bordered frame on the
  White Glass stage, while the speaker's head and raised hands stay outside it.
  - Command: `scripts/fx.py escape --at 2-5`.
  - It needs a real outline of the speaker. Two sources:
    - `--matte wall` keys a plain, evenly lit wall (the "Free Space" set-up).
    - `--matte FILE` takes a matte video from CapCut ("Remove background") or Runway, white = person.
  - A busy room needs one of those files. The AI segmenter (MediaPipe) wasn't allowed to install in the
    cloud session.
  - Use it for a hook or a reveal, 2.5–4 s, at most once per reel.
- **I · Chat takeover (R4, owner request 2026-11-25).** `templates/chat-takeover.html`, rendered `--transparent`.
  - The sequence: a contact list → one contact picked (the rest blur away) → a message types out with an
    orange caret → the orange send button → typing dots → a reply.
  - `?layout=top` sits above the head: pass `?bottom=` (head top − 40 px) so it can't cover the face.
  - `?layout=full` takes over the frame with a frosted wash.
  - Honesty:
    - The "Example chat" label stays unless the chat is real and shared with the person's written OK, with
      their name and number hidden.
    - Never a WhatsApp or Instagram logo or look-alike.
    - Never a made-up customer testimonial.
- **J · Head and hand motion (owner request 2026-11-25).** `scripts/motion_track.py` follows the head at the
  full frame rate (face detection plus optical flow) and finds the hands (the speaker's own skin tone, movement,
  within arm's reach), with no model download.
  - It lists moments to time effects on: `gesture`, `hands_up`, `head_move`.
  - `--preview` draws what it found.
  - The orbit and escape use it automatically.
  - Reliable on a plain wall with contrasting clothes (R4: hands in 99% of frames, no false hands). Warm,
    busy rooms, wooden furniture and blonde hair can fool the hand finder (R5), so check the preview.
    The head track is reliable in both.
- **Check badge:** orange gradient circle with a white tick (`.nh-check`) for fact lists.

## 5. Motion: physical, calm and intentional

| Primitive | Spec | Easing |
|---|---|---|
| 01 Glass reveal (`.nh-reveal`) | Opacity 0→100%, scale 96→100%, 0.6–0.9 s (default 0.75), edge-highlight sweep | ease-out `cubic-bezier(.22,1,.36,1)` |
| 02 3D float (`.nh-float`) | Y drift ±12 px, rotation ±3°, 2.0–3.0 s loop (default 2.6) | sine in-out `cubic-bezier(.37,0,.63,1)` |
| 03 Kinetic type (`.nh-type`) | Mask reveal per word, stagger 40–70 ms (default 55), 0.35–0.55 s each (default 0.45) | ease-out, **no bouncy overshoot** |
| 04 Slam (`.nh-slam`) *(approved 2026-11-25)* | Lands from 2.5× with a 14 px motion blur clearing to sharp, opacity in over the first 55%, 0.28–0.36 s (default 0.32). Only for the hook word in the first 0.6 s and for condensed slam words; at most one per beat | expo-out `cubic-bezier(.16,1,.3,1)`, settles exactly at 1, **no overshoot** |
| Exit *(derived)* | Reverse of the reveal: opacity →0, scale →0.98, 0.3–0.45 s | ease-in `cubic-bezier(.64,0,.78,0)` |

- GSAP equivalents: `power3.out` or `expo.out` for reveals, `sine.inOut` for float. Never use `back`, `elastic` or `bounce`.
- Remotion: `Easing.bezier(.22,1,.36,1)`. For springs use `{damping: 200}` with `overshootClamping: true`.
- Put the reveal and the float on different elements (a wrapper and its child), because both animate `transform`.
- **Transitions between shots** *(derived)*: a straight cut by default, a 0.3–0.5 s soft
  dissolve, or a 0.3–0.5 s **dip to porcelain white** (ffmpeg `xfade=transition=fadewhite`).
- **Banned:** whip pans, glitch or RGB split, camera zoom punches on footage, camera shake,
  flash frames, spins, bounces, light leaks, star wipes. The 04 Slam is a *type* entrance only:
  never on the logo, cards, captions or footage.
- **Pacing for high-retention reels** *(derived)*:
  - The hook headline is readable by 0.6 s.
  - Introduce a new visual beat every 1.5–3 s.
  - Hold any text for at least 1 s plus 0.25 s per word.
  - Leave scenes fully before the next one reveals. Never overlap two glass reveals of different beats.
- **Sound effects** *(owner request 2026-11-25)*: SFX are calm, glassy and sparse, the sound of the
  motion above. `scripts/sfx.py` holds an original kit synthesised in code, so there are no samples
  and no licence to check.

  | Sound | Marks | Level under the voice |
  |---|---|---|
  | `thud` | a slam word landing (0.18 s into the 04 Slam) | 6 dB |
  | `riser` | the lead-in to a slam (optional; ends on the cue) | 14 dB |
  | `whoosh` | a dissolve or a scene change | 10 dB (13 on b-roll dissolves) |
  | `swish` | a dip to white, including into b-roll | 10 dB |
  | `pop` | a glass card or data callout appearing | 12 dB |
  | `tick` | a check pill, badge or list item (a run steps up in pitch) | 14 dB |
  | `glass` | the logo or end card | 11 dB |

  - **Where:** only on structure: slams, dips to white, pills, cards and the logo.
    - `render.cjs` writes a cue sheet (`<out>.sfx.json`) from the template's own animations.
    - `broll.py --plan-out` gives the b-roll moments.
    - Plain cuts into b-roll stay silent, and so do captions, kinetic type and ordinary cuts.
    - About one sound beat every 2 s at most; a run of ticks counts as one beat.
  - **Level:** each sound is set against the voice's measured loudness (above), and the mix is mastered to
    −14 LUFS. Music, when there is any, sits 18–22 dB under the voice, so SFX sit above the music.
  - **Banned:** cartoon boings, "vine boom" bass drops, record scratches, cash registers, glitch
    stutters, laugh tracks, camera-shutter clicks, and any sound on every word.
  - **Other libraries:** Epidemic Sound SFX only when the owner has a commercial plan that covers the
    business account. Keep the same placement and level rules.

## 6. Captions *(derived)*

- **Caption words are bare: no glass, box, pill or panel behind them** (the owner's call, 2026-11-25).
  Inter Bold 62 with a soft blurred shadow for legibility, never a hard black outline.
  - **Footage (default):** white words with a soft dark shadow.
  - **Light walls and the white stage:** graphite ink words with a soft white glow. Use ink only
    where everything behind the words is light; over dark clothing or busy footage, use white.
  - **Busy light-and-dark backgrounds:** white words with a stronger shadow.
- **Caption colours follow the video** (the owner's call, 2026-11-25). Always build captions with
  `--match <the video they go on>` (`scripts/caption_colors.py` does the analysis):
  - **Base:** read from the caption zone about twice a second. White for dark or mid footage,
    ink for light footage, and on mixed videos each caption follows what is behind it.
  - **Key word colour:** the video's own dominant colour, even a small accent (lime on a navy edit,
    green or mustard on a minimal white edit). It is re-coloured to a readable shade: bright on
    white words, deep on ink words (3:1 or better for large text).
  - **Fallback:** signal orange (#F0782B, or #E66D2A on ink words) when the video has no clear
    colour or its colour is already warm or orange.
  - **Per caption:** a caption switches to orange when the video's colour sits right behind it at
    that moment (a blue key word on a blue shirt would vanish). Tested on R6, where the blue shirt
    sends every caption to orange.
  - Caption words only. The logo, glass cards, callouts, kickers, data metrics and the serif
    accent keep the §2 palette.
- One key word per caption (a number, a unit or a claim word) goes in that key-word colour.
  Don't use scale pops or bounces.
- Keep each caption to 2 lines at most, about 28 characters per line, on screen for 1–3 s.
- **Position** (`captions.py --position`):
  - **`auto`: captions use the vacant space around the person** (owner request, 2026-11-25).
    `scripts/layout_plan.py` tracks the face (`person_track.py`) and, for every caption, fits the text
    into five candidate slots:
    - left or right of the head, from the safe edge to 40 px off the face, at head-to-shoulder height
    - above the head
    - the chest, one face-height below the chin
    - the bottom band under the person
    It wraps and resizes the text from 62 px down to 46 px, at most 3 lines, and picks the calmest slot that
    fits, measured by edge energy behind the text, with side slots preferred and the chest and bottom last.
    It keeps the previous caption's slot unless another is clearly better, never covers the face, and
    follows the person as they move. The words take the slot's own background: ink on a light wall,
    white elsewhere, and a strong shadow on busy ground. Use it with `--max-words 2` or `3`.
    `--prefer left|right|top|chest|bottom` uses one slot whenever the caption fits there; for example,
    `--prefer bottom` puts captions in the blur band. With no face (a faceless video) it falls back to `bottom`.
  - `bottom` (default without a person): the text bottom at about y 1400 on 1920, above the platform UI.
  - `mic`: centred about 58%, for seated desk and mic shoots, above a bottom blur band (R6).
  - `chest`: centred about 50% (R5).
  `--match` reads the colours from the same band the captions sit in.
- **Talking-head recipe:**
  1. `python3 scripts/captions.py words.json --out c.ass --match graded.mp4 --position auto --max-words 3 --keywords protein --serif-words really --plan-out plan.json`
  2. `python3 scripts/bottom_blur.py graded.mp4 blurred.mp4 --plan plan.json`. The band fades in **only
     while** a caption sits on a busy bottom; with nothing there, the video is copied unchanged.
  3. Burn `c.ass` into `blurred.mp4` (below).
  Needs `pip install opencv-python-headless==4.10.0.84`. The 4.x line ships the face model; 5.x does not.
- Quick path: `python3 scripts/captions.py words.json --out captions.ass --srt captions.srt --keywords creatine,protein --match video.mp4`
  turns word timings (Whisper / faster-whisper JSON, Remotion captions, or an `.srt`) into
  captions that follow every rule above, using the `reference/captions.ass` style. It never
  splits a number from its unit, highlights the number first and a `--keywords` claim word
  second, and leaves a caption one colour when it has neither. `--match` picks the colours
  from the video. Without it, captions are white with an orange key word; `--style` and
  `--accent #RRGGBB` override by hand. Burn in with
  `ffmpeg -vf "ass=captions.ass:fontsdir=<skill>/assets/fonts"`. That folder holds the serif; Inter comes
  from the system fonts, so Inter must be installed.
- For animated captions (kinetic type), build them as an HTML overlay of bare Inter words with a
  soft `text-shadow`, no chip or glass, and render it with `--transparent`.
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
   - `hook-slam.html`: a 10 s hook. Two condensed slam words 5 s apart, Inter lines ending on a serif accent
     word, check pills, then the original logo. Colour schemes via `?scheme=` (see §2).
   - `molecule-3d.html`: a realistic 3D molecule (pick it with `?molecule=<id>`). Set the copy in `SCENE`.
   - `product-hero-3d.html`: the real product photo in a 3D studio (`?photo=/path/pack.png`).
   - `chat-takeover.html`: a chat sequence (list → pick → typed message → send → reply), above the head or
     taking over the frame (§4 I).
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
6. **Edit the footage:** reframe, grade, b-roll cutaways (§4 F), composite, caption, transition,
   end card, then sound effects and loudness (§5 Sound effects, `scripts/sfx.py`, run last). Follow
   `reference/footage-editing.md`; every recipe in it has been tested.
7. **QA before you deliver.** Run `python3 scripts/qa.py out.mp4` (add `--graphics` for an
   all-graphics piece, `--expect <s>` for the planned length). It checks format, codec,
   audio, faststart, loudness, the logo hash, stray hues and black frames, writes a
   contact sheet, and exits 1 on any FAIL. Then look at the sheet and at full-size stills. Check that:
   - the logo is the original file, unaltered, with clear space and no name repeated beside it
   - at most one serif accent word per line and one slam per beat; the serif is never on a number
   - the palette holds 55/20/15/10, there is one accent focal point, and no stray hues (a matched
     caption key word may be the video's own colour; run `qa.py` without `--graphics` then)
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
| Live control of Blender on the owner's computer: read the scene, build and light it, look through the camera, render a still | `blender` MCP server (`.mcp.json`, set-up and rules in `reference/blender-mcp.md`) | Real product photos only (never `generate_3d` for products, labels or logos); White Glass look constants from `molecular-film`; safe mode stays on |
| Cut b-roll into a talking head (on spoken words or at set times) | `scripts/broll.py` (§4 F) | The owner's clips, named as in `reference/broll-shot-list.md`, plus word timings |
| Orbit, frame escape, chat takeover; head and hand motion | `scripts/fx.py`, `templates/chat-takeover.html`, `scripts/motion_track.py` (§4 G–J) | A plain-wall take or a matte video for the escape; real, consented chats or the "Example chat" label |
| Photoreal B-roll with no product in it (powder pouring, a shaker, a gym, an athlete) | Only with the owner's OK: Runway, ManyMotions or Veo / Kling (`social-media-skills` ai-video router). They spend the owner's credits. | §4 B prompt base with high-key white light. Never for packaging, labels, logos, results or real people's bodies. Say it is AI-generated where the platform asks. |
| One-off ffmpeg operations | `reference/footage-editing.md` recipes first (tested), then the `ffmpeg-llm` plugin | — |
| Captions from a transcript | `scripts/captions.py` | Word timings from Whisper, IT Reelsmaker's transcription or the WhisperAI connector |
| Long video → short clips | Clipzi or OpusClip connectors | Logo, Inter, palette, a plain caption preset (no box, no pop) |
| Sound effects | `scripts/sfx.py` (original kit, §5): cue sheets from `render.cjs` and `broll.py` | — |
| Licensed music (and SFX beyond the kit) | Epidemic Sound connector, only with a commercial plan for the business | Music calm and clean, 18–22 dB under the voice; SFX by §5 rules |
| Fit a size cap (WhatsApp 16 MB, Gmail, Outlook) | `halfsize` skill (`--for whatsapp`), or the tested ffmpeg fallback in `reference/footage-editing.md` §9 | — |
| Hooks, scripts, captions for the post | `social-media-skills` (hook-writer, reels-script, caption-writer) | §8 content rules |
| Final check | `scripts/qa.py`, then §9.7 by eye | — |

**When a companion disagrees with this skill, this skill wins.** Take structure and
tooling from companions, never their look:

- **Look:** palette, Inter, glass components and the original logo file come from here.
  Ignore a companion's default theme, fonts, colours and style presets. Nutrition Hub
  type is fixed (Inter, plus the two §3 accent faces in `assets/fonts/`), so don't run a
  font-picking step for it.
- **Motion:** §5 overrides any motion advice. That means no camera zoom punches or snap-zooms,
  no whip pans, no pop, spring or bounce captions, no logo crash-ins from oversize, and no
  glitch or flash frames, even when a companion recommends them for retention. The one
  oversize entrance allowed is §5's 04 Slam, on a hook or slam word. A slow
  push-in of up to about 5% over a whole shot is fine.
- **Captions:** §6 overrides karaoke, "Hormozi" and word-pop presets.
- **Pacing:** retention advice from companions is welcome when it fits §5 (hook readable by 0.6 s, a beat every 1.5–3 s, text holds).
- **Content:** §8 overrides any generated copy. No invented numbers, sources or results.
- **Sound:** licensed or synthesized only, finished at −14 LUFS.

In any app (ManyMotions, Clipzi, OpusClip, Picsart, CapCut, HyperFrames and so on): upload
`assets/logo/nutrition-hub-logo.png` as the logo, set Inter and the §2 colours, pick the
caption preset closest to "plain bold words with a soft shadow and one orange word, no box, no animation",
set transitions to cut, fade or dip-to-white, and run `scripts/qa.py` on the export.

## Files

```
SKILL.md                       this guide
assets/logo/nutrition-hub-logo.png   ORIGINAL logo (never modify)
assets/brand.css               tokens, components and motion primitives
templates/reel-9x16.html       full branded reel (edit the SCENE object)
templates/overlay-callout.html transparent glass callout for footage
templates/hook-slam.html       10 s hook: Bebas slams + Inter lines with a serif accent + pills + logo; ?scheme= colour schemes
templates/chat-takeover.html   chat sequence overlay (R4): ?layout=top (above the head, ?bottom=) or ?layout=full (takeover)
assets/fonts/                  Instrument Serif Italic + Bebas Neue (SIL OFL 1.1), with licences and SOURCE.md
templates/molecule-3d.html     realistic 3D molecule (ceramic + frosted glass, studio light, real-camera blur)
templates/product-hero-3d.html real product photo in a 3D studio (shadow, reflection, parallax)
assets/wg3d.js                 the 3D studio: PBR materials, light, shadow catcher, camera, builders
assets/molecules/              computed conformers of 17 supplement molecules (+ library.json of verified SMILES)
assets/vendor/three/           three.js r170 (MIT), vendored
scripts/make_molecule.py       SMILES → verified 3D molecule JSON (needs RDKit)
scripts/render.cjs             HTML → MP4 / ProRes 4444 / VP9-alpha / PNG (Playwright + ffmpeg)
scripts/captions.py            word timings / SRT → White Glass .ass captions (+ .srt sidecar)
scripts/caption_colors.py      reads a video and picks caption colours to match it (used by captions.py --match)
scripts/bottom_blur.py         R6 bottom blur band for footage: progressive blur + dark or light fade (--auto follows the person)
scripts/broll.py               b-roll cutaways over a talking head: on spoken words or set times; cut, white dip or dissolve
scripts/sfx.py                 original SFX kit (synthesised) + mixer: cue sheets, b-roll plans, levels under the voice, -14 LUFS master
scripts/fx.py                  person-aware effects: orbit (spheres or word chips around the head) and frame escape
scripts/person_matte.py        person mattes for fx.py: head shape from the face track, plain-wall key, or a matte video
scripts/motion_track.py        head (full frame rate) and hand tracking, gesture / hands-up / head-move moments, --preview
scripts/person_track.py        finds where the person is (face track) for auto caption placement and the blur band
scripts/layout_plan.py         picks the vacant slot around the person for each caption and when the blur band is needed
scripts/qa.py                  automated delivery QA (specs, loudness, logo hash, hues, contact sheet)
reference/playbook.png         the original brand playbook sheet
reference/captions.ass         caption style for ffmpeg/libass
reference/footage-editing.md   tested ffmpeg recipes for real footage
reference/broll-shot-list.md   what to film in the store for b-roll, how to film it and how to name the files
reference/blender-mcp.md       Blender MCP (the repo's .mcp.json): one-time set-up on the owner's computer and the rules for using it
reference/style-references.md  the owner's reference reels: techniques, caption layout and placement, open decisions
```
