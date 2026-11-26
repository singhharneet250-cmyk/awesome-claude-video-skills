#!/usr/bin/env python3
"""
High-quality output (owner, 2026-11-26: "output quality must be in high quality"). One place for every encode:

  WORK   steps in between (timeline stages, effects, glass, cut-outs): visually lossless (x264 CRF 10), so a reel
         that passes through eight steps doesn't lose a little at each one
  FINAL  the file that is delivered: x264 High, CRF 14, preset slow, BT.709 tags, at most 30 Mbit/s (Instagram,
         YouTube and TikTok all take it and re-encode from a clean master), AAC 256 kbit/s 48 kHz, faststart
  scale  enlarging uses Lanczos plus a light unsharp; anything below 1080x1920 is flagged (send the original
         camera file, not a WhatsApp copy: WhatsApp shrinks video to about 576x1024 at 1.3 Mbit/s)

    python3 encode.py deliver in.mp4 out.mp4      # any file -> the FINAL delivery encode (audio copied if AAC)
    python3 encode.py check take.mp4               # resolution, bitrate and whether it will be enlarged

For a platform size cap (WhatsApp 16 MB) use the halfsize skill on the delivered file, never on the master.
"""
import json
import subprocess
import sys

WORK = ["-c:v", "libx264", "-crf", "10", "-preset", "fast", "-pix_fmt", "yuv420p"]
FINAL = ["-c:v", "libx264", "-crf", "14", "-preset", "slow", "-profile:v", "high", "-level:v", "4.2", "-pix_fmt", "yuv420p",
         "-maxrate", "30M", "-bufsize", "60M", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
         "-movflags", "+faststart"]
AUDIO = ["-c:a", "aac", "-b:a", "256k", "-ar", "48000"]
UPSCALE_SHARPEN = "unsharp=5:5:0.45:5:5:0"


def scale(w, h, src_w=None, src_h=None):
    """The fill-and-crop scale to w x h, Lanczos, with a light sharpen when it enlarges."""
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}"
    if src_w and src_h and max(w / src_w, h / src_h) > 1.05:
        vf += "," + UPSCALE_SHARPEN
    return vf


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,bit_rate",
                        "-show_entries", "format=bit_rate,duration", "-of", "json", str(path)], capture_output=True, text=True)
    j = json.loads(r.stdout or "{}")
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in j.get("streams", []) if s.get("codec_type") == "audio"), {})
    fmt = j.get("format", {})
    return {"w": int(v.get("width", 0)), "h": int(v.get("height", 0)), "vcodec": v.get("codec_name"),
            "vbr": int(v.get("bit_rate") or fmt.get("bit_rate") or 0), "acodec": a.get("codec_name"),
            "dur": float(fmt.get("duration", 0) or 0)}


def source_note(path, w=1080, h=1920):
    """None when the source is big enough; otherwise a plain sentence for the owner."""
    p = probe(path)
    if not p["w"]:
        return None
    k = max(w / p["w"], h / p["h"]) if p["w"] < p["h"] else max(w / p["h"], h / p["w"])
    if k <= 1.05:
        return None
    return (f"source is {p['w']}x{p['h']} at {p['vbr'] / 1e6:.1f} Mbit/s, enlarged {k:.1f}x: for full detail send the "
            f"original camera file (in WhatsApp, attach it as a Document, or share it by Google Drive)")


def deliver(src, out):
    """src (any) -> out with the FINAL settings; AAC audio is copied, anything else re-encoded at 256k."""
    a = probe(src)
    audio = ["-c:a", "copy"] if a["acodec"] == "aac" else AUDIO
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", str(src), "-map", "0:v", "-map", "0:a?",
                        *FINAL, *audio, str(out)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-800:])
    return out


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("deliver", "check"):
        sys.exit(__doc__)
    if sys.argv[1] == "check":
        p = probe(sys.argv[2])
        print(f"{p['w']}x{p['h']} {p['vcodec']} {p['vbr'] / 1e6:.1f} Mbit/s, audio {p['acodec']}, {p['dur']:.1f} s")
        print(source_note(sys.argv[2]) or "big enough for 1080x1920: no enlarging")
        return
    if len(sys.argv) != 4:
        sys.exit("encode.py deliver in.mp4 out.mp4")
    deliver(sys.argv[2], sys.argv[3])
    p = probe(sys.argv[3])
    print(f"wrote {sys.argv[3]}: {p['w']}x{p['h']}, {p['vbr'] / 1e6:.1f} Mbit/s")


if __name__ == "__main__":
    main()
