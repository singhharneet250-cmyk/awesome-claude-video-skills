# Editing real footage in the Liquid Glass style

These ffmpeg recipes take raw footage to a finished branded reel. All of them were run end
to end on a test clip (1920×1080 at 25 fps in, 1080×1920 at 30 fps out). The grade numbers
are starting points: always judge a full-size still by eye.

`SK` below means this skill's folder: `.claude/skills/nutrition-hub-white-glass`.

## 0. One timeline for the whole edit

Write the edit as an `edit.json` next to the footage. Paths are relative to it, and every track is optional:

```json
{
  "source": "take.mp4", "out": "final.mp4", "grade": true, "words": "words.json",
  "broll":    [{"start": 4.2, "end": 5.8, "file": "broll/shelf-pan-01.mp4", "transition": "white"}],
  "effects":  [{"effect": "escape", "start": 1.0, "end": 3.4, "matte": "wall"},
               {"effect": "orbit", "start": 6.6, "end": 9.4, "words": "Whey,Creatine,Omega-3", "tilt": 65}],
  "overlays": [{"template": "chat-takeover.html?bottom=560", "start": 10}],
  "captions": {"position": "auto", "keywords": ["protein", "sugar"], "blur": true},
  "sfx":      [{"t": 9.6, "sfx": "tick"}],
  "endcard":  {"template": "reel-9x16.html", "from": 8.15}
}
```

```bash
python3 $SK/scripts/timeline.py check edit.json --motion   # rules + edit.timeline.png (with gesture moments)
python3 $SK/scripts/timeline.py edit edit.json --motion    # edit.editor.html: drag and trim before the final render
python3 $SK/scripts/timeline.py render edit.json           # the finished reel, then qa.py
```

- **`check`:**
  - FAIL lines block the render: b-roll in the 1.5 s hook, shots outside 1–4 s or closer than 1 s, an effect
    over b-roll, an effect shorter than 1.55 s, overlays on top of each other, a missing file, captions
    without word timings.
  - WARN lines are for a look: b-roll over 45%, an effect used twice.
  - It also draws the timeline. Show the owner that picture before rendering.
- **`edit`:** an editor page with a filmstrip of the take, caption words, gesture moments and every track.
  - Drag clips to move them and drag their edges to trim. Click one to change its b-roll clip, transition
    (cut / dip to white / dissolve), effect, orbit words or sound.
  - The brand rules re-check as you drag.
  - Only timing and content change: colours, fonts and the caption look aren't editable there.
  - "Copy edit.json", then save it over `edit.json` (or paste it to Claude) and render.
  - Tested: drag, trim, word edits, undo and reset in a headless browser, at phone and desktop widths.
- **`render`:** runs the recipes below in this order:
  1. reframe and grade (HDR is tone-mapped)
  2. b-roll (§2b)
  3. orbit / escape (§2d)
  4. captions, with the blur band only when needed (§2c, §4)
  5. overlays (§3)
  6. burn the captions
  7. end card through a dip to white (§6)
  8. SFX from every cue sheet, then −14 LUFS (§7b)
  9. `qa.py`
  - Intermediate files go to `timeline_work/`, named by what made them (so an old render is never reused).
  - A b-roll entry can be a motion-kit beat: `{"start": 8, "end": 11.2, "template": "motion-kit.html?scene=wheel&pick=Creatine"}`.
    It renders, keeps its colours ungraded, and its sounds join the mix.
  - Overlays get real liquid glass (§3b); `"glass": "flat"` on an overlay keeps the near-opaque panel.
  - `"motion_blur": 4` renders every graphic with motion blur.
- **`export`:** `edit.otio` + `edit.srt` for DaVinci Resolve (File > Import > Timeline), Premiere or Kdenlive:
  V1 the graded take then the end card, V2 b-roll and beats, V3 overlays (ProRes 4444), A1 voice, A2 each SFX as a
  clip at its cue, effects as markers on V1. Tested on a 10 s take with a beat and an overlay: 2 s once rendered.
- **Rhythm:** `check` warns after 6 s with no new picture (no b-roll, effect, overlay or beat).
- **Tested** on a 10 s take:
  - With every track except overlays, it took 1 min 37 s.
  - With a chat-takeover overlay, it took 36 s.
  - `qa.py` passed everything both times (−14.2 to −14.4 LUFS, true peak −1.9 dBTP).

