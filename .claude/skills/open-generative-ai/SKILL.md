---
name: open-generative-ai
description: "Companion skill: Open Generative AI (github.com/Anil-matcha/Open-Generative-AI @ 7746dd2, MIT) and the MuAPI core scripts from github.com/SamurAIGPT/muapi-skills @ 1dd7527 (MIT). AI image, video and music generation across 600+ models (Flux, Midjourney, Nano Banana, Kling, Veo, Sora, Seedance, Hailuo, Wan) through one paid API, MuAPI (api.muapi.ai). Every generation spends the owner's MuAPI credits and sends the prompt and any reference file to MuAPI, so use it only with the owner's OK for that job. For any Nutrition Hub video, load nutrition-hub-white-glass first: its owner's standing decisions win (never the logo, products, labels, results or a real person's face or body; disclose AI). Use when the owner asks for Open Generative AI, MuAPI or an AI-generated still or clip (b-roll, a background plate, a texture, a thumbnail element)."
---

# Open Generative AI (MuAPI)

Added on 2026-11-28 at the owner's request ("Add open generative ai from github"). Provenance and what was left out:
`SOURCE.md`.

## What it is

- **Open Generative AI** is an open-source studio app (web and desktop, MIT) with 14 studios (Image, Video, Audio,
  Lip Sync, Cinema, Workflows…) over **600+ models**. It is a front end: almost every model runs on **MuAPI**
  (`api.muapi.ai`), a paid, credit-based API. The app is free; the generations are not.
- **Local models** (desktop app only, no credits): sd.cpp for images (SD 1.5, SDXL, Z-Image, bundled) and Wan2GP for
  video (the owner installs it on a computer with an NVIDIA or AMD GPU; about 8 GB VRAM for the lightest model).
- The upstream README calls it "uncensored". That changes nothing here: Nutrition Hub's rules below apply to every model.

## The rules for AI media (from nutrition-hub-white-glass, the owner's standing decisions)

1. **Ask first.** Licensed music, AI voice, AI b-roll or anything that spends credits only with the owner's OK
   (decision 10), for that job, with the model and an estimated cost (`muapi/muapi-models/README.md` shows prices).
2. **Never generate:** the logo (original file only), a product, pack or label (real photos only), a real person's
   face or body, celebrities, results or before-and-after, fake news, documents or screenshots, health claims in
   generated text. The scripts block face swap, dress change, dance, skin enhance and product shots (exit 3).
3. **Lip sync and AI voice** on the owner's own footage only with the owner's explicit OK for that video.
4. **Disclose it.** Realistic AI footage: turn on Instagram's "AI info" label and YouTube's "Altered or synthetic
   content: Yes". Never show AI footage as real store footage.
5. **Good uses:** generic b-roll the owner can't film (sunlight through an office window, a desk at dusk, vegetables,
   fruit and whole grains on a table, a city street at rush hour, abstract light), background plates and textures
   for title cards, mood frames for a storyboard. Keep it non-identifiable: no faces, no brands, no text.
6. **Then the house style:** grade it into Liquid Glass (`grade.py`), cut it in as 1-4 s b-roll with `timeline.py`
   (`broll.py`), captions and claims as usual. B-roll order stays: the owner's footage, made-here graphics, licensed
   stock, then AI (§4 F).

## The owner's own use (no Claude needed)

- **In a browser:** the hosted studio at https://muapi.ai/open-generative-ai (free account, credits per generation).
- **Desktop app:** the installers on https://github.com/Anil-matcha/Open-Generative-AI/releases (macOS, Windows,
  Linux). The API key is pasted once in the app (kept on that computer). Settings → Local Models turns on the free
  local engines.
- **API key:** https://muapi.ai/dashboard. Never paste it into a chat or a file in this repo (the repo is public).

## Claude's use in a cloud session

1. Get the owner's OK for the job, the model and the cost.
2. Save the key as a network secret with `request_credential`: host `api.muapi.ai`, header `x-api-key`, no prefix. The
   proxy injects it and allows the host; the key never touches the container. Then `export MUAPI_KEY=placeholder`
   (the scripts refuse to start without a value; the proxy replaces it).
3. When a download of a result is blocked, ask to allow that exact CDN host (`update_environment`), once.
4. Find and price a model (read live, never from memory): `muapi/muapi-models/README.md`
   (`curl -s https://api.muapi.ai/api/v1/models`), or `jq '.[].name' muapi/schema_data.json` for the offline list.
5. Generate (each script has `--help`; `--async` and `muapi/core/platform/check-result.sh` for long video jobs):

   ```bash
   S=.claude/skills/open-generative-ai/muapi
   bash $S/core/media/generate-image.sh --model flux-dev --prompt "..." --aspect-ratio 9:16
   bash $S/core/media/generate-video.sh --model kling-v2.1-master-t2v --prompt "..." --aspect-ratio 9:16 --duration 5
   bash $S/core/media/image-to-video.sh --model ... --image-url URL --prompt "..."
   bash $S/core/edit/enhance-image.sh --op upscale --image-url URL
   ```

   Model names change: take them from step 4. For film-like prompts (shot, lens, light, camera move) read
   `muapi/library/motion/cinema-director/README.md`; our reels never use whip-ins, push-ins or camera zooms (§5).
6. Results land in `muapi/media_outputs/` (git-ignored). Move them to the scratchpad; never commit generated media or
   the owner's footage to this public repo.

## Files

| Path | What |
|---|---|
| `muapi/core/platform/` | `setup.sh` (key check), `check-result.sh` (poll an async job) |
| `muapi/core/media/` | `generate-image.sh`, `generate-video.sh`, `image-to-video.sh`, `create-music.sh`, `upload.sh` |
| `muapi/core/edit/` | `edit-image.sh`, `enhance-image.sh` (upscale, background remove…), `video-effects.sh`, `lipsync.sh` |
| `muapi/muapi-models/README.md` | How to list, price and run any MuAPI model |
| `muapi/library/motion/cinema-director/` | Prompting a model like a film director (shot grammar, lenses, light) |
| `muapi/schema_data.json` | The model and endpoint list the scripts read (upstream snapshot) |
