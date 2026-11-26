#!/usr/bin/env node
/*
 * Render a White Glass HTML composition to video or a still.
 *
 *   node render.cjs <page.html> --out out.mp4            # H.264 MP4 (opaque)
 *   node render.cjs <page.html> --out overlay.mov --transparent   # ProRes 4444 with alpha
 *   node render.cjs <page.html> --out overlay.webm --transparent  # VP9 with alpha
 *   node render.cjs <page.html> --out frame.png --still 5.2       # one frame (QA, thumbnails)
 *
 *   node render.cjs <page.html> --out endcard.mp4 --from 8         # only t=8s → end
 *
 *   node render.cjs <page.html> --out reel.mp4 --blur 4             # motion blur: 4 sub-frames per frame
 *
 *   Real glass over footage (scripts/glass.py bends, frosts and lights the footage under each glass panel):
 *   node render.cjs <page.html> --transparent --real-glass --out content.mov   # words and icons, panels left clear
 *   node render.cjs <page.html> --transparent --glass-mask --out mask.mov      # only the panel shapes, solid white
 *   Type, fills and icons are drawn in brand gradients (assets/gradients.js); --flat keeps solid colours.
 *
 * Options: --fps 30  --size 1080x1920  --from <s> (start, default 0)
 *          --blur <n> sub-frames blended per frame over a half-frame shutter (180°): real motion blur on fast
 *          moves, nothing changes on still frames. 3-4 is plenty; render time grows n times. Default 1 (off).
 *          --duration <s> (default: page's window.__duration minus --from)
 *          --logo <path>  (original logo file, if not at assets/logo/)  --crf 12
 *
 * The page must expose window.__seek(t) and window.__duration (see templates/).
 * Video renders also write <out>.sfx.json, the sound-effect cue sheet for scripts/sfx.py (SKILL.md §5).
 * The render FAILS if the original logo did not load: there is no fallback mark.
 */
const { chromium } = require("playwright");
const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const { pathToFileURL } = require("node:url");

function parseArgs(argv) {
  const o = { fps: 30, size: "1080x1920", crf: 12, transparent: false };   // high quality (owner)
  const pos = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) { pos.push(a); continue; }
    const key = a.slice(2);
    if (key === "transparent") { o.transparent = true; continue; }
    if (key === "real-glass" || key === "glass-mask" || key === "flat-type" || key === "flat") { o[key] = true; continue; }
    o[key] = argv[++i];
  }
  o.page = pos[0];
  return o;
}

