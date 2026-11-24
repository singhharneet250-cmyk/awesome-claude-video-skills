# How to Read a Supplement Label in 40 Seconds

9:16 reel, 1080×1920, 30 fps, 42 s, faceless explainer for Nutrition Hub Khanna.

- `index.html`: the composition. White stage, charcoal type, orange #FF7518 highlights, grey #29292D cards, particles and a progress bar.
- `out/supplement-label-40s.mp4`: the rendered video. It has no audio, because the voiceover has not been recorded yet.
- `vo-hinglish.srt`: the Hinglish voiceover timed to each scene. Use it as a recording guide or as captions.

## Render

From this folder:

```bash
node ../../scripts/render.cjs index.html --out out/supplement-label-40s.mp4 --crf 17
```

Stills for QA: `node qa/stills.cjs 2.2 17.5 41.5` writes PNGs into `qa/`.

## Retime to the recorded voiceover

Edit `SC` (each scene's in/out time in seconds) near the top of the `<script>`. Every
`data-at` is relative to its scene start, so the animation inside each scene moves with it.

## Notes

- The 33 g / 24 g / 40 g label values are illustrative and marked "Example label" / "Example values".
- The logo is the original `assets/logo/nutrition-hub-logo.png`, unaltered, on a white plate.