## 1. Probe

```bash
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate:format=duration -of compact in.mp4
ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer -of csv=p=0 in.mp4
```

If the second line prints `arib-std-b67` or `smpte2084`, the clip is HDR (iPhones record it by
default) and looks washed out unless it is tone-mapped. Put this at the start of the §2 filter
(tested): `zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,`.
Better still, ask for the next takes with HDR video switched off (`reference/broll-shot-list.md`).

## 2. Reframe to 9:16 and apply the "soft studio light" grade

The look is bright, clean and slightly low-contrast, with neutral-to-cool whites and gently
reduced saturation. Skin must stay natural. **Don't grade product close-ups in a way that
shifts label colours** (accurate packaging): grade those shots separately or leave them alone.

```bash
ffmpeg -i in.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,\
eq=brightness=0.02:contrast=0.96:saturation=0.92,colorbalance=rh=-0.01:bh=0.015,setsar=1" \
  -c:v libx264 -crf 4 -preset fast -pix_fmt yuv420p -c:a copy graded.mp4
```

If the subject isn't centred, change the crop's x offset (for example `crop=1080:1920:(iw-1080)*0.35:0`).

## 2b. B-roll cutaways (R5)

Cut away from the face to what is being said, and back. The voice track is copied unchanged,
and each b-roll is filled to the frame, conformed and graded like the footage (SKILL.md §4 F).
Run this after the grade:

```bash
# when a word is spoken (word timings from step 4)
python3 $SK/scripts/broll.py graded.mp4 cut.mp4 --words words.json \
  --map label=broll/label-closeup-whey-01.mp4 --map scoop=broll/scoop-01.mp4 --map store=broll/shelf-pan-01.mp4

# at set times, with an in-point (@2.5) inside the b-roll file, through a dip to white
python3 $SK/scripts/broll.py graded.mp4 cut.mp4 --at 3.2-5.0=broll/shelf-pan-01.mp4@2.5 --transition white
```

- **Spec file:** for full control, `--spec broll.json` with `[{"start", "end", "file", "in", "speed",
  "x", "y", "grade", "transition"}]`.
  - `"speed": 0.5` plays a 60 fps pour in slow motion.
  - `"x"`/`"y"` (0–1) move the crop.
  - `"grade": false` keeps a label close-up untouched.
- **Check first:** `--dry-run` prints the placements and any rule notes without rendering.
- **Keyword mode:**
  - It uses each mapped file once, on the next time its word is spoken.
  - It cuts back at the pause nearest to `--len` (2.2 s).
  - It skips a shot that would break the rules.
- **Stills:** `.jpg`/`.png` get a slow 4% push-in, sampled sub-pixel so it doesn't judder. A cut-out PNG
  sits on an ice-mist stage.
- **Tested:** cut, white dip and dissolve; 60 fps slow motion; an HLG HDR clip; a still and a cut-out;
  29.97 fps and silent A-rolls. The audio stayed byte-identical. A 14 s 1080×1920 reel with four shots
  takes about 12 s.

## 2c. Bottom blur band (R6 look)

Run this after the grade and b-roll and before any overlay or captions, so they stay sharp:

```bash
python3 $SK/scripts/bottom_blur.py graded.mp4 blurred.mp4               # dark fade, like R6
python3 $SK/scripts/bottom_blur.py graded.mp4 blurred.mp4 --tone light  # fade to white
```

- **Defaults:** blur from 64% of the height, full by 76%, sigma 26 px at 1080 wide, fade from 72% to 85% at the bottom.
- **Tuning:** adjust with `--start`, `--full`, `--sigma` and `--fade`.
- **Speed:** a 4 s 1080×1920 clip takes about 20 s.
- **Captions:** then use `captions.py --position mic` (or `auto`), so they sit above the band.
- **Only when needed:** pass `--plan plan.json` from `captions.py --position auto --plan-out plan.json`. The band
  then fades in only while captions sit on a busy bottom. Add `--when 3.0-5.5` for animations in the band.
  Without either option it covers the whole clip. `--auto` starts it just under the person.
  Needs `pip install opencv-python-headless==4.10.0.84`.

