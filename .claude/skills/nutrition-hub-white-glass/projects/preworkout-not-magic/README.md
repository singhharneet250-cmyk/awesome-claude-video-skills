# Pre-workout Is NOT Magic

A 9:16 reel for Nutrition Hub Khanna: 1080×1920, 30 fps, 24.5 s, text-only explainer with no voiceover.
It is built from the client's "Google-style animations" storyboard, with original sound effects and no music.

## Files

| File | What it is |
|---|---|
| `index.html` | The animation. Every frame is a pure function of time (`window.__seek(t)`). |
| `out/preworkout-not-magic.mp4` | The finished reel: picture and sound effects at −13.9 LUFS. Add a music track inside Instagram if you want one. |
| `out/cover.png` | Reels cover frame (the "Pre-workout is NOT magic." hook). |
| `audio/sfx.py` | Generates every sound effect procedurally and places it on the timeline. Needs numpy only. |
| `qa/stills.cjs` | Renders QA stills at the times you pass it. |

## Look

The client chose two changes from the standard White Glass system for this reel:

- **Google-style four-colour accents.** Blue, red, yellow and green replace the White Glass orange.
  Each ingredient keeps one colour all the way through: 01 caffeine blue, 02 beta-alanine red,
  03 citrulline yellow and 04 creatine green.
  - Fills use the bright tones (`#4285F4`, `#EA4335`, `#FBBC05`, `#34A853`).
  - Words on white use darker text tones, and words on charcoal use light tones, so every key word stays readable.
- **Charcoal cards.** Cards are `#29292D` with white type, on the white stage. This matches the client's supplement-label reel.

These still follow the skill: the original logo file (sha256 checked), Inter, the white stage, the safe zones, calm
ease-out motion with no overshoot, and the content rules (every number has a unit and an on-screen source).
`scripts/qa.py` warns about stray hues on the green battery (14–15.5 s). That is the client's chosen green, not an error.

## Storyboard → build

| Time | Storyboard | As built |
|---|---|---|
| 0–2 s | The 4 dots bounce, pop into "NOT" with ripples, and "Pre-workout is … magic" blurs in on glass | The blue, red and yellow dots become N, O and T with colour ripples. The green dot becomes the full stop of "magic". The lines blur in on a charcoal card. |
| 2–4 s | The dots spin into a loader, which morphs into a scoop; the scoop shakes and 4 orbs fly to the corners | Same, with a colour-cycling loader. The orbs are charcoal with colour rings and are labelled 01–04 with their names. |
| 4–7 s | The blue orb grows into a card, a brain draws itself, a shield cracks and a sparkle lands on "ENERGY" | Same. The copy reads "Masks tiredness. Feels like energy." with 3–6 mg/kg and its source. |
| 7–10 s | The card swipes left, the red card slides in, a rep counter flips 8 → 10 → 12 and red dots jitter | Same swipe. The counter flips 01 → 14 → 28 days ("Builds up over 2–4 weeks at 4–6 g a day"), because a rep gain would be an unsourced result. Red dots jitter beside "That tingle? Harmless." |
| 10–13 s | The red card shrinks into a dot that becomes a yellow vein, a pulse travels along it, and "BIG PUMP" is stamped in | Same, under "More blood flow. via nitric oxide". |
| 13–16 s | The vein curls into a battery that fills green in 4 steps, and an "ATP" chip pops on with a sparkle | Same, with "Recharges your ATP battery. 3–5 g/day". |
| 16–19 s | The orbs orbit into a spinner ring around a clock, the ring counts down 30 → 20 min, and a ✕ wipes out a moon | The orbs lock onto a four-colour ring around a "60 min before training" clock, and the ring counts down. The moon chip reads "Not within 6 h of bedtime" with a red ✕. Both numbers are sourced. |
| 19–22 s | The ring unrolls into a search bar that types "best pre-workout for me?", a results card says "Comment PRE 👇", and the dots become the logo end card | Same, with an arrow icon instead of the emoji. The end transition is a Material circular reveal of four colour rings, then white. The dots converge as the original logo glass-reveals. |
| End | — | `@nutritionhubkhanna`, WhatsApp 9914571175, and "Comment PRE for help choosing". It runs to 24.5 s so the handle holds long enough to read. |

## Sources shown on screen

- Caffeine: 3–6 mg/kg; about 60 min before exercise is the most common timing. ISSN position stand, caffeine and exercise performance (Guest et al., 2021). <https://doi.org/10.1186/s12970-020-00383-4>
- Sleep: 400 mg of caffeine even 6 h before bed cut measured sleep by over 1 h. Drake et al., J Clin Sleep Med, 2013. <https://pubmed.ncbi.nlm.nih.gov/24235903/>
- Beta-alanine: 4–6 g a day for at least 2–4 weeks; tingling (paraesthesia) is the only reported side effect. ISSN position stand (Trexler et al., 2015). <https://doi.org/10.1186/s12970-015-0090-y>
- Citrulline: raises L-arginine and nitric oxide availability. Gonzalez & Trexler, J Strength Cond Res, 2020. <https://pubmed.ncbi.nlm.nih.gov/31977835/> No dose is shown, because the dose could not be confirmed from the source.
- Creatine: 3–5 g a day. ISSN position stand (Kreider et al., 2017).

## Render

From this folder:

```bash
node ../../scripts/render.cjs index.html --out video.mp4 --crf 16
python3 audio/sfx.py sfx.wav
ffmpeg -i video.mp4 -i sfx.wav -filter_complex "[1:a]acompressor=threshold=-32dB:ratio=4:attack=2:release=150:knee=6,volume=22dB,alimiter=limit=0.60:attack=0.8:release=50:level=disabled,aresample=48000[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest out/preworkout-not-magic.mp4
python3 ../../scripts/qa.py out/preworkout-not-magic.mp4 --expect 24.5
```

QA stills: `node qa/stills.cjs <outdir> 0.9 5.4 8.3`. Preview a frame in a browser with `index.html?t=5.4`.
