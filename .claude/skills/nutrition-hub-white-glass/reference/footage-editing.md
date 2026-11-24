# Editing real footage in the White Glass style

These ffmpeg recipes take raw footage to a finished branded reel. All of them were run end
to end on a test clip (1920×1080 at 25 fps in, 1080×1920 at 30 fps out). The grade numbers
are starting points: always judge a full-size still by eye.

`SK` below means this skill's folder: `.claude/skills/nutrition-hub-white-glass`.

## 1. Probe

```bash
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate:format=duration -of compact in.mp4
```

## 2. Reframe to 9:16 and apply the "soft studio light" grade

The look is bright, clean and slightly low-contrast, with neutral-to-cool whites and gently
reduced saturation. Skin must stay natural. **Don't grade product close-ups in a way that
shifts label colours** (accurate packaging): grade those shots separately or leave them alone.

```bash
ffmpeg -i in.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,\
eq=brightness=0.02:contrast=0.96:saturation=0.92,colorbalance=rh=-0.01:bh=0.015,setsar=1" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy graded.mp4
```

If the subject isn't centred, change the crop's x offset (for example `crop=1080:1920:(iw-1080)*0.35:0`).

## 3. Brand graphics over footage

Render a transparent overlay from a template, then composite it starting at the right
second. Use `-itsoffset` for the start time.

```bash
node $SK/scripts/render.cjs $SK/templates/overlay-callout.html --transparent --out callout.mov
ffmpeg -i graded.mp4 -itsoffset 1 -i callout.mov \
  -filter_complex "[0:v][1:v]overlay=0:0:eof_action=pass[v]" \
  -map "[v]" -map 0:a -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy over.mp4
```

- `--transparent` writes ProRes 4444 (`.mov`) or VP9 with alpha (`.webm`).
- Over footage the glass goes near-opaque automatically. Never put ink type straight on video.
- The callout sits in the upper safe area (y about 270) so it never meets the captions.

## 4. Captions

1. Get a transcript. Use the user's script, a connected transcription tool, or Whisper if it is installed.
2. Copy `$SK/reference/captions.ass` and replace the `[Events]`. Follow these limits:
   - 2 lines at most, about 28 characters per line, 1–3 s each.
   - One orange key word per caption, written as `{\c&H2B78F0&}word{\c&H382B20&}`.
3. Burn the captions in:

```bash
ffmpeg -i over.mp4 -vf "ass=captions.ass:fontsdir=/usr/share/fonts/opentype/inter" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy capped.mp4
```

Keep the box opaque. A translucent `BorderStyle=3` box stripes wherever a colour change
splits the line (this was tested). `BorderStyle=4` leaves blobby halos.

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
  -map "[v]" -map "[a2]" -c:v libx264 -crf 18 -preset slow -profile:v high -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart final.mp4
```

If the footage has no audio track, add `-f lavfi -i anullsrc=r=48000:cl=stereo` as a third
input. Use `[2:a]atrim=0:$MAIN,afade=...` in place of `[0:a]afade=...`, because the silent
source is endless and needs the trim (tested).

## 7. Audio

- Speech: `highpass=f=80`, plus a gentle `acompressor` if levels jump around.
- Music sits about 18–22 dB under the voice. Use licensed music only.
- Finish with loudness `loudnorm=I=-14:TP=-1.5:LRA=11` for social platforms.

## 8. QA

```bash
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate:format=duration -of compact final.mp4
ffmpeg -i final.mp4 -vf "fps=2,scale=180:-1,tile=10x2" -frames:v 1 sheet.png    # look at it
ffmpeg -ss 3 -i final.mp4 -frames:v 1 still.png                                 # full-size check
sha256sum $SK/assets/logo/nutrition-hub-logo.png   # must match the hash in SKILL.md
```

Then run through the checklist in SKILL.md §9.7.
