# Source

Vendored on 2026-11-27 at the owner's request (from agentskillshub.top/best/claude-video-skills: "Install the best ones",
Manim skill chosen). This note covers all three folders: `manim-composer`, `manimce-best-practices`,
`manimgl-best-practices`.

- Upstream: https://github.com/adithya-s-k/manim_skill @ `cef0450` (2026-01-24), folder `skills/`
- Licence: MIT (`LICENSE`, copied unchanged into each folder; the two best-practice folders also had their own
  `LICENSE.txt` upstream, kept).
- Read before vendoring: instructions, examples and templates only; no scripts that reach the network.

## Use for Nutrition Hub

Manim draws clean animated science diagrams (how a vitamin is absorbed, a dose curve, a ratio) as video. Plan with
`manim-composer`, build with `manimce-best-practices` (Manim Community, `pip install manim`). Brand rules still apply:
white or ice background, ink type, Logo Red #D30204 as the one accent, Inter for text, no shadows beside words, and a
unit and a source on every number. Render the Manim scene as a clip and place it in the reel with `scripts/timeline.py`.

Manim needs `pip install manim` (plus LaTeX for `MathTex`); it is not installed in this cloud container by default.

## Not included here

`tests/` and the upstream `README.md` (development material).

## Changes in this copy

Each `SKILL.md`: the frontmatter description starts with the companion note. Everything else is upstream as-is.