## 2d. Orbit, frame escape and motion (SKILL.md §4 G, H, J)

Run these after the grade and b-roll, and before captions:

```bash
python3 $SK/scripts/motion_track.py graded.mp4 --preview motion_check.mp4   # where the head and hands are, and the moments
python3 $SK/scripts/fx.py orbit graded.mp4 orbit.mp4 --at 6.0-9.5                  # spheres around the head
python3 $SK/scripts/fx.py orbit graded.mp4 orbit.mp4 --at 6-9.5 --words "Whey,Creatine,Omega-3" --tilt 65
python3 $SK/scripts/fx.py escape orbit.mp4 escape.mp4 --at 1.0-4.0 --matte wall    # plain wall behind the speaker
python3 $SK/scripts/fx.py escape orbit.mp4 escape.mp4 --at 1-4 --matte person_matte.mp4   # matte from CapCut / Runway
```

- **Timing:** start an effect on a `gesture` or `hands_up` moment from `motion_track.py`, so it answers the
  speaker's movement. Give it 2.5–4 s, and use each effect at most once per reel.
- **Check the outline first:** `person_matte.py graded.mp4 --source wall --out matte.mp4 --at 1-4`. The wall key
  wants a locked camera and a plain, evenly lit wall that differs from the hair and clothes.
- **Sound:** each run writes `<out>.sfx.json` with a soft whoosh. Add it with `sfx.py --cues orbit.sfx.json` at the end (§7b).
- **Speed:** about 45 s for a 7 s 1080×1920 clip with the wall key; about 20–30 s with the head shape.
  Only the effect window changes, and the audio is copied.
- **Tested** on the reference reels:
  - Orbit with spheres, flat and tilted word chips, and hands passing in front.
  - The escape with the wall key on R4.
  - The motion tracker: the head in 100% of frames on R4 and R5; hands in 99% on R4's plain wall, unreliable
    in R5's warm, busy room.

### The R7 pack (SKILL.md §4 K)

```bash
python3 $SK/scripts/fx.py sticky   graded.mp4 out.mp4 --at 1.6-3.6 --text "3–5 g a day" --badge 12
python3 $SK/scripts/fx.py wipe     graded.mp4 out.mp4 --at 4.0-6.2 --before ungraded.mp4
python3 $SK/scripts/fx.py pullback graded.mp4 out.mp4 --at 6-9
python3 $SK/scripts/fx.py scatter  graded.mp4 out.mp4 --at 6.6-9.2 --words "Label,first"
python3 $SK/scripts/fx.py bgswap   graded.mp4 out.mp4 --at 2-5 --matte wall --bg stage   # or a clip / image / blur
node $SK/scripts/render.cjs "$SK/templates/headline-wall.html" --transparent --out wall.mov      # overlays (§3)
node $SK/scripts/render.cjs "$SK/templates/phone-mockup.html?side=left&top=560" --transparent --out phone.mov
node $SK/scripts/render.cjs "$SK/templates/ui-world.html" --transparent --out ui.mov
node $SK/scripts/render.cjs "$SK/templates/chat-takeover.html?layout=comment" --transparent --out comment.mov
```

- **In `edit.json`:** the five fx effects go under `"effects"`, the templates under `"overlays"`.
  `timeline.py render` makes the ungraded "before" for a wipe by itself.
- **Speed:** 10–20 s each on a 7 s clip.
- **Tested on the R4 and R5 clips:**
  - The full pack timeline (sticky, wipe, scatter, headline wall, phone, end card) rendered in 1 min 45 s.
  - `qa.py` passed everything (−14.5 LUFS, true peak −2.4 dBTP).
  - That test is why `sfx.py` now adds a limiter after loudness: four quick ticks pushed the peak to −0.1 without it.

### Chat takeover (SKILL.md §4 I)

```bash
python3 $SK/scripts/person_track.py graded.mp4          # read "top" (the head top, as a share of the height)
node $SK/scripts/render.cjs "$SK/templates/chat-takeover.html?bottom=560" --transparent --out chat.mov   # 40 px above the head
node $SK/scripts/render.cjs "$SK/templates/chat-takeover.html?layout=full" --transparent --out chat.mov  # takeover
```

