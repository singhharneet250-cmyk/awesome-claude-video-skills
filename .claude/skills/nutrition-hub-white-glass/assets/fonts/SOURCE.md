# Bundled accent fonts

The owner approved two accent faces on 2026-11-25. They are bundled here so renders
never fall back to another font. Inter stays the main typeface; see SKILL.md §3.

| File | Family | Use | Licence | Source |
|---|---|---|---|---|
| `InstrumentSerif-Italic.ttf` | Instrument Serif Italic | One orange accent word per line | SIL OFL 1.1 (`OFL-InstrumentSerif.txt`) | Google Fonts (fonts.gstatic.com, v5); licence text from npm `@fontsource/instrument-serif@5.3.0` |
| `BebasNeue-Regular.ttf` | Bebas Neue | One-word condensed slams | SIL OFL 1.1 (`OFL-BebasNeue.txt`) | Google Fonts (fonts.gstatic.com, v16); licence text from npm `@fontsource/bebas-neue@5.3.0` |

The OFL allows bundling and redistribution with the licence, but not selling the fonts on their own.

- **HTML templates:** load these fonts through `assets/brand.css`. This needs `scripts/render.cjs`, which allows file access.
- **ffmpeg/libass:** pass `fontsdir=<skill>/assets/fonts`.
