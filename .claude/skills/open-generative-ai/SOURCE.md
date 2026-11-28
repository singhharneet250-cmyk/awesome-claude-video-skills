# Source

Added on 2026-11-28 at the owner's request ("Add open generative ai from github").

- **Open Generative AI:** https://github.com/Anil-matcha/Open-Generative-AI @ `7746dd2` (2026-11-25), MIT
  (`LICENSE-Open-Generative-AI`). A web and desktop studio app over MuAPI. Read: README, `project_knowledge.md`,
  the file tree. The app itself is not copied here (see below); `SKILL.md` describes how the owner uses it.
- **MuAPI scripts:** https://github.com/SamurAIGPT/muapi-skills @ `1dd7527` (2026-10-02), MIT (`LICENSE-muapi-skills`),
  linked from the Open Generative AI README as its agent skills. Copied into `muapi/` with the upstream layout, so
  the scripts' relative paths still work. Read and scanned before vendoring: plain bash with `curl` and `jq` against
  `https://api.muapi.ai/api/v1`; no telemetry, no installers piped to a shell.

## Copied

| Upstream (`skills/…`) | Here (`muapi/…`) |
|---|---|
| `core/platform`, `core/media`, `core/edit` | the same |
| `muapi-models/SKILL.md` | `muapi-models/README.md` |
| `library/motion/cinema-director` | the same |
| `schema_data.json` | the same (model snapshot; prices and names are read live) |

## Changed (so the owner's rules hold, and nothing unsafe runs)

- Every nested `SKILL.md` was renamed `README.md`: only `open-generative-ai/SKILL.md` is a skill here.
- The line `if [ -f ".env" ]; then source .env …; fi` was removed from all 8 scripts that had it: sourcing a file
  from whatever folder a script runs in executes that file. The key comes from the environment (a network secret).
- `core/edit/video-effects.sh` refuses `face-swap`, `dress-change` and `dance`; `core/edit/enhance-image.sh` refuses
  `face-swap`, `skin-enhance`, `product-shot` and `product-photo` (exit 3), before any network call. They change a
  real person's face or body, or regenerate a product: never for Nutrition Hub.
- `.gitignore` keeps `muapi/media_outputs/` (generated files) and any `.env` out of this public repo.

## Not included (and why)

| Left out | Why |
|---|---|
| The Open Generative AI app source (Next.js, Electron, 32 MB) | an app, not a skill; the owner uses the hosted studio or the desktop installer |
| `library/visual/logo-creator`, `logo-generator`, `logo-branding`, `brand-kit`, `3d-logo-animation` | the logo is the original file only, never redrawn (standing decision 1) |
| `selfie-with-celebrities`, `fashion-try-on`, `ugc-lifestyle-try-on`, `couple-grid-creator`, `action-figure-generator`, `talking-baby-video` | fake or altered real people |
| `amazon-product-listing`, `product-*` videos, `giant-product-showcase`, `jewelry-product-video` | products and labels come from real photos only (§4 D) |
| `edit/ai-clipping`, `social/youtube-shorts` | they upload the owner's full video to MuAPI; `claude-shorts` does this locally |
| The other ~40 recipes, `muapi-chat-agents`, `media_outputs/` samples | not needed for Nutrition Hub reels; can be added later on request |