async function main() {
  const o = parseArgs(process.argv.slice(2));
  if (!o.page || !o.out) {
    console.error("usage: node render.cjs <page.html> --out <file.mp4|.mov|.webm|.png> [--still t] [--transparent]");
    process.exit(2);
  }
  const [W, H] = o.size.split("x").map(Number);
  const fps = Number(o.fps);
  const [pagePath, query] = o.page.split("?");          // "page.html?molecule=caffeine" passes URL params
  const url = pathToFileURL(path.resolve(pagePath));
  if (query) new URLSearchParams(query).forEach((v, k) => url.searchParams.set(k, v));
  if (o.transparent) url.searchParams.set("transparent", "1");
  if (o.logo) url.searchParams.set("logo", pathToFileURL(path.resolve(o.logo)).href);

  // --allow-file-access-from-files lets the 3D templates load three.js as ES modules from file://
  const browser = await chromium.launch({ args: ["--allow-file-access-from-files", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"] });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on("console", (m) => { if (m.type() === "error") console.error("[page]", m.text()); });
  await page.goto(url.href, { waitUntil: "load" });
  await page.evaluate(() => Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 4000))]));
  await page.waitForFunction(() => window.__logoStatus !== "loading", null, { timeout: 10000 }).catch(() => {});
  const logoStatus = await page.evaluate(() => window.__logoStatus ?? "none");
  if (logoStatus === "missing" || logoStatus === "loading") {
    await browser.close();
    throw new Error("Original Nutrition Hub logo did not load. Put it at assets/logo/nutrition-hub-logo.png or pass --logo <file>. Never substitute a redraw.");
  }
  // 3D pages build asynchronously (modules, data, textures): wait for __seek, or for the page's own error
  await page.waitForFunction(() => typeof window.__seek === "function" || window.__error, null, { timeout: 60000 }).catch(() => {});
  const pageError = await page.evaluate(() => window.__error);
  if (pageError) { await browser.close(); throw new Error(`Page failed to build: ${pageError}`); }
  const hasSeek = await page.evaluate(() => typeof window.__seek === "function");
  if (!hasSeek) { await browser.close(); throw new Error("Page has no window.__seek(t) — use a template from templates/."); }

  // Brand gradients on everything (owner, 2026-11-26): type, fills and SVG icons (assets/gradients.js), re-checked
  // after every seek. --flat keeps solid colours (--flat-type is the old name).
  if (o.flat === undefined && o["flat-type"] === undefined && o["glass-mask"] === undefined)
    await page.addScriptTag({ content: fs.readFileSync(path.join(__dirname, "..", "assets", "gradients.js"), "utf8") });

  // Real-glass passes (SKILL.md §4 A): the content pass leaves glass panels clear; the mask pass draws only them
  if (o["real-glass"] !== undefined) await page.addStyleTag({ content: `
    .nh-glass { background: transparent !important; -webkit-backdrop-filter: none !important; backdrop-filter: none !important;
      border-color: transparent !important; box-shadow: none !important; }` });   /* clear glass: no drop shadow */
  if (o["glass-mask"] !== undefined) await page.addStyleTag({ content: `
    html, body, .nh-stage { background: transparent !important; }
    body * { visibility: hidden !important; }
    .nh-glass { visibility: visible !important; background: #FFFFFF !important; border-color: #FFFFFF !important; box-shadow: none !important;
      -webkit-backdrop-filter: none !important; backdrop-filter: none !important; }
    .nh-glass::before, .nh-glass::after { display: none !important; }
    .nh-glass * { visibility: hidden !important; }` });
  if (o["glass-mask"] !== undefined || o["real-glass"] !== undefined) await page.evaluate(() => window.__seek(0));
  const shot = () => page.screenshot({ type: "png", omitBackground: o.transparent });

  if (o.still !== undefined || o.out.endsWith(".png")) {
    const t = Number(o.still ?? 0);
    await page.evaluate((t) => window.__seek(t), t);
    fs.writeFileSync(o.out, await shot());
    await browser.close();
    console.log(`still @ ${t}s → ${o.out}`);
    return;
  }

  const from = Number(o.from ?? 0);
  const duration = Number(o.duration ?? (await page.evaluate(() => window.__duration)) - from);
  const frames = Math.round(duration * fps);
  const ext = path.extname(o.out).toLowerCase();

  // SFX cue sheet (SKILL.md §5 Sound) for scripts/sfx.py: read from the page's own animations,
  // or from window.__sfx = [{t, sfx, what}] when a page lists its cues itself
  const cues = await page.evaluate(() => {
    if (Array.isArray(window.__sfx)) return window.__sfx;
    const at = (el) => parseFloat(getComputedStyle(el).getPropertyValue("--at")) || 0;
    const name = (el) => (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 40);
    const out = [];
    // a slam is fully opaque and near full size 0.18 s into its 0.32 s entrance (measured): the thud lands there
    document.querySelectorAll(".nh-slam").forEach((el) => out.push({ t: at(el) + 0.18, sfx: "thud", what: "slam: " + name(el) }));
    document.querySelectorAll(".nh-reveal").forEach((el) => {
      if (el.matches(".nh-logo, :has(.nh-logo)")) {   // glass marks the logo reveal (end card), not a header logo there from the start
        if (at(el) >= 1.0) out.push({ t: at(el) + 0.1, sfx: "glass", what: "logo" });
      }
      else if (el.matches(".nh-chip, .nh-check, .fact")) out.push({ t: at(el) + 0.06, sfx: "tick", what: name(el) });
      else if (el.matches(".nh-glass, .nh-callout")) out.push({ t: at(el) + 0.06, sfx: "pop", what: "card: " + name(el) });
    });
    return out.sort((a, b) => a.t - b.t);
  });
  const inWindow = cues.filter((c) => c.t >= from && c.t < from + duration)
    .map((c) => ({ ...c, t: Math.round((c.t - from) * 1000) / 1000 }));
  if (inWindow.length) {
    const cueFile = o.out.replace(/\.[^.]+$/, "") + ".sfx.json";
    fs.writeFileSync(cueFile, JSON.stringify(inWindow, null, 2));
    console.log(`${inWindow.length} SFX cues → ${cueFile} (add them with scripts/sfx.py --cues)`);
  }
  let codec;
  if (o.transparent && ext === ".mov") codec = ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"];
  else if (o.transparent && ext === ".webm") codec = ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "24", "-row-mt", "1"];
  else if (o.transparent) throw new Error("--transparent needs a .mov or .webm output");
  else codec = ["-c:v", "libx264", "-preset", "slow", "-crf", String(o.crf), "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart"];

  // motion blur (learned from the prompt-motion build notes): n sub-frames per frame spread over a 180° shutter,
  // averaged by ffmpeg tmix; then one blended frame is kept per output frame
  const blur = Math.max(1, Math.round(Number(o.blur ?? 1)));
  const SHUTTER = 0.5;
  const blurVf = blur > 1 ? ["-vf", `tmix=frames=${blur},select='eq(mod(n\\,${blur})\\,${blur - 1})',setpts=N/(${fps}*TB)`] : [];
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps * blur), "-c:v", "png", "-i", "-", ...blurVf, ...codec, "-r", String(fps), o.out], { stdio: ["pipe", "inherit", "inherit"] });
  const done = new Promise((res, rej) => ff.on("close", (c) => (c === 0 ? res() : rej(new Error("ffmpeg exited " + c)))));

  for (let f = 0; f < frames; f++) {
    for (let k = 0; k < blur; k++) {
      const dt = blur > 1 ? ((k + 0.5) / blur - 0.5) * SHUTTER / fps : 0;      // centred on the frame time
      await page.evaluate((t) => window.__seek(t), Math.max(0, from + f / fps + dt));
      const buf = await shot();
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    }
    if (f % fps === 0) process.stdout.write(`\r${f}/${frames} frames`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log(`\r${frames}/${frames} frames → ${o.out}`);
}

main().catch((e) => { console.error(e.message || e); process.exit(1); });
