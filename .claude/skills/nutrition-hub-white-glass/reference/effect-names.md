# Effect and skill names (what the owner can ask for)

The owner asks for things by these names, for example: *"Free Space style, Word Orbit at the first gesture
(Whey, Creatine), Sticky Text '3–5 g a day', B-roll Cutaways with White Dip, End Card."* Each name maps to the
skill part listed here. Effects marked ✗ are not available because they break the Liquid Glass rules (§5).

## Talking-head styles

| Name | What it is | Where |
|---|---|---|
| Free Space | Captions sit in the empty space around the speaker | `captions.py --position auto` (§6) |
| Mic Blur | Desk-mic shot, captions at mic height, bottom blur band | `--position mic` + `bottom_blur.py` (R6) |
| Chest Line | One small caption at collarbone height | `--position chest` (R5) |
| Lockup | A big word with small words around it, beside the head | can be built (Skill Menu #1) |

## Effects around the speaker

| Name | What it is | Where |
|---|---|---|
| Orbit | White spheres (one orange) circle the head | `fx.py orbit` |
| Word Orbit | Word chips circle at chin level, passing behind the head | `fx.py orbit --words … --tilt 65` |
| Frame Escape (Frame Break) | The picture shrinks into a frame while the head and hands stay outside | `fx.py escape` |
| Depth Scatter | One big word behind the head, one in front | `fx.py scatter` |
| Sticky Text | A sticker that follows the speaker | `fx.py sticky` |
| Green Screen | The room behind becomes the stage, a blur or a clip | `fx.py bgswap` |

## Overlays

| Name | What it is | Where |
|---|---|---|
| Headline Wall | Real headlines on cards around the speaker | `templates/headline-wall.html` |
| Phone Mockup | A phone beside the head with a screenshot or photo | `templates/phone-mockup.html` |
| UI World | Glass app cards act out a task | `templates/ui-world.html` |
| Chat Takeover | A chat: pick a contact, type, send, reply (above the head or full screen) | `templates/chat-takeover.html` |
| Comment Bubble | A comment types the keyword, then a reply with "Open link" | `chat-takeover.html?layout=comment` |
| Data Callout | A number with its unit and source on a glass card | `templates/overlay-callout.html` |
| Slam Hook | A big condensed word slams in, then a line ending on a serif accent | `templates/hook-slam.html` |

## Cuts and transitions

| Name | What it is | Where |
|---|---|---|
| B-roll Cutaway | Cut to b-roll on the word it shows, then back | `broll.py` |
| White Dip | A 0.4 s dip to white, into b-roll or into the end card | `broll.py --transition white` |
| Soft Dissolve | A 0.25 s dissolve | `broll.py --transition soft` |
| Before + After | A light bar wipes from before to after (edits and products only) | `fx.py wipe` |
| Watch the Line | Before + After in R18's attention style: the line keeps swinging with a glass handle, labels and a headline pill on top | `fx.py wipe --mode line --words "Before,After" --text "Same reel. Watch the line."` |
| Pull-back Reveal | The picture pulls back into an editing screen | `fx.py pullback` |

## Captions and type

| Name | What it is | Where |
|---|---|---|
| Matched Captions | Bare words, coloured to suit the video | `captions.py --match` |
| Serif Accent | One italic serif word per caption | `captions.py --serif-words` |
| Bottom Blur Band | The bottom of the frame softly blurs, only when needed | `bottom_blur.py --plan` |

## 3D, product and ending

| Name | What it is | Where |
|---|---|---|
| 3D Molecule | Creatine, caffeine and 15 more as ceramic and glass models | `templates/molecule-3d.html` |
| Product Hero | The real product photo in a 3D studio | `templates/product-hero-3d.html` |
| End Card | The original logo, contact details and call to action | `templates/reel-9x16.html --from 8.15` |
| Protein Film | A protein or enzyme from a real structure (GPU computer) | `molecular-film` skill |

## Motion kit (from R8–R18)

One template, `templates/motion-kit.html?scene=NAME`. Ask for them by name, for example: *"Word Wheel landing on
Creatine at 8 s, then Toggle List over me: Seal intact, Batch code scanned."* Full-screen beats are cut in like
b-roll (`"template"` in `edit.json`); overlays sit over the speaker in real liquid glass.

| Name | Scene | What it is | Main parameters |
|---|---|---|---|
| Word Wheel | `wheel` | A list rolls like a slot reel and lands on one word, with the orange dot | `words`, `pick`, `kicker`, `note` |
| Menu Switch | `menu` | A word list steps down; the dot travels; a glass card swaps per item | `items=Title\|line;…`, `imgs`, `step` |
| Count-up Bars | `count` | A big number counts up while bars rise (last bar orange) | `value`, `unit`, `decimals`, `label`, `source` (required: a real source) |
| Toggle List | `toggle` | Switches flip on one by one in a glass card (overlay) | `items`, `title`, `slot=top` |
| Word Split | `split` | A line opens and a check, chip or photo springs into the gap | `text=Read the\|label`, `chip`, `img`, `under` |
| Highlighter Sweep | `highlight` | Words rise, then an orange bar sweeps behind *the phrase* | `text=line\|*marked phrase*` |
| Prompt Box | `prompt` | A question types into a pill, a cursor clicks send, an answer card rises (overlay) | `q`, `a` |
| Shape Morph | `morph` | One ink shape becomes check → button → slider → toggle (→ chart), never cut | `states`, `label`, `hold` |
| Big Scroll | `scroll` | One huge line slides across; its full stop is the orange dot | `text`, `kicker`, `size` |
| Text Ring | `ring` | Words run round a slowly turning circle around a product photo | `text`, `img`, `caption` |
| Progress Pill | `progress` | A pill fills in steps (18% … 92% … 100%) then becomes a check (overlay) | `label`, `done` |
| Spatial Panels | `panels` | Glass cards float at the sides in 3D, turned toward the speaker (overlay) | `items`, `imgs`, `text`, `dur` |
| Photo Strip | `strip` | A column of photos scrolls up between two words | `imgs`, `left`, `right` |
| Echo Stack | `echo` | The line lands, faint copies spread above and below (photo optional, washed white) | `text=LINE\|LINE`, `img` |
| Tracking Reveal | `tracking` | Small capitals slowly open their spacing; never still (overlay: in a chip) | `text`, `dur` |
| Comment Banner | `banner` | Two labels at the top: a topic tag and "Comment KEYWORD for the full guide" (overlay) | `top`, `line=Comment *WORD* …`, `dur` |
| Comment CTA | `cta` | A glass card, an orange "Comment KEYWORD" pill and your handle (R18's ending; overlay) | `title`, `sub`, `keyword`, `handle`, `dur` |
| Glass Lens | `lens` | A round glass magnifier glides to a spot in your footage and magnifies it (overlay; give it `"glass_lens": 0.35`) | `x`, `y`, `to`, `size`, `label`, `from`, `dur` |
| Photo Scatter | `photos` | A headline in the middle; real photos pop in around it and drift outward | `imgs`, `text` |

For a TV or laptop screen, render any scene at 16:9 with `--size 1920x1080`.

## Glass, screens and finish

| Name | What it is | Where |
|---|---|---|
| Liquid Glass | Glass panels over footage that really bend and light the video behind them; panels "materialize" | `glass.py` (automatic in `timeline.py render`; `"glass": "flat"` turns it off) |
| Clear Glass | The house default since 2026-11-26: see-through, ink text, no shadows | `glass.py` (default; `--variant regular` for the old frosted look) |
| Liquid Edge | The thick rounded edge bends the picture like a drop of water | `glass.py --liquid 1.0` (0 = flat slab) |
| Glossy Glass | Rim specular + bloom, a far-edge line, fresnel edges and a soft curved sheen | `glass.py --gloss 1.0` (0 = rim light only) |
| Lens Cards | Every glass card is a convex lens: what is behind it is magnified ~1.14× in the middle, easing to the edge | `glass.py --lens 0.12` (default; 0 = flat), `"glass_lens"` per overlay |
| Gradient Glass | Glass tinted warm peach (lit corner) to cool ice (far corner), filtering the light like coloured glass | `glass.py --grad 1.0` (default; 0 = plain) |
| Gradient Type | Ink, orange and slate text as top-to-bottom gradients, repeated per line | automatic in `render.cjs` (`--flat-type` = solid); `fx.text_grad` for chips |
| Glass Strength | The iOS 27-style slider: 0 opaque porcelain … 0.4 frosted … 0.9 house default (clear) … 1 completely clear | `glass.py --strength 0.6`, or `"glass_strength"` on an overlay |
| Screen Insert | A beat or clip playing on a real TV, laptop or monitor in your footage | `screen_insert.py plate.mp4 beat.mp4 out.mp4` (`--detect dark`, `--corners`, `--track`) |
| Motion Blur | Real motion blur on rendered graphics (4 sub-frames, 180° shutter) | `render.cjs --blur 4`, or `"motion_blur": 4` in `edit.json` |
| Remove Background | Only when asked (off by default, owner 2026-11-26): you on the Liquid Glass stage (or a blur, white, or your own picture or clip), no room behind | `person_cutout.py take.mp4 out.mp4 --matte-out matte.mp4` |
| Clear Voice | Clearer, natural voice: less mud, more presence, light denoise | `voice.py take.mp4 clean.mp4` (`--ab 0-10` to compare) |
| Word Bridge | A word stays on screen across a cut (R8's match cut) | a Tracking Reveal or a caption that spans the b-roll cut |

## Sound

Sound effect names: **thud** (slam), **riser**, **whoosh**, **swish** (white dip), **pop** (card), **tick** (pill),
**glass** (end-card logo). Run with `sfx.py`.

## Colour schemes

Liquid Glass (house, `?scheme=white-glass`), Charcoal Cards (`charcoal`), Mint (`mint`), Mustard (`mustard`), Navy + Lime (`navy-lime`): `hook-slam.html?scheme=`.
The colours of R8–R16 (warm off-white, peach and mint, lavender, forest green, neon) are recorded in
`reference/style-references.md` for reference; they are not Nutrition Hub schemes unless the owner adds one.

## Tools for the edit

| Name | What it does |
|---|---|
| Timeline | The whole edit in one `edit.json`, checked against the rules and drawn (`timeline.py check`) |
| Timeline Editor | Drag-and-trim page before the final render, with the style locked (`timeline.py edit`) |
| Final Render | Builds the reel from the timeline and runs the quality check (`timeline.py render`) |
| Export to Resolve | The same edit as a real timeline for DaVinci Resolve, Premiere or Kdenlive, plus captions as SRT (`timeline.py export`) |
| Rhythm Check | Warns when nothing new appears for over 6 s (`timeline.py check`) and on frozen stretches (`qa.py`) |
| Motion Tracking | Follows the head and hands, and finds gesture moments (`motion_track.py`) |
| Cut-out (Matte) | Plain-wall key, a cut-out video, or ghost-editor's matte (`person_matte.py`) |
| Raw Cut | Best take of each line from a long recording (ghost-editor, on a Mac) |
| B-roll Shot List | What to film in the store (`reference/broll-shot-list.md`) |
| Quality Check | Format, loudness, logo and colours (`qa.py`) |
| WhatsApp Size | Fit under 16 MB (`halfsize` skill) |

## Connected skills and apps

- **In the repo:** nutrition-hub-white-glass (the Liquid Glass system), molecular-film, use-3d-software, halfsize,
  the HyperFrames plugin, Blender MCP, OpenChatCut MCP, and three skills from prompt-motion.com: **Cinetic**
  (premium launch and promo films with measured gates), **Product Film** (a product film cut to music on measured
  beats) and **3D Camera Captions** (captions in depth around a talking head; no camera zooms on our reels).
- **Ideas library:** prompt-motion.com (240 Claude motion videos with their prompts; `reference/learned-tools.md`).
- **On the owner's computer, if wanted:** DaVinci Resolve (opens `timeline.py export`), pen.dev (design canvas
  with an MCP), Rive (Rive Editor MCP). Details and set-up in `reference/learned-tools.md`.
- **Already on the account:** the Remotion skills (synced as the Remotion plugin).
- **On the owner's Mac:** ghost-editor (raw cut and matte only).
- **Plugins:** IT Reelsmaker (raw take to reel), Remotion, Motion Reel, ffmpeg-llm, social-media-skills (hooks
  and post captions).
- **Connectors:**
  - WhisperAI (transcripts)
  - Epidemic Sound (music; needs a commercial plan)
  - Clipzi and OpusClip (long video to shorts)
  - ManyMotions and Runway (AI b-roll, only with the owner's OK)

## Not available (they break the Liquid Glass rules)

Zoom-through Cut, Vertigo, Digital Zoom (zoom punches and camera zooms, §5); Paper Cut, Doodle Boil (not the
Liquid Glass look); UI Tunnel fly-through (R11) and Dock Zoom (R14) (camera zooms); Neon Glow (R9, R13), Gradient
Smear (R12) and Pixel Sparkles (R10) (off-palette). The owner can change those rules to allow them.
