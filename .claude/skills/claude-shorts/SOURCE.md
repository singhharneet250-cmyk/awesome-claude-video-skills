# Source

Vendored on 2026-11-27 at the owner's request (from agentskillshub.top/best/claude-video-skills: "Install the best ones",
claude-shorts chosen). The skill's own name is `shorts` (say "shorts" or "make shorts from this video").

- Upstream: https://github.com/AgriciDaniel/claude-shorts @ `a369fad` (2026-04-10)
- Licence: MIT (`LICENSE`, unchanged)
- Read before vendoring: no telemetry. `setup.sh` installs faster-whisper, mediapipe, numpy and opencv into a venv
  (`~/.shorts-skill`) and the Remotion packages with npm. faster-whisper downloads its model from huggingface.co on
  first use; that works in this cloud environment (tested 2026-11-27).

## Use for Nutrition Hub

Use it to find the best moments in a long talk and cut them into vertical clips (transcribe, score, pick, cut, export).
Then finish each clip with `nutrition-hub-white-glass`: Roman Punjabi captions beside the head with the brand gradient
and the Logo Red key word (`scripts/captions.py`), not this skill's Bold/Bounce/Clean caption styles; real background
kept; full HD at -14 LUFS (`scripts/encode.py`). Show the picked clips and a short sample before rendering them all.

For the owner's Punjabi talks, run its transcription with Hindi as the language
(`python3 scripts/transcribe.py take.mp4 --output t.json --language hi`): auto-detect picks Punjabi and the text comes out as
junk, while Hindi gives good word timings and rough words to rewrite in Roman Punjabi (tested 2026-11-27).

## Changes in this copy

- `SKILL.md`: the frontmatter description starts with the companion note; the pre-flight search also looks for this
  repo copy (`.claude/skills/claude-shorts`).
- `requirements.txt` and `setup.sh`: PyAV pinned below 16. With PyAV 19.0, faster-whisper 1.2.1 fails on every file
  (`open() got an unexpected keyword argument 'metadata_errors'`); with 15.1 it works (tested 2026-11-27).
- `scripts/transcribe.py`: a `--language` option (default: auto-detect as upstream), passed to faster-whisper.
- `CLAUDE.md` renamed to `UPSTREAM-CLAUDE.md`, so its upstream development notes (install to `~/.claude/skills`) are
  not loaded as instructions for this repo. `install.sh` is not needed here: the skill already loads from the repo.
