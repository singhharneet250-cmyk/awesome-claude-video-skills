# Learned tools, sites and skills (2026-11-26)

What the owner pointed to (in the R8–R18 videos and in screenshots), what was learned or installed, and what needs
the owner's own computer or account. Everything here is subordinate to SKILL.md: take techniques, not looks.

## prompt-motion.com (from R16)

A free library of 240 motion videos made with Claude, each beside the prompt or skill that made it, curated by
@p4nthera_ (started 5 October 2026). "Videos and prompts belong to their creators", so prompts are read for
technique and never copied into a deliverable. Categories (November 2026): Product UI 103, Kinetic type 100,
Shapes 43, Particles 43, Charts 33, Diagrams 31, Characters 25, Phone 23, Photos 23, Music 51, Code 20.
This repo's cloud environment allows `prompt-motion.com` and `www.prompt-motion.com` (added at the owner's request).

What the best prompts share, now in SKILL.md §5 and the motion kit:

- **Every frame is a pure function of time**: compute every style inside `seek(t)`; no CSS transitions, timers or
  state carried between frames (our templates already work this way).
- **Closed-form springs**; a value that changes target several times is the sum of one spring per change. We use
  critically damped springs (no overshoot, §5), where the prompts allow "a tiny overshoot at most".
- **Two edges on different springs**: a toggle knob or tab indicator stretches (leading edge first) and settles.
  Used in Toggle List and Shape Morph.
- **One shape, never cut**: every state is the same element morphing size, radius and colour while its content
  swaps with a short blur (Shape Morph). Outgoing and incoming text get separate timing so letters never overlap.
- **One element connects every scene** (the "orange dot motion system" prompt), and "motion that isn't connected to
  an element already on screen" is banned. Ours: the orange dot.
- **Something happens on every beat** (120 BPM is common); scene changes land on bars; SFX placed at measured peaks.
- **Motion blur**: render sub-frames and blend them (they use 4 sub-frames with ffmpeg `tmix`). Ours:
  `render.cjs --blur 4`.
- **Check before the full render**: one still per beat, then a contact sheet, then the full render.
- **Gotchas**: no `will-change` on anything a camera scales (text goes soft); the last frame equals the first for
  loops; when a shape fills the screen, scale it past all four corners.
- **Banned in the good prompts too**: bouncy easing, particle bursts, glows, gradients on UI chrome, dead time,
  anything that looks like a template.
- Music for those films: royalty-free tracks around 120 BPM, often Mixkit.

## Skills installed in this repo (read in full and checked first)

| Skill | From | Licence | Use for Nutrition Hub |
|---|---|---|---|
| `cinetic` | github.com/Leonxlnx/cinetic @ f4bbfc8 | MIT | Launch, product and promo films from code, held to measured gates (words in the middle, one element carried, hidden cuts, copy check, `forensics.py`). Its own rule says a supplied brand wins, so its "no orange", "no serif" and "no glassmorphism" house bans don't apply to us. |
| `product-film` | github.com/Rieranthony/product-film-skill @ fe11efc | MIT | A product film on the brand's design system, cut to music on measured beats (`scripts/beats.py`), with stills and verify steps |
| `camera-3d-captions` | github.com/heygen-com/hyperframes-community-skills @ ba7a0bb | Apache-2.0 | Captions in depth around a talking head (groups at depths, a hero word behind the head, a ring of words). Its whip-ins and push-ins are camera zooms: not on our reels. |

Each description says to load `nutrition-hub-white-glass` first. Python packages they need were installed in this
session (scipy, soundfile, pyloudnorm, librosa, fonttools, brotli, uharfbuzz, imageio-ffmpeg, opentimelineio); a fresh
cloud session reinstalls them with `pip install -r` of each skill's requirements, or from a saved setup script.

Not installed: `html-demo` (MengTo/skills, app demos in a Mac window: Nutrition Hub has no app), Taste Skill
(dashboards), the history-film skill, and the other HyperFrames community skills (day-in-my-life, duo, p5 paint,
Strudel music, X posting licence).

## Tools from the owner's screenshots (@thebotfather.ai, 2026-11-26)