Composite it like any overlay (§3), at the second it should start. It writes `chat.sfx.json`: a pop for the
panel and the send, and a tick for the reply. Edit the copy in its `SCENE` object, and keep the "Example chat"
label unless the chat is real and shared with consent.

## 3. Brand graphics over footage

Render a transparent overlay from a template, then composite it starting at the right
second. Use `-itsoffset` for the start time.

```bash
node $SK/scripts/render.cjs $SK/templates/overlay-callout.html --transparent --out callout.mov
ffmpeg -i graded.mp4 -itsoffset 1 -i callout.mov \
  -filter_complex "[0:v][1:v]overlay=0:0:eof_action=pass[v]" \
  -map "[v]" -map 0:a -c:v libx264 -crf 4 -preset fast -pix_fmt yuv420p -c:a copy over.mp4
```

- `--transparent` writes ProRes 4444 (`.mov`) or VP9 with alpha (`.webm`).
- Over footage the glass is real clear Liquid Glass (§3b; `"glass": "flat"` falls back to near-opaque). Keep callout text on its glass card;
  only caption words go straight on video (§4).
- The callout sits in the upper safe area (y about 270) so it never meets the captions.

## 3b. Liquid glass over footage (SKILL.md §4 A)

The glass is done at composite time, because a separately rendered overlay can't see the footage:

```bash
T="$SK/templates/motion-kit.html?scene=prompt"
node $SK/scripts/render.cjs "$T" --transparent --real-glass --out prompt.mov        # words, icons, clear panels
node $SK/scripts/render.cjs "$T" --transparent --glass-mask --out prompt.mask.mov   # the panel shapes only
python3 $SK/scripts/glass.py graded.mp4 over.mp4 --content prompt.mov --mask prompt.mask.mov --at 1
```

- Under each panel (house default since 2026-11-26: clear, liquid, glossy): a 32 px rounded edge that bends the
  picture like a drop of water (IOR 1.5, `--liquid 1.0`), faint colour split, almost no frost, a porcelain tint
  that adapts just enough for ink text (about 0.73 luminance), gloss (`--gloss 1.0`: rim specular and bloom from
  the top left, a far-edge line, fresnel, a curved sheen), no drop shadow, and a materialize as the panel reveals.
- `--compare flat.mov` writes a side-by-side (old flat panel left, liquid glass right) for checking.
- `--strength 0…1` is the iOS 27-style slider (0 opaque, 0.4 frosted, 0.9 the clear house default, 1 clear;
  tested at 0, 0.4 and 0.9: text reads at all three, hands show through at 0.9). `--variant regular` = 0.4.
- Checked on the owner's Vitamin D take (plaid shirt, white stage): toggle, prompt and CTA cards and the orbit
  chips read at 0.9 with ink text; sample `Clear-Glossy-Glass-sample.mp4` (12.6 s).
- Tested on a 6 s 1080×1920 take (bright interior): 32 s for 180 frames; text reads over hands, hair and a dark chair.
- Any template works; panels are whatever carries `.nh-glass`. A template without glass just gets its overlay.

## 3c. Screen insert (SKILL.md §4 M)

```bash
node $SK/scripts/render.cjs "$SK/templates/motion-kit.html?scene=menu" --size 1920x1080 --out beat.mp4
python3 $SK/scripts/screen_insert.py store-tv.mp4 beat.mp4 tv.mp4 --preview tv.png   # check the corners first
python3 $SK/scripts/screen_insert.py store-tv.mp4 beat.mp4 tv.mp4 --at 0.5
```

- A lit screen is found by itself (edges and brightness, screen-shaped, not cut off by the frame); a switched-off
  screen with `--detect dark`; otherwise `--corners x1,y1,…` (top-left, top-right, bottom-right, bottom-left).
- Tested: R15's curved monitor and R11's dark monitor (`--detect dark`), both locked off, look real. A handheld
  laptop shot that runs off the frame (R16) needs `--corners`, and `--track` drifts there after about a second:
  film the store TV locked off.
- The result is b-roll: cut it in with `broll.py` or a b-roll entry in `edit.json`.

## 3d. Remove the background and clean the voice (SKILL.md §4 N, O)

