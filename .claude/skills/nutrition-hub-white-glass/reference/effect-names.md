# Effect and skill names (what the owner can ask for)

The owner asks for things by these names, for example: *"Free Space style, Word Orbit at the first gesture
(Whey, Creatine), Sticky Text '3–5 g a day', B-roll Cutaways with White Dip, End Card."* Each name maps to the
skill part listed here. Effects marked ✗ are not available because they break the White Glass rules (§5).

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

## Sound

Sound effect names: **thud** (slam), **riser**, **whoosh**, **swish** (white dip), **pop** (card), **tick** (pill),
**glass** (end-card logo). Run with `sfx.py`.

## Colour schemes

White Glass (house), Charcoal Cards, Mint, Mustard, Navy + Lime (`hook-slam.html?scheme=`).

## Tools for the edit

| Name | What it does |
|---|---|
| Timeline | The whole edit in one `edit.json`, checked against the rules and drawn (`timeline.py check`) |
| Timeline Editor | Drag-and-trim page before the final render, with the style locked (`timeline.py edit`) |
| Final Render | Builds the reel from the timeline and runs the quality check (`timeline.py render`) |
| Motion Tracking | Follows the head and hands, and finds gesture moments (`motion_track.py`) |
| Cut-out (Matte) | Plain-wall key, a cut-out video, or ghost-editor's matte (`person_matte.py`) |
| Raw Cut | Best take of each line from a long recording (ghost-editor, on a Mac) |
| B-roll Shot List | What to film in the store (`reference/broll-shot-list.md`) |
| Quality Check | Format, loudness, logo and colours (`qa.py`) |
| WhatsApp Size | Fit under 16 MB (`halfsize` skill) |

## Connected skills and apps

- **In the repo:** nutrition-hub-white-glass, molecular-film, use-3d-software, halfsize, the HyperFrames
  plugin, Blender MCP, OpenChatCut MCP.
- **On the owner's Mac:** ghost-editor (raw cut and matte only).
- **Plugins:** IT Reelsmaker (raw take to reel), Remotion, Motion Reel, ffmpeg-llm, social-media-skills (hooks
  and post captions).
- **Connectors:**
  - WhisperAI (transcripts)
  - Epidemic Sound (music; needs a commercial plan)
  - Clipzi and OpusClip (long video to shorts)
  - ManyMotions and Runway (AI b-roll, only with the owner's OK)

## Not available (they break the White Glass rules)

Zoom-through Cut, Vertigo, Digital Zoom (zoom punches and camera zooms, §5); Paper Cut, Doodle Boil (not the
White Glass look). The owner can change those rules to allow them.
