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
  anything that looks like a template. (The owner has since asked for gradient type and gradient glass in the
  brand's own colours, 2026-11-26: SKILL.md §2. The rest still applies.)
- Music for those films: royalty-free tracks around 120 BPM, often Mixkit.

## The 16 tested films in the owner's list (owner, 2026-11-27: "double check the links and its reference video")

The owner's repo README (`awesome-claude-video-skills`) links 525 skill repos and a test in which 16 of them, and
Claude Code with no skill, each made the same 15-second promo. The films, prompts and scripts are public in
github.com/zhuyansen/agent-skills-hub (`ops/video-runs/`, films in `frontend/public/best-runs/video/`); all 18 were
watched frame by frame on 2026-11-27. Links checked the same day: 529 of 530 linked repos answer; the one that is gone
(`luminexlabs-io/antigravity-remotion-skill`) was taken out of both READMEs and `data/skills.json`. The README's
preview images and in-page links all resolve. Later the same day (owner: "both things") the list was refreshed from
upstream zhuyansen/awesome-claude-video-skills (its 2026-11-26 update: 561 repos, 40 new); upstream had dropped that
repo too, and all 565 linked repos, the preview images and the in-page links were checked again. (`results.json` there also has a 17th run, OpenMotion, 12.9 min, not yet
on the published page.)

What separates the films is not whether they work (all passed the same four checks) but one strong idea each:

| Film | What it does well | What we took |
|---|---|---|
| explainroo (fastest, 2 min) | Words write on one at a time; the key word or number in the accent colour; "2,400 beaches" becomes a field of 2,400 pins | **Dot Grid** (`dots`): a sourced share as 100 dots filling in Logo Red; the key word in red was already our rule |
| OpenMontage | "Good · Fair · Stay out" as three full-height colour panels; the number underlined | **Three Panels** (`panels3`): three choices as full bands, the picked one turns Logo Red (brand colours, not traffic-light colours) |
| onetake | One drop of water carries the whole film: ripple, wave line, status dot, the full stop of the logo | Already ours: one red dot carried through a beat (motion kit, Big Scroll) and Cinetic's "one element carried" |
| motion-video-kit | Big, bold, left-aligned type and big icons: the most readable at phone size | Already ours: headline sizes in §3; keep body lines at 48 px or more on 9:16 |
| the 6 "default" films (remotion skills, lottie, hypit, …) | Deep teal gradient, small white centred type, sine waves: what Claude makes unprompted | A warning sign: if a frame could belong to any brand, it is the default. Ours is white glass, ink and Logo Red |

The test also measured "held frames" (pairs of frames sampled twice a second that barely change): 0–10 % for the
lively films, 34–48 % for the static ones. `qa.py`'s rhythm check (no frozen stretch over 1.6 s for graphics) keeps
ours lively; look at the 2 fps contact sheet as the test did.

## Skills installed in this repo (read in full and checked first)

| Skill | From | Licence | Use for Nutrition Hub |
|---|---|---|---|
| `cinetic` | github.com/Leonxlnx/cinetic @ f4bbfc8 | MIT | Launch, product and promo films from code, held to measured gates (words in the middle, one element carried, hidden cuts, copy check, `forensics.py`). Its own rule says a supplied brand wins, so its "no orange", "no serif" and "no glassmorphism" house bans don't apply to us. |
| `product-film` | github.com/Rieranthony/product-film-skill @ fe11efc | MIT | A product film on the brand's design system, cut to music on measured beats (`scripts/beats.py`), with stills and verify steps |
| `camera-3d-captions` | github.com/heygen-com/hyperframes-community-skills @ ba7a0bb | Apache-2.0 | Captions in depth around a talking head (groups at depths, a hero word behind the head, a ring of words). Its whip-ins and push-ins are camera zooms: not on our reels. |
| `open-generative-ai` | github.com/Anil-matcha/Open-Generative-AI @ 7746dd2 (the app, described) + github.com/SamurAIGPT/muapi-skills @ 1dd7527 (core scripts, vendored) | MIT | AI images, video and music from 600+ models through MuAPI (paid credits, owner's OK first). Face swap, dress change and product shots are blocked in the scripts; logo, celebrity and try-on recipes were left out. Owner, 2026-11-28: "Add open generative ai from github". |

Each description says to load `nutrition-hub-white-glass` first. Python packages they need were installed in this
session (scipy, soundfile, pyloudnorm, librosa, fonttools, brotli, uharfbuzz, imageio-ffmpeg, opentimelineio); a fresh
cloud session reinstalls them with `pip install -r` of each skill's requirements, or from a saved setup script.

Not installed: `html-demo` (MengTo/skills, app demos in a Mac window: Nutrition Hub has no app), Taste Skill
(dashboards), the history-film skill, and the other HyperFrames community skills (day-in-my-life, duo, p5 paint,
Strudel music, X posting licence).

## Tools from the owner's screenshots (@thebotfather.ai, 2026-11-26)

| Tool | What it is | Decision |
|---|---|---|
| Remotion Skills (remotion.dev/skills) | Official skills for videos in React | **Added to the repo** (owner, 2026-11-27: "add remotion plugin"): `.claude/settings.json` enables `remotion@remotion` from the `remotion-dev/claude-code-plugin` marketplace (plugin MIT, 4.0.528), so every session on this repo has the `remotion:*` skills, not only the owner's account. Remotion itself is free for individuals and companies of up to 3 people; larger companies need a Remotion company licence. Brand rules still win (SKILL.md §10). |
| pen.dev (formerly Pencil) | A free design canvas inside VS Code or Cursor that Claude Code reads and draws on through its own MCP, with `.pen` files next to the code | Useful for designing thumbnails and title cards by hand. Desktop only: install it on the owner's computer; its MCP registers itself while it runs (check with `/mcp`). |
| Rive MCP (rive.app) | Claude builds Rive animations and state machines in the Rive Editor | Desktop editor (macOS, Windows) with a local server: `claude mcp add --transport http rive http://127.0.0.1:9791/mcp` while the editor is open. Good for interactive or looping UI pieces; for a reel, export a video. Never redraw the logo in it. |
| Mobbin MCP (mobbin.com/mcp) | 600,000+ real app screens for design reference | Not added: it needs a paid Mobbin plan and Nutrition Hub has no app. |
| React Bits (reactbits.dev) | 165+ animated text effects, backgrounds and components for React | Not installed (no React project here; licence MIT + Commons Clause: free to use in videos, not to resell). Its text effects map to ours: Count Up → Count-up Bars, Rotating Text → Word Wheel, Scroll Velocity → Big Scroll, Blur Text → Tracking Reveal. Its colourful backgrounds (Aurora, Silk) are off-palette. |

## Sherlock (owner, 2026-11-26: "Add sherlock")

Two tools share the name; the owner didn't pick, so the well-known one was added:

- **Added: Sherlock, the username finder** (github.com/sherlock-project/sherlock, MIT, 0.16.2). It checks whether
  an account with a given name exists on 400+ sites. For Nutrition Hub: see where `@nutritionhubkhanna` is free or
  taken before claiming it, and spot look-alike accounts (`nutritionhub_khanna`, `nutritionhub.khanna`, ...) that
  could be impersonating the shop. `bash scripts/handle_check.sh` installs it in its own venv on first use (the system
  pip can't build its `stem` dependency on Debian Python) and checks Instagram, YouTube, TikTok, Threads, X,
  Pinterest, Snapchat, LinkedIn, Reddit, Telegram and GitHub, writing a CSV per name. Only for the brand's own handles
  and look-alikes, never to look up a private person; a hit means a name exists, not who runs it. In this cloud
  environment only GitHub answered (the social platforms are not allowed hosts); run it on the owner's computer, or
  allow those hosts first.
- **Not added: Sherlock AI plugin** (github.com/proyecto26/sherlock-ai-plugin, MIT): six research skills (deep
  research reports, paper and PDF analysis with a MinerU key, paper-to-comic, diagrams, Gemini image generation
  with a Google sign-in). Its deep research could help find sources for supplement facts; add it if the owner asks
  (read and scan it first, like the other companions).

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
  `--variant clear` (the house default since the owner's choice, 2026-11-26, with a porcelain legibility layer for ink
  text) and `--variant regular` (the frosted fallback).
- **Highlights respond to movement** → the rim light turns a little as a panel moves.
- **Concentric shapes**, and **never glass on glass** → SKILL.md §4 A.
- **iOS 27 (WWDC 2026)** refined Liquid Glass after a year of readability complaints: a system slider from fully
  opaque to completely clear, a more legible default, new rendering, and adaptation to Reduce Transparency and
  Increase Contrast → `glass.py --strength` (0 opaque … 1 clear), house default 0.9 (clear) since 2026-11-26.
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