```bash
python3 $SK/scripts/person_cutout.py take.mp4 --preview cut.png --at 12        # check one moment first
python3 $SK/scripts/person_cutout.py take.mp4 nobg.mp4 --matte-out matte.mp4    # you on the Liquid Glass stage
python3 $SK/scripts/voice.py take.mp4 voice.wav                                  # clear, natural voice
ffmpeg -i nobg.mp4 -i voice.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest take_src.mp4
```

- Then `take_src.mp4` is the `edit.json` source with `"grade": false` (the cut-out is graded already), and
  `"matte": "matte.mp4"` on the orbit, escape or scatter.
- Tested on the owner's 42 s WhatsApp take (576×1024, a busy room with a counter touching the arm): about 15 min of
  BiRefNet-lite keyframes plus about 8 min for every frame on 4 CPU cores.
- Captions for Punjabi or Hindi speech: Whisper (faster-whisper `medium`, local) gives good word timings but rough
  Devanagari spelling for Punjabi; write the words in Roman script on those timings (`words.json`), the way the label
  reel's Hinglish captions were done. Keep "Vitamin D" as one word with a no-break space so it never splits.

## 4. Captions

1. Get word timings. Use Whisper or faster-whisper with word timestamps, IT Reelsmaker's
   transcription, or the WhisperAI connector. An `.srt` also works, but its word timing is
   estimated, so check the sync.
2. Build the captions. They follow the limits in SKILL.md §6: 2 lines, about 28 characters
   per line, 1–3 s each, one red key word, never across a sentence end or a pause.

```bash
python3 $SK/scripts/captions.py words.json --out captions.ass --srt captions.srt --keywords creatine,protein,recovery --match over.mp4
```

   `--match` reads the video the captions go on. It picks white, ink or strong-shadow words from
   what is behind each caption, and takes the key-word colour from the video's own dominant colour
   (logo red when it has none). Check what it picked with
   `python3 $SK/scripts/caption_colors.py over.mp4`. To fix a single caption by hand, the key word
   is written `{\c&H002B78F0&}word{\r\blur6}` (colour as `&H00BBGGRR`).
3. Burn the captions in:

```bash
ffmpeg -i over.mp4 -vf "ass=captions.ass:fontsdir=$SK/assets/fonts" \
  -c:v libx264 -crf 4 -preset fast -pix_fmt yuv420p -c:a copy capped.mp4
```

Captions have no box (SKILL.md §6). The style uses `BorderStyle=1` with a semi-transparent
border softened by `{\blur6}`, which reads as a soft shadow while the words stay sharp. This
was tested on a busy test pattern and on real footage. Don't switch back to a box: a
translucent `BorderStyle=3` box stripes wherever a colour change splits the line, and
`BorderStyle=4` leaves blobby halos.

## 5. Transitions between shots

- Use a cut by default.
- For a soft dissolve: `xfade=transition=fade:duration=0.35:offset=<A_len-0.35>`.
- For a dip to porcelain white: `xfade=transition=fadewhite:duration=0.4:offset=<A_len-0.4>`.
- Pair each with `acrossfade=d=<same>` on the audio.
- Both inputs need the same size, fps, pixel format and SAR, so normalise with `fps=30,format=yuv420p,setsar=1`.

## 6. End card with the original logo

```bash
# render only the end-card beat of the reel template (its logo comes from assets/logo/)
node $SK/scripts/render.cjs $SK/templates/reel-9x16.html --from 8.15 --out endcard.mp4

MAIN=$(ffprobe -v error -show_entries format=duration -of csv=p=0 capped.mp4)
END=$(ffprobe -v error -show_entries format=duration -of csv=p=0 endcard.mp4)
X=0.4; OFF=$(python3 -c "print(round($MAIN-$X,3))"); PAD=$(python3 -c "print(round($END-$X,3))")

ffmpeg -i capped.mp4 -i endcard.mp4 -filter_complex "\
[0:v]fps=30,format=yuv420p,setsar=1[a];[1:v]fps=30,format=yuv420p,setsar=1[b];\
[a][b]xfade=transition=fadewhite:duration=$X:offset=$OFF[v];\
[0:a]afade=t=out:st=$OFF:d=$X,apad=pad_dur=$PAD,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a2]" \
  -map "[v]" -map "[a2]" -c:v libx264 -crf 2 -preset slower -profile:v high -level:v 5.1 -pix_fmt yuv420p \
  -maxrate 100M -bufsize 200M -c:a aac -b:a 320k -movflags +faststart final.mp4
```

