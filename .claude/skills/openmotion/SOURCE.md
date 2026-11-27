# Source

Vendored on 2026-11-27 at the owner's request (from agentskillshub.top/best/claude-video-skills: "Install the best ones",
OpenMotion chosen). This SOURCE note covers all nine OpenMotion folders in `.claude/skills/`:
`openmotion`, `openmotion-design`, `-director`, `-game`, `-media`, `-production`, `-recreate`, `-template-to-video`,
`-video-to-template`.

- Upstream: https://github.com/nexu-io/openmotion @ `49f69b4` (2026-11-27), folder `skills/`
- Licence: Apache-2.0 (`LICENSE`, copied unchanged into each folder). `openmotion-game` also carries a handbook ported
  from higgsfield-ai/skills under MIT (`LICENSE-HIGGSFIELD`, `PROVENANCE.md`, unchanged).
- Read and scanned before vendoring: the skills are instructions only, with a few local helper scripts; no telemetry.

## How it works, and what that means for Nutrition Hub

These skills drive the hosted **OpenMotion Cloud** through its MCP server (`https://app.open-design.ai/mcp`, OAuth 2.1
sign-in or a workspace token). The editing, rendering and AI generation (images, video, music, voice) happen in that
cloud, and generation spends credits.

- The owner's footage, voice and logo would be uploaded to that service: use it only with the owner's OK
  (standing decision 10), and AI voice, AI b-roll or anything that spends credits only with the owner's OK (decision 8).
- The sign-in needs a browser, so connect it from the owner's own Claude app or computer. This cloud session cannot
  reach `app.open-design.ai` (not on the network allowlist), so here the skills are reference only.
- Whatever OpenMotion makes still follows `nutrition-hub-white-glass`: original logo, real background, clear glass,
  Logo Red accent, Roman Punjabi captions, -14 LUFS, sourced claims.

## Not included here (and why)

| Left out | Why |
|---|---|
| The OpenMotion app itself (`src/`, `server.ts`, `studio/`, `desktop/`, `gateway/`, `packages/`, `deploy/`) | it is the cloud product, not a skill; the skills talk to the hosted service |
| `library/` (about 400 design and motion style skills) and `template-library/` | served by OpenMotion Cloud through its catalog tools; too large to copy and not needed locally |
| `.agents/skills/`, `.codex-plugin/`, docs, tests, translations | upstream development material |

## Changes in this copy

- Each `SKILL.md`: the frontmatter description starts with the companion note above (load the brand skill first,
  owner's OK for the cloud and for credits). Everything else is upstream as-is.
