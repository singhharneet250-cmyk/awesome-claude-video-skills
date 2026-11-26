# ghost-editor: the clean raw cut, and a person matte, on your Mac

[ghost-editor](https://github.com/kurbaitaev/ghost-editor) (MIT, by kurbaitaev) is a Claude Code skill
that edits talking-head reels on an Apple-silicon Mac. Nutrition Hub uses **two of its parts only**, and
Liquid Glass does the rest:

1. **The raw cut.** From one long recording with retakes and false starts, it finds every spoken try, keeps
   the best take of each line, smooths the voice across the joins, and checks faces on every frame.
   - The result is `build/rawcut.mp4`, with no grade, captions or effects.
   - It becomes the `"source"` of your `edit.json` (footage-editing.md §0).
2. **The person matte.** ghost-editor's `scripts/matte.py` (BiRefNet-portrait, MIT weights) writes the speaker as a cut-out
   with transparency (VP9 WebM).
   - `fx.py escape --matte matte.webm` uses its alpha channel (tested), so the frame escape works in any room,
     not only in front of a plain wall.

- **Pinned commit:** `d71bdb6` (18 Nov 2026, "19 named styles", v0.3.0). Update only on purpose.
- **Where it runs:** a Mac with Apple silicon. Its author says Linux and Intel Macs are untested, and Windows
  isn't mentioned. It doesn't run in the cloud sessions.
- **Not used here:**
  - its 19 styles and one-word presets, meme sounds and Mixkit music
  - stock B-roll and Google image pulls
  - `brand_kit.py`, which pulls other companies' logos
  - the ElevenLabs narrator
  - These all have their own looks or licences; SKILL.md wins wherever they disagree.

## Install once (on the Mac)

1. In Claude Code: *"Clone https://github.com/kurbaitaev/ghost-editor into ~/.claude/skills/ghost-editor, check
   out d71bdb6, and follow its docs/INSTALL.md, with these changes:"*
   - **OpenCV:** install `opencv-python==4.10.0.84`, not the newest. This skill's face tracking needs
     the 4.x face models, and one OpenCV serves both.
   - **No Gemini key:** without one, its B-roll check is skipped. With one, video frames go to Google;
     add it only if you agree to that.
   - **Skip:** `brew install yt-dlp` and the ElevenLabs key, which aren't needed for the raw cut.
2. For the matte, also run `bash ~/.claude/skills/ghost-editor/scripts/setup_matte.sh`.
   - It sets up its own environment (`~/.venvs/ghost-matte`, about 1.5 GB plus 1.1 GB of model weights from
     Hugging Face). It doesn't touch the OpenCV above.

## Use

**Raw cut** (follow its `references/take-selection.md`, "The raw cut, step by step"):

```bash
G=~/.claude/skills/ghost-editor
bash $G/scripts/rawcut_prep.sh take.MOV proj     # voice files + frame-exact proxy
# then, as that guide says: vad_pauses.py → islands_tx.py → facescan.py --pts → takes.py → plan_cut.py
#   → subcheck.py → recipes/clean-os/assemble.py --plan → voice_smooth.py --plan → qa_cut.py
```

Look at its approval page before accepting the cut. Then set `"source": "proj/build/rawcut.mp4"` in
`edit.json`, run `timeline.py check`, and render.

**Matte for the frame escape:**

```bash
~/.venvs/ghost-matte/bin/python $G/scripts/matte.py graded.mp4 -o matte.webm --ranges 1.0-3.4
python3 $SK/scripts/fx.py escape graded.mp4 escape.mp4 --at 1.0-3.4 --matte matte.webm
```

In `edit.json`: `{"effect": "escape", "start": 1.0, "end": 3.4, "matte": "matte.webm"}`.
- Matte the same file the effect runs on (the graded take), so the frames line up.
- Outside `--ranges` the WebM is fully transparent.