If the footage has no audio track, add `-f lavfi -i anullsrc=r=48000:cl=stereo` as a third
input. Use `[2:a]atrim=0:$MAIN,afade=...` in place of `[0:a]afade=...`, because the silent
source is endless and needs the trim (tested).

## 7. Audio

- Speech: `highpass=f=80`, plus a gentle `acompressor` if levels jump around.
- Music sits about 18–22 dB under the voice. Use licensed music only.
- Finish with loudness `loudnorm=I=-14:TP=-1.5:LRA=11` for social platforms.

### 7b. Sound effects (run last)

`sfx.py` adds the original kit (SKILL.md §5 Sound effects) to the finished video. It copies the
picture unchanged, sets each sound against the voice's measured loudness, and re-masters the mix to
−14 LUFS. So run it after the end card (§6), on `final.mp4`:

```bash
# cue sheets: render.cjs writes one next to every render (slams, pills, cards, logo)
#   @1    the callout overlaid from second 1 (§3)
#   @$OFF the end card, which starts at $OFF in final.mp4 (§6)
python3 $SK/scripts/sfx.py final.mp4 final_sfx.mp4 \
  --cues callout.sfx.json@1 \
  --cues endcard.sfx.json@$OFF \
  --broll broll_plan.json             # from broll.py --plan-out: a swish into each dip to white

python3 $SK/scripts/sfx.py final.mp4 final_sfx.mp4 --at 4.9=thud --at 6.5=tick   # by hand
```

- **Several renders:** `--cues FILE@START` can be given several times. START is where that render begins
  in this video (0 when left out).
- **Check first:** `--dry-run` prints every sound with its level and why it is there.
- **Adjust:** `--level -3` makes every sound quieter. `--kit DIR` exports the kit as WAV files (with
  `kit.json` of hit times) for CapCut or Premiere.
- **Tested:**
  - Every sound landed on its cue to the sample.
  - Levels came out within 0.5 dB of target against the voice.
  - The mastered file passed `qa.py` loudness (−14.1 LUFS, true peak −1.5 dBTP).
  - The video stream was byte-identical.
- **Graphics-only pieces with no voice and no music:** the sounds sit where they would against a mastered
  voice (−14 LUFS), and the file isn't mastered. `qa.py` will flag the low overall loudness; add music
  or accept the warning.

## 8. QA

```bash
python3 $SK/scripts/qa.py final.mp4 --expect 18.5          # footage reel; add --graphics for all-graphics pieces
ffmpeg -ss 3 -i final.mp4 -frames:v 1 still.png           # full-size check, look at it
```

`qa.py` prints one PASS / WARN / FAIL line per check, with the fix for each FAIL. It
checks format, codec, audio, faststart, loudness, the logo hash, stray hues and black
frames, and it writes `final.sheet.png`. Look at the sheet, then run through the by-eye
checklist in SKILL.md §9.7.

## 9. Fit a size cap (WhatsApp 16 MB, email)

Prefer the `halfsize` skill (`npx -y halfsize@0.2.0 final.mp4 --for whatsapp`), which also
reports VMAF. Without it, this two-pass ffmpeg encode lands just under the cap (tested:
1.473 MB for a 1.5 MB target on an 11 s reel):

```bash
IN=final.mp4; TARGET_MB=15.5      # WhatsApp media cap is 16 MB; keep headroom
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $IN)
VK=$(python3 -c "print(int($TARGET_MB*8000/$DUR*0.97 - 128))")   # video kb/s after 128k audio
ffmpeg -y -i $IN -c:v libx264 -b:v ${VK}k -preset slow -pass 1 -passlogfile fit -an -f null /dev/null
ffmpeg -y -i $IN -c:v libx264 -b:v ${VK}k -preset slow -pass 2 -passlogfile fit -profile:v high -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 -movflags +faststart whatsapp.mp4 && rm -f fit-0.log*
```

If `VK` comes out under about 1500 for a 1080×1920 reel, the picture will soften. Trim the
reel, or send the full-quality file another way, instead of going lower. Run `qa.py` on the
result too.
