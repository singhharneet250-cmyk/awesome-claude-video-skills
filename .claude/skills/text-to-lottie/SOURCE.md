# Source

Vendored on 2026-11-27 at the owner's request (from agentskillshub.top/best/claude-video-skills: "Install the best ones",
Lottie chosen).

- Upstream: https://github.com/diffusionstudio/lottie @ `3c72912` (2026-07-25): the skill from `skills/text-to-lottie/`,
  and the repository's Skia Skottie player app copied into `player/`
- Licence: MIT (`LICENSE` and `player/LICENSE`, unchanged)
- Read before vendoring: no telemetry. The player is a local Vite app (`npm install`, `npm run dev`); `npm install`
  fetches its packages from the npm registry.

## Use for Nutrition Hub

Lottie files are small vector animations (icons, check marks, loaders, stat counters, lower thirds) that play in apps,
on websites and in Remotion or HyperFrames. Brand rules still apply: brand palette with Logo Red #D30204, critically
damped motion (no bounce or overshoot), no shadows beside words, and the logo is never redrawn, animated or recoloured
(use the original file in a video layer instead).

## Not included here (and why)

| Left out | Why |
|---|---|
| `assets/demo-1.gif`, `assets/demo-2.gif`, `assets/header.gif` (about 4 MB) | pictures for the upstream README only |

## Changes in this copy

- `SKILL.md`: the frontmatter description starts with the companion note.
- `references/player-contract.md`: one line saying the player is vendored at `player/` in this folder.
