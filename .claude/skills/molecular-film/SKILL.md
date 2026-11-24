---
name: molecular-film
description: Blender-grade, scientifically honest molecular films (proteins, enzymes, peptides, nucleic acids and their ligands) for Nutrition Hub supplement education, using the open-source Molecular_Animation framework (Apache-2.0) with the White Glass look. Use when a reel needs a real protein structure from the PDB or AlphaFold (whey's beta-lactoglobulin, collagen, an enzyme a supplement acts on) rendered photoreal in Cycles with measured thermal motion. For a small molecule (creatine, caffeine, amino acids, vitamin C) use the faster three.js template nutrition-hub-white-glass/templates/molecule-3d.html instead. Needs Blender 5.2 and ideally an NVIDIA GPU, so it runs on the user's own machine.
---

# Molecular film (White Glass edition)

[Molecular_Animation](https://github.com/AmadeusBio-ai/Molecular_Animation) turns a brief plus PDB/mmCIF or
AlphaFold structures into a Blender 5.2 film: proteins as cartoons or spheres, ligands as ball-and-stick, thermal
motion at literature rates, depth of field, and a production record that says what is experimental and what is
illustrative. This skill sets it up at a reviewed commit and gives it the White Glass look. The film then goes
through the normal Nutrition Hub pipeline (captions, callouts, end card, QA).

Load `nutrition-hub-white-glass` first. Its rules win over the framework's defaults (palette, type, motion, §8 evidence).

## When to use which

| Subject | Use |
|---|---|
| A small molecule: creatine, caffeine, BCAAs, beta-alanine, taurine, vitamin C, melatonin… | `nutrition-hub-white-glass/templates/molecule-3d.html` (three.js, renders anywhere in minutes) |
| A protein or peptide with a real deposited structure, a ligand in its pocket, an enzyme mechanism | this skill (Blender Cycles, hours of GPU time for a full film) |
| A photoreal B-roll shot (powder pouring, a shaker, a gym) | a video model (Runway, ManyMotions, Veo): see SKILL.md §10, never for packaging |

## Requirements (the user's machine)

- Blender **5.2** (`BLENDER` env var if not on the default path), an NVIDIA GPU with OptiX for sane render times
  (about 19 s per 1080p Cycles frame at 128 samples on an RTX 5060 Ti; plan the render before starting it).
- Python 3.10+, `ffmpeg` with libx264 and libvpx-vp9, network access to `files.rcsb.org` to fetch structures.
- The cloud container cannot run this: it has no Blender 5.2, no GPU and no route to RCSB. Use it there only to
  write the brief and the shot constants.

## Set up once, at the reviewed commit

```bash
git clone https://github.com/AmadeusBio-ai/Molecular_Animation.git ~/molecular-animation
cd ~/molecular-animation
git checkout 14bf9e49026446aa850ca190d4bf5c69a3f2b43a     # the commit reviewed for this skill
pip install -r requirements.txt                          # numpy, Pillow
python pipeline.py doctor                                # Blender, GPU, ffmpeg, checksums
python -m pytest tests                                   # science layer, no Blender needed
```

Update only on purpose: read the new commits, then change the hash here.

## Make a film

1. Run Claude Code **inside `~/molecular-animation`** so its own `/new-film` skill and `AGENTS.md` load, or read
   `.claude/skills/new-film/SKILL.md` and `docs/workflow.md` there and follow them. They are the authority on the
   science steps: brief, structures with evidence levels, measured claims, look-dev, preview, final, record.
2. Scaffold a vertical reel: `python pipeline.py new <name> --pdb <ID> --fps 30 --seconds 8 [--highlight <residues>]`
   (add `--loop` for a seamless orbit). Choose the PDB entry from RCSB yourself and write its ID, method and
   resolution into `brief.md`; don't take an ID from memory.
3. In `projects/<name>/<name>.py`, set the frame and the White Glass look below, then build, still, preview and render
   as the workflow says.
4. Deliver the **clean** take (no framework labels) and finish it in the Nutrition Hub pipeline.

## White Glass look constants

Replace these constants in the shot script (sRGB 0–255). They keep the palette at white, ice, ink and one orange
accent (SKILL.md §2): no teal, green or purple chains, and no CPK blue nitrogen or red oxygen.

```python
RES = (1080, 1920)                                   # 9:16 reel; keep (1920, 1080) for 16:9 education films
BACKDROP_TOP, BACKDROP_BOTTOM = (255, 255, 255), (234, 240, 246)   # porcelain → ice mist
AMBIENT_RGB, AMBIENT_STRENGTH = (240, 244, 248), 0.5
CHAIN_TONES = [((222, 228, 235), (246, 248, 250)),   # porcelain ceramic
               ((196, 207, 219), (234, 240, 246)),   # ice
               ((140, 154, 170), (198, 208, 220))]   # mist slate, for a second chain
ACCENT_C = ((240, 120, 43), (253, 170, 98))         # signal orange #F0782B → #FDAA62: the one focal point
ELEMENT = {'C': ((226, 230, 235), (246, 248, 250)), 'N': ((188, 200, 214), (222, 230, 238)),
           'O': ((204, 212, 222), (236, 240, 245)), 'S': ((170, 182, 196), (214, 222, 230)),
           'P': ((170, 182, 196), (214, 222, 230))}  # elements told apart by tone and size, never by hue
SECTION_RGB, SECTION_MIX = (234, 240, 246), 0.35
BLOOM = {'threshold': 1.0, 'strength': 0.12, 'size': 0.4}   # no glow look (§4 B: avoid glowing particles)
LABELS_ON = False                                    # labels come from the White Glass overlay instead
```

Motion stays the framework's (measured thermal motion, one clock): it is physics, not decoration. Keep camera
moves calm: no whip moves, no zoom punches (§5). Keep its depth of field: it is the "shallow depth of field" the
brand asks for.

## Back into the Nutrition Hub pipeline

- Labels, evidence tags and the source go on White Glass callouts, not burned in by Blender:
  `templates/overlay-callout.html` rendered with `--transparent`, timed with `timeline.label_data` (the framework
  exports its label timings as data). Keep its honesty: say "motion illustrative" and name the PDB entry and method
  in the source note, e.g. "Structure: PDB <ID> (X-ray, <res> Å). Motion illustrative."
- Composite, caption, end card and loudness as in `nutrition-hub-white-glass/reference/footage-editing.md`.
- Run `python3 scripts/qa.py final.mp4` from the brand skill: the stray-hue check catches any framework colour that slipped through.
