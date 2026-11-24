# Source

- Upstream: https://github.com/YKLovePython/halfsize (`skills/halfsize/SKILL.md`)
- Commit: `3024a56c44d81e94450026345267970b127a6064` (npm package `halfsize@0.2.0`)
- Licence: MIT (`LICENSE`, copied unchanged)
- Security grade on agentskillshub.top: safe

## Local changes

- Every `npx halfsize` is pinned to `npx -y halfsize@0.2.0`, and the GitHub fallback is pinned
  to the commit above, so a new upstream release can't change what runs without a review.
- Added the `--for whatsapp` example (the preset exists in the CLI: 16 MB).

## Review notes

The CLI source at that commit was read before vendoring. It encodes locally with FFmpeg and
never uploads the video. It only reaches the network in `--fix` (downloads the
`ffmpeg-static` binary from GitHub or the npmmirror) and runs a local-only web UI with `--web`.

Not yet run in the cloud container: running an npm package was blocked there. Test it on a
real clip before relying on it. The tested plain-ffmpeg fallback is in
`../nutrition-hub-white-glass/reference/footage-editing.md` §9.
