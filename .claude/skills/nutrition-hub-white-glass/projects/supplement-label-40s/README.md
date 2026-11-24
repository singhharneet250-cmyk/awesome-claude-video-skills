# How to Read a Supplement Label in 40 Seconds

A 9:16 reel for Nutrition Hub Khanna: 1080×1920 at 30 fps, 60.8 s long, faceless explainer, timed to the recorded Hinglish voiceover.

## Files

- `index.html`: the composition. It uses a white stage with charcoal type, orange #FF7518 highlights, grey #29292D cards, particles and a progress bar.
- `out/supplement-label-40s.mp4`: the final video. It is H.264 High with yuv420p video and AAC 192 kb/s 48 kHz audio, and the voiceover sits at about −14.6 LUFS with peaks at −1.5 dBTP.
- `vo/vo-final.m4a`: the edited voiceover. This is the audio track used in the final video.
- `vo-hinglish.srt`: the voiceover lines with their timings in the edited voiceover. The wording follows the script. It was checked against the recording with offline keyword alignment, so proofread it before you use it as captions.

## Voiceover edit

The source is the client's recording "WhatsApp Video 2026-11-24 at 7.42.47 PM", which is 67.8 s long. Only its audio is used.

1. The repeated sentence "Protein ko scoop size se divide karo" was removed. It had been read twice, at 24.3 s and at 29.7 s in the raw recording. The cut is at 31.82 s raw, so the take keeps "Achhi whey mein lagbhag 70–80% protein hota hai".
2. Pauses were tightened to 0.45 s within a scene and 0.60 s at a scene change. The speech itself was not sped up.
3. The voice was processed with an 80 Hz high-pass filter and gentle 3:1 compression, then a two-pass loudnorm pass targeting −14 LUFS and −1.5 dBTP.

## Render

From this folder:

```bash
node ../../scripts/render.cjs index.html --out out/video-only.mp4 --crf 17
```

```bash
ffmpeg -i out/video-only.mp4 -i vo/vo-final.m4a -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 -t 60.8 -movflags +faststart out/supplement-label-40s.mp4
```

To render QA stills, run `node qa/stills.cjs 2.6 18.9 59` (times in seconds). It writes PNGs into `qa/`.

## Retiming

The time each scene starts and ends is set in `SC`, near the top of the `<script>`. Each `data-at` is measured from the start of its own scene. Each scene's custom function also has a few beat times written into it, so it hits the right words. For example, the scoop drops on "ek scoop", the rings fill on "divide karo", the tick lands on "utna better" and the end card comes in on "Nutrition Hub Khanna".

## Notes

- The 33 g / 24 g / 40 g values on the label are illustrative. They are marked "Example label" and "Example values" on screen.
- The voiceover says that good whey is about 70–80% protein. That figure is spoken only and is not shown on screen, because the brand rules require a source note for any on-screen number.
- The logo is the original `assets/logo/nutrition-hub-logo.png`, unaltered, shown on a white plate.