| Tool | What it is | Decision |
|---|---|---|
| Remotion Skills (remotion.dev/skills) | Official skills for videos in React | **Already available**: they sync from the owner's Claude account as the Remotion plugin (`remotion:*` skills). Nothing to add. |
| pen.dev (formerly Pencil) | A free design canvas inside VS Code or Cursor that Claude Code reads and draws on through its own MCP, with `.pen` files next to the code | Useful for designing thumbnails and title cards by hand. Desktop only: install it on the owner's computer; its MCP registers itself while it runs (check with `/mcp`). |
| Rive MCP (rive.app) | Claude builds Rive animations and state machines in the Rive Editor | Desktop editor (macOS, Windows) with a local server: `claude mcp add --transport http rive http://127.0.0.1:9791/mcp` while the editor is open. Good for interactive or looping UI pieces; for a reel, export a video. Never redraw the logo in it. |
| Mobbin MCP (mobbin.com/mcp) | 600,000+ real app screens for design reference | Not added: it needs a paid Mobbin plan and Nutrition Hub has no app. |
| React Bits (reactbits.dev) | 165+ animated text effects, backgrounds and components for React | Not installed (no React project here; licence MIT + Commons Clause: free to use in videos, not to resell). Its text effects map to ours: Count Up → Count-up Bars, Rotating Text → Word Wheel, Scroll Velocity → Big Scroll, Blur Text → Tracking Reveal. Its colourful backgrounds (Aurora, Silk) are off-palette. |

## Tools named in the videos

| Tool | Seen in | Decision |
|---|---|---|
| DaVinci Resolve | R16's hashtags | `timeline.py export` writes an `.otio` timeline Resolve imports (File > Import > Timeline), plus captions as `.srt`. Effects arrive as markers; real glass and effects are rendered by `timeline.py render`. |
| Mixkit (mixkit.co) | the prompt-motion prompts | Free music and SFX. Mixkit's information page says its Free License covers commercial use (YouTube, social, ads) without attribution; check the licence shown on each track's page before use. `mixkit.co` is allowed in this cloud environment. |
| ArtCraft / FilmCraft | browser tabs in R16 | An open-source (MIT) desktop "IDE for AI film" by Storyteller; generation runs on paid credits or your own keys. Not installed: desktop app, and AI generation needs the owner's OK. |
| Holo (tryholo.ai), Kinso, FYLR, Codex | R12, R15, R13, R14 | Products being promoted, not tools for us. |
| liquid/glass web component (zerowing.in/glass) | R18 | Not installed: we need glass on rendered video, not on a website. Its ideas (Snell refraction, IOR 1.5, RGB dispersion, rigid rim) are rebuilt in `scripts/glass.py`. |

## Apple's Liquid Glass (owner's suggestion)

Apple's guidance (Human Interface Guidelines: Materials; WWDC25 "Meet Liquid Glass") and how it is used here:

- **Lensing**: the material bends and concentrates light instead of scattering it → `glass.py` refracts the footage
  at the rim.
- **Materialize**: elements appear by modulating light bending, not by fading → `glass.py` grows the lensing, frost,
  tint and rim with the panel's reveal.
- **Adaptivity**: the material adapts to what is behind it → the porcelain tint adapts so ink text always reads.
- **Variants**: regular (works everywhere) and clear (more see-through, needs care for legibility) →
  `--variant regular` (default) and `--variant clear` (no small text on it).
- **Highlights respond to movement** → the rim light turns a little as a panel moves.
- **Concentric shapes**, and **never glass on glass** → SKILL.md §4 A.
- **iOS 27 (WWDC 2026)** refined Liquid Glass after a year of readability complaints: a system slider from fully
  opaque to completely clear, a more legible default, new rendering, and adaptation to Reduce Transparency and
  Increase Contrast → `glass.py --strength` (0 opaque … 1 clear), house default 0.4, readable by design.
- **Clear variant, from the HIG (Materials) and SwiftUI `Glass.clear`, read 2026-11-26**: clear is "highly
  translucent", for components that float over photos and video, and only over visually rich backgrounds; regular
  "blurs and adjusts the luminosity" and suits text-heavy components. Clear needs a layer underneath for
  legibility: the HIG suggests a dark dimming layer of 35% when the content behind is bright (none when it is
  already dark); the SwiftUI example uses 30% black. Apple's clear glass carries no halo or shadow around words.
- **Owner's decision (2026-11-26)**: clear glass for all cards and animations from now on, shown with iOS-style
  white text and with brand ink text; the owner chose **ink text** (so our legibility layer is light porcelain,
  not dark), **no shadows**, and a **liquid, glossy** finish → `glass.py` defaults: strength 0.9, `--liquid 1.0`,
  `--gloss 1.0`, 32 px rim.
- Not taken: Apple's look-alike controls, icons or system UI (never in a Nutrition Hub video).
