# How to Read a Supplement Label in 40 Seconds

A 9:16 reel for Nutrition Hub Khanna: 1080×1920, 30 fps, 59.9 s, faceless explainer.
It is timed to the recorded Hinglish voiceover and finished with music, original sound design and VFX.

## What is in this repo (and what is not)

This repository is **public**, so the licensed Epidemic Sound music is kept out of it.
The final master with music, and the stems, were delivered to the client directly.

| File | What it is |
|---|---|
| `index.html` | The animation: white stage, charcoal type, orange #FF7518 accents, grey #29292D cards, plus the VFX (see below). |
| `out/supplement-label-40s_no-music.mp4` | Voiceover, sound effects and VFX with no music. Use it if you want to add a trending track inside Instagram. It sits at −13.6 LUFS. |
| `out/cover.png` | The Reels cover frame (hook headline and tub), 1080×1920. |
| `vo/vo-final.m4a` | The edited and cleaned voiceover only. |
| `vo-hinglish.srt` | The voiceover lines timed to the final cut, for captions. Proofread before use. |
| `audio/sfx.py` | Generates every sound effect procedurally and places it on the timeline. They are original and royalty-free. |
| `audio/mix.filter` | The ffmpeg mix graph: voiceover chain, music EQ with sidechain ducking, and the effects bus. |

## Audio

- **Voiceover.** The source is the client's WhatsApp recording, audio only. Two edits were made:
  - At 29.7 s raw, the duplicated sentence "Protein ko scoop size se divide karo" was removed.
  - At 37.6 s raw, the false start "Agar fat…" was removed. This was the repeat heard at about 31 s in the previous cut.

  Pauses were tightened to 0.45 s within a scene and 0.60 s at a scene change. The speech itself was not sped up. The voice chain is an 80 Hz high-pass filter, a light de-esser and 3:1 compression.
- **Music.** "Just Wanna Come Alive (Instrumental Version)" by SOOP (Epidemic Sound, recording `21df0c7a-4c19-464a-be75-689d18e5ac62`). An Epidemic Sound edit cut it to exactly 59.9 s, with its ending landing on the end card. The edit is job `55b2e37c-67f4-43d8-b808-872b238a540a`, edit `b381e350-09ee-48d1-a165-1b1155be0fba`. The mix applies a 3.5 dB EQ dip at 2.8 kHz to leave room for the voice. Sidechain ducking keeps the music about 13 dB under the voice, it comes back up in the gaps, and it lifts slightly on the end card.
- **Sound effects.** There are 88 events, all synthesised in `audio/sfx.py`:
  - an opening hit, whooshes on the tub spin and every scene change, and scanner sweeps on the label
  - rising pops on the four checkpoints
  - a scoop thud, 33 scale ticks locked to the digits, a scale beep and a bracket lock
  - the ring-fill tone, the winner chime, sugar-cube clinks, the warning tone, a marker swipe and the amino-tag pops
  - genuine-check chimes, phone taps for "LABEL", the reply ping, and the logo shimmer with a soft low bloom
- **Master.** −13.8 LUFS integrated, true peak −2.3 dBTP after AAC, AAC 256 kb/s at 48 kHz.

## VFX (all in `index.html`)

- A slow camera push-in (2.8 %) across every shot. Scenes 1 and 2 count as one continuous shot so the Nutrition Facts card stays aligned.
- Background depth drift on the large white discs.
- A soft blur on every scene exit, as a dip to the white stage.
- A thin orange scan streak at each scene change, matching the label-scan look.
- Light sweeps across the cards as they land, and again on the winning scoop.
- Orange ripples on the four checkpoints, the winner tick and the three genuine-check ticks.
- An impact ring where the scoop lands on the scale, and a glow on the LCD when the count settles.
- A glowing head on the progress bar.
- Everything from before is unchanged: the tub spin with its label zoom and scan, kinetic type, counters, rings, falling cubes, typing, and the logo reveal.

## Render

From this folder:

```bash
node ../../scripts/render.cjs index.html --out video-only.mov --crf 12
```

```bash
python3 audio/sfx.py sfx.wav
```

Then mix with `audio/mix.filter`. Its inputs are the tightened voiceover, the music edit and `sfx.wav`. Add +6.4 dB and run `alimiter` with a limit of 0.72, then mux with `-c:v libx264 -crf 16 -c:a aac -b:a 256k -movflags +faststart`.

QA stills: `node qa/stills.cjs 2.9 24.0 54.8`.

## Notes

- The 33 g / 24 g / 40 g label values are illustrative. They are marked "Example label" and "Example values" on screen.
- The voiceover says good whey is about 70–80% protein. That figure is spoken only and is not shown on screen, because the brand rules require a source note for any on-screen number.
- The logo is the original `assets/logo/nutrition-hub-logo.png`, unaltered, on a white plate.
- Epidemic Sound licence: posting this for a business (a supplement store) needs an Epidemic **commercial** plan, not a personal one.
