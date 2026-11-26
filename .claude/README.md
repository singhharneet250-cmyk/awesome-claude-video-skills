# Video toolkit for Nutrition Hub edits

What Claude Code loads in this repo, and why. The brand skill decides the look; everything
else does the heavy lifting under its rules.

## Skills in this repo (`.claude/skills/`)

| Skill | What it adds |
|---|---|
| `nutrition-hub-white-glass` | The Liquid Glass brand and motion system: original logo, palette, Inter type, glass components, motion timings, caption style, footage grade, HTML templates and the render pipeline. 2026-11-26: renamed Liquid Glass in the docs (the skill id is unchanged); real liquid glass over footage (`scripts/glass.py`), 17 motion-kit beats from the owner's references (`templates/motion-kit.html`), a screen insert (`scripts/screen_insert.py`), motion blur (`render.cjs --blur`), and a DaVinci Resolve export (`timeline.py export`). Also `scripts/captions.py` (word timings → on-brand captions), `scripts/qa.py` (automated delivery QA), a routing table for the companions below (SKILL.md §10), and realistic 3D: `templates/molecule-3d.html` (17 supplement molecules as ceramic and frosted-glass models from verified computed conformers, studio light, contact shadow, real-camera motion blur and depth of field) and `templates/product-hero-3d.html` (your real product photo in a 3D studio with shadow, reflection and parallax, label untouched). |
| `molecular-film` | Blender-grade protein and enzyme films from real PDB / AlphaFold structures with the [Molecular_Animation](https://github.com/AmadeusBio-ai/Molecular_Animation) framework (Apache-2.0, pinned commit), given the Liquid Glass look. Needs Blender 5.2 and a GPU, so it runs on your own machine. |
| `use-3d-software` | Exact Blender 5.x and three.js steps for realistic materials, glass, lighting, HDRI, depth of field and headless renders. Vendored from [codepawl/creator-generalist](https://github.com/codepawl/creator-generalist) (MIT). |
| `cinetic` | Premium launch, product and promo films from code, held to measured gates (words in the middle, one element carried, hidden cuts, copy check, forensics). Vendored from [Leonxlnx/cinetic](https://github.com/Leonxlnx/cinetic) (MIT) @ f4bbfc8, found on prompt-motion.com; its description defers to the Liquid Glass skill. |
| `product-film` | A product film built on the brand's own design system and cut to music on measured beats (Remotion). Vendored from [Rieranthony/product-film-skill](https://github.com/Rieranthony/product-film-skill) (MIT) @ fe11efc. |
| `camera-3d-captions` | Captions in 3D around a talking head: depth groups, a hero word behind the head, a ring of words (HyperFrames). Vendored from [heygen-com/hyperframes-community-skills](https://github.com/heygen-com/hyperframes-community-skills) (Apache-2.0) @ ba7a0bb. No camera zooms on Nutrition Hub reels. |
| `halfsize` | Compress a finished video to an exact size cap (WhatsApp 16 MB, Gmail, Outlook) and report the measured quality. Vendored from [YKLovePython/halfsize](https://github.com/YKLovePython/halfsize) (MIT), pinned to v0.2.0. See `skills/halfsize/SOURCE.md`. |

## Project plugin (`.claude/settings.json`)

| Plugin | What it adds |
|---|---|
| `hyperframes@hyperframes` | HeyGen's HyperFrames skills (Apache-2.0): editable HTML-to-video projects, the CLI, the block registry, media, captions and Remotion ports. Claude Code offers to install it when you open this repo. Its main skill asks before sending HeyGen a usage note; say no to skip. |

## Project MCP servers (`.mcp.json` at the repo root)

| Server | What it adds |
|---|---|
| `openchatcut` | [OpenChatCut](https://github.com/0xsline/OpenChatCut) (AGPL-3.0, use v0.2.17), a local video editor with a multi-track timeline. Claude Code edits an open project through a draft that you approve inside OpenChatCut (`approvalMode: "manual"`); it can't export, generate, delete or publish. No remote telemetry was found; AI calls go only to services you add keys for. It needs OpenChatCut running on your computer (`localhost:5199`): see `skills/nutrition-hub-white-glass/reference/openchatcut.md`. Nothing of its code is copied into this repo. |
| `blender` | [MCP for Blender](https://github.com/ahujasid/mcp-for-blender) (MIT), pinned to 2.2.7. Claude Code drives a running Blender on your computer: it reads the scene, builds and lights it with Blender Python, looks through the camera and renders. Telemetry is off (`DISABLE_TELEMETRY`) and safe mode is on (scripts can't touch files, programs or the network). It needs Blender, uv and the add-on on your computer: see `skills/nutrition-hub-white-glass/reference/blender-mcp.md`. Claude Code asks you to approve it the first time you open the repo. In a cloud session it has no Blender to reach. |

## Companion installed on your own computer

| Tool | What it adds |
|---|---|
| [ghost-editor](https://github.com/kurbaitaev/ghost-editor) (MIT, commit `d71bdb6`) | Added at the owner's request on 2026-11-25, after first being left out. Only two parts are used: its raw cut (the best take of each line from a long multi-take recording, voice smoothed, faces checked) and its BiRefNet person matte for the frame escape. Its styles, memes, stock fetching and Google B-roll check are not used. It needs an Apple-silicon Mac: see `skills/nutrition-hub-white-glass/reference/ghost-editor.md`. Nothing of it is copied into this repo. |

## Plugins enabled from the Anthropic Directory

These were added from the plugin catalog on claude.ai, not from files in this repo:

- **IT Reelsmaker**: raw talking-head footage → finished 9:16 reel (pause and retake cuts, word-timed subtitles, face-aware layout, −14 LUFS).
- **Remotion**: the official Remotion skills.
- **Motion Reel**: product films and showreels rendered from code, with a contact-sheet critique loop.
- **ffmpeg-llm**: natural-language → FFmpeg commands.

## Considered and left out

From the 526 repos in `data/skills.json`, these were read and not added because they fight
the Liquid Glass rules or duplicate a plugin above:

- `Tejashmakwana/motionmaxxing`: bans kickers, centred stat callouts, on-screen source notes and fades, which are core Liquid Glass components.
- `hughminhphan/motion-kit`: declares its motion rules override every other skill.
- `iart-ai/tiktok-video-skills`: recommends zoom punches, whip pans and spring "pop" captions, all banned here.
- `louisedesadeleer/cut-video`: macOS/Homebrew install; IT Reelsmaker cuts pauses and retakes.
- `remotion-dev/skills`: no licence file to copy under; the official Remotion plugin is used instead.
- `mromidev/claude-blender-skills`: realistic Blender drone, forest and car films; Windows-centred scripts and not supplement content. `use-3d-software` covers the Blender craft.
- `sunxiayi/make-blender-education-video-skill`: forces its own Kokoro voice, Arial subtitles and English-only narration, against your recorded Hinglish VO and Inter captions.
- The rest of `codepawl/creator-generalist` (characters, games, cutaways): renders through its own Crucible engine and MCP server; only its `use-3d-software` tool skill was taken.
