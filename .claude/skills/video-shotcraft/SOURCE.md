# Source

Vendored on 2026-11-27 at the owner's request ("Install this skill for me: https://github.com/Vincentwei1021/video-shotcraft").

- Upstream: https://github.com/Vincentwei1021/video-shotcraft @ `1152363` (2026-11-25), plugin `video-shotcraft` 1.0.0 by Wei Yihao
- Licence: Apache-2.0 for the code and docs (`LICENSE`, kept unchanged). Shot cards credit their research sources in
  `references/shots/ATTRIBUTION.md` (motion techniques re-implemented from scratch, no original footage or brand assets).
- Read and scanned before vendoring: no telemetry or hidden network calls. Network use is opt-in and explicit:
  `assets/scripts/sfx-source.py` talks only to freesound.org / cdn.freesound.org; `publish/upload_post.py` posts to
  api.upload-post.com only with the user's own `UPLOAD_POST_API_KEY`; `workbench/` is a local dev server.

## The owner's fork

https://github.com/singhharneet250-cmyk/video-shotcraft (sent by the owner on 2026-11-27). Checked the same day: a plain
fork at `075b548` (2026-11-19), 8 commits behind upstream, with no commits of its own. The 8 commits change only the
READMEs, the sponsor images and the WeChat group picture, none of which are vendored here, so the skill files in this
copy (`1152363`) are the same as the fork's. To update later: sync the fork with upstream on GitHub, then copy the
skill from it again and record the new commit here.

## Not included here (and why)

| Left out | Why |
|---|---|
| `assets/audio/bgm/*.mp3` (5 Mixkit tracks) | Mixkit's licence allows use in videos, not redistributing the files on their own; this repo is public |
| `template/public/audio/*.mp3` (the Ink Press template's historical SFX) | upstream itself marks several as unverifiable ("review or replace before publishing"); same redistribution concern |
| `assets/readme/`, `assets/wechat-*` | sponsor and social images for the upstream README |
| `README_CN/JA/RU/TW.md`, `.github/`, `videos/`, `demos/_legacy/` | translations, CI, and superseded demos |

To run the Ink Press template unchanged, take its audio from upstream or replace it: for Nutrition Hub use
`nutrition-hub-white-glass/scripts/sfx.py` (original SFX kit) and `scripts/score.py` (original music), or
Freesound through `assets/scripts/sfx-source.py` (CC0 by default), or music the owner has licensed.

## Changes in this copy

- `SKILL.md`: the frontmatter description starts with the companion note (load the brand skill first) and a licence line;
  the BGM line notes that the audio is not included. Everything else is upstream as-is.
- The plugin is also in the owner's Claude account catalog (Anthropic Directory, `video-shotcraft`); this copy makes it
  available to every session on this repo.
