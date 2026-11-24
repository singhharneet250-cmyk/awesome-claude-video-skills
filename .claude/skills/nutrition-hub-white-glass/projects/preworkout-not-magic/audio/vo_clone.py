"""Voiceover in the client's own voice (with their go-ahead), cloned with Chatterbox Multilingual (MIT licence).

The reference is ~10 s of the client's recording from the label reel
(projects/supplement-label-60s/vo/vo-final.m4a, 15.3–25.3 s, mono 24 kHz).
Each line of vo-script.md is generated as several seeded takes, so the best take can be picked by ear or ASR.

    python vo_clone.py <ref.wav> <outdir> [--takes 2] [--lines 1,4]

Needs: pip install chatterbox-tts (downloads ResembleAI/chatterbox from Hugging Face on first run).
Output: <outdir>/line<N>_take<K>.wav at the model's sample rate (24 kHz).
Chatterbox adds an inaudible Perth watermark to everything it generates.
"""
import argparse
from pathlib import Path

import torch
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

# Hinglish written in Devanagari (the model reads Hindi from Devanagari); English terms transliterated.
LINES = [
    "प्री-वर्कआउट कोई मैजिक नहीं है।",
    "एक स्कूप, चार इंग्रेडिएंट्स, चार काम।",
    "कैफ़ीन थकान छुपाता है, इसलिए एनर्जी फ़ील होती है।",
    "बीटा-एलानिन की झुनझुनी हार्मलेस है। रोज़ लेने पर असर, दो से चार हफ़्ते में आता है।",
    "सिट्रुलिन ब्लड फ़्लो बढ़ाता है, इसलिए पंप मिलता है।",
    "क्रिएटिन आपकी ए टी पी बैटरी, री-चार्ज करता है। रोज़ तीन से पाँच ग्राम।",
    "ट्रेनिंग से एक घंटा पहले लो, पर सोने से छह घंटे के अंदर नहीं।",
    "आपके लिए कौन सा प्री-वर्कआउट सही है? कमेंट करो, प्री।",
    "न्यूट्रिशन हब खन्ना। जेन्युइन सप्लीमेंट्स, सही गाइडेंस।",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref")
    ap.add_argument("outdir")
    ap.add_argument("--takes", type=int, default=2)
    ap.add_argument("--lines", default="")
    ap.add_argument("--exaggeration", type=float, default=0.5)
    ap.add_argument("--cfg", type=float, default=0.5)
    ap.add_argument("--temperature", type=float, default=0.75)
    a = ap.parse_args()

    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    pick = [int(x) for x in a.lines.split(",") if x] or list(range(1, len(LINES) + 1))
    torch.set_num_threads(max(1, torch.get_num_threads()))
    model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    for n in pick:
        for k in range(1, a.takes + 1):
            path = out / f"line{n}_take{k}.wav"
            if path.exists():
                continue                    # keep earlier takes; raise --takes to add more
            torch.manual_seed(1000 * n + k)
            wav = model.generate(LINES[n - 1], language_id="hi", audio_prompt_path=a.ref,
                                 exaggeration=a.exaggeration, cfg_weight=a.cfg, temperature=a.temperature)
            ta.save(str(path), wav, model.sr)
            print(f"{path.name}  {wav.shape[-1] / model.sr:.2f} s", flush=True)


if __name__ == "__main__":
    main()
