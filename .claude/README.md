# Video toolkit for Nutrition Hub edits

What Claude Code loads in this repo, and why. The brand skill decides the look; everything
else does the heavy lifting under its rules.

## Skills in this repo (`.claude/skills/`)

| Skill | What it adds |
|---|---|
| `nutrition-hub-white-glass` | The White Glass brand and motion system: original logo, palette, Inter type, glass components, motion timings, caption style, footage grade, HTML templates and the render pipeline. Now also `scripts/captions.py` (word timings → on-brand captions), `scripts/qa.py` (automated delivery QA) and a routing table for the companions below (SKILL.md §10). |
| `halfsize` | Compress a finished video to an exact size cap (WhatsApp 16 MB, Gmail, Outlook) and report the measured quality. Vendored from [YKLovePython/halfsize](https://github.com/YKLovePython/halfsize) (MIT), pinned to v0.2.0. See `skills/halfsize/SOURCE.md`. |

## Project plugin (`.claude/settings.json`)

| Plugin | What it adds |
|---|---|
| `hyperframes@hyperframes` | HeyGen's HyperFrames skills (Apache-2.0): editable HTML-to-video projects, the CLI, the block registry, media, captions and Remotion ports. Claude Code offers to install it when you open this repo. Its main skill asks before sending HeyGen a usage note; say no to skip. |

## Plugins enabled from the Anthropic Directory

These were added from the plugin catalog on claude.ai, not from files in this repo:

- **IT Reelsmaker**: raw talking-head footage → finished 9:16 reel (pause and retake cuts, word-timed subtitles, face-aware layout, −14 LUFS).
- **Remotion**: the official Remotion skills.
- **Motion Reel**: product films and showreels rendered from code, with a contact-sheet critique loop.
- **ffmpeg-llm**: natural-language → FFmpeg commands.

## Considered and left out

From the 526 repos in `data/skills.json`, these were read and not added because they fight
the White Glass rules or duplicate a plugin above:

- `Tejashmakwana/motionmaxxing`: bans kickers, centred stat callouts, on-screen source notes and fades, which are core White Glass components.
- `hughminhphan/motion-kit`: declares its motion rules override every other skill.
- `iart-ai/tiktok-video-skills`: recommends zoom punches, whip pans and spring "pop" captions, all banned here.
- `kurbaitaev/ghost-editor`: Apple-silicon only, sends frames to Google; IT Reelsmaker covers the same job.
- `louisedesadeleer/cut-video`: macOS/Homebrew install; IT Reelsmaker cuts pauses and retakes.
- `remotion-dev/skills`: no licence file to copy under; the official Remotion plugin is used instead.
