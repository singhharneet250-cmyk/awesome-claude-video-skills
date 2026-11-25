# B-roll shot list for Nutrition Hub Khanna

What to film once in the store, so every future reel can cut away to it (SKILL.md §4 F,
`scripts/broll.py`). Film the **Core 8** first. The rest can come later.

## How to film (every shot)

- **Vertical 9:16:** 1080×1920 or 4K at 30 fps. Pours and shakes at 60 fps, so they can play in slow motion.
- **HDR video off.** Otherwise colours wash out.
  - iPhone: Settings → Camera → Record Video → HDR Video off.
  - Android: switch off "HDR10+" or "HDR video" in the camera settings.
- **Bright, even, white light.** Switch off coloured LED strips, and wipe the lens.
- **Lock focus and exposure** (tap and hold on the subject).
- **Hold each shot 6–8 s.** Start moving 1 s after you press record. Use both hands or a gimbal.
- **Slow moves only:** a slow push, a slow slide or a still frame. No whip pans or quick zooms.
- **Take each shot twice:** once wide and once close.
- **Labels:** straight on, sharp, no glare. Tilt the tub slightly if the light reflects.
- **People:**
  - Anyone recognisable needs to have given written consent.
  - Keep other customers out of frame.
  - No personal details on phones, bills or screens.
- **No prices on screen** unless the reel is about a price; prices change.
- **Send the original files** (Google Drive, or upload them here), not WhatsApp copies, which are
  compressed.

## Name the files by what they show

`what-it-shows-NN.mp4`, all lowercase, with hyphens. For example `shelf-pan-01.mp4`,
`label-closeup-whey-01.mp4` or `scoop-02.mp4`. The edit matches spoken words to these names
(`--map label=label-closeup-whey-01.mp4`).

## The shots

| # | File name | What to film | Length | Used when the script says… |
|---|---|---|---|---|
| **Core 8** | | | | |
| 1 | `store-front-01` | Outside: the signboard, then a slow walk to the door | 8 s | "visit us", "our store", intros |
| 2 | `shelf-pan-01` | A slow sideways slide along a shelf of tubs, labels facing out | 8 s | "brands", "choose", "which one" |
| 3 | `pick-up-01` | A hand takes one tub off the shelf (3 takes) | 5 s | "buy", "pick", "before you buy" |
| 4 | `label-closeup-<product>-01` | The back label: the nutrition table, a slow tilt from top to bottom | 8 s | "label", "per serving", "ingredients", "sugar" |
| 5 | `scoop-01` | The scoop goes in, is levelled off and lifted out (60 fps) | 5 s | "scoop", "serving", "dose" |
| 6 | `shaker-pour-01` | Powder into the shaker, then water (60 fps) | 6 s | "mix", "shaker", "water" |
| 7 | `shake-01` | Lid on, shake, open (60 fps) | 4 s | "after workout", "drink" |
| 8 | `counter-01` | The counter from the customer's side, the owner behind it | 6 s | "ask us", "come in", the call to action |
| **Later** | | | | |
| 9 | `authenticity-check-01` | Scanning the authenticity code or QR on a tub (no personal data on the phone) | 5 s | "original", "fake", "authentic" |
| 10 | `seal-open-01` | Peel the seal, open the lid | 4 s | "fresh", "sealed" |
| 11 | `capsules-01` | Capsules or tablets poured into a palm | 4 s | "multivitamin", "omega", "tablets" |
| 12 | `scale-weigh-01` | A kitchen scale weighing one scoop, the grams readable | 5 s | "grams", "how much" |
| 13 | `protein-foods-01` | Paneer, eggs, dal, curd, chana on a white table, top-down, slow push | 6 s | "food", "diet", "protein from food" |
| 14 | `water-pour-01` | Water poured into a glass | 4 s | "water", "hydration" |
| 15 | `gym-lift-01` | A trainer or customer lifting, wide and close (consent) | 6 s | "workout", "strength", "recovery" |
| 16 | `owner-explains-01` | Over the shoulder: the owner points at a label for a customer (consent) | 6 s | "we help", "advice" |
| 17 | `aisle-walk-01` | A slow walk down the aisle, phone at chest height | 8 s | topic changes, "we stock" |
| 18 | `logo-wall-01` | The logo on the wall or the signboard, close and still | 5 s | outros, before the end card |

## B-roll made here, without filming

- **3D molecules** (creatine, caffeine and 15 more): `templates/molecule-3d.html`. Render 2–3 s as a cutaway.
- **Product hero** from a real cut-out photo: `templates/product-hero-3d.html`.
- **Photos:** a product or label photo becomes b-roll directly in `broll.py`. It gets a slow 4% push;
  a cut-out sits on an ice-mist stage.
- **Data callout cards:** `templates/reel-9x16.html`.
- **Protein and enzyme films:** the `molecular-film` skill (needs Blender and a GPU).

## Stock and AI b-roll

- **Stock:** only with a licence that allows business use. Record where each clip came from.
- **AI video:** only with the owner's OK. It spends the owner's credits on Runway or ManyMotions.
  - Never show products, labels, logos, results or real people's bodies.
  - Say it is AI-generated where the platform asks.
