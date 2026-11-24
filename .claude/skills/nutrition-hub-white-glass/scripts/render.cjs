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
 * Options: --fps 30  --size 1080x1920  --from <s> (start, default 0)
 *          --duration <s> (default: page's window.__duration minus --from)
 *          --logo <path>  (original logo file, if not at assets/logo/)  --crf 16
 *
 * The page must expose window.__seek(t) and window.__duration (see templates/).
 * The render FAILS if the original logo did not load: there is no fallback mark.
 */
const { chromium } = require("playwright");
const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const { pathToFileURL } = require("node:url");

function parseArgs(argv) {
  const o = { fps: 30, size: "1080x1920", crf: 16, transparent: false };
  const pos = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) { pos.push(a); continue; }
    const key = a.slice(2);
    if (key === "transparent") { o.transparent = true; continue; }
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
  let codec;
  if (o.transparent && ext === ".mov") codec = ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"];
  else if (o.transparent && ext === ".webm") codec = ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "24", "-row-mt", "1"];
  else if (o.transparent) throw new Error("--transparent needs a .mov or .webm output");
  else codec = ["-c:v", "libx264", "-preset", "slow", "-crf", String(o.crf), "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart"];

  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "png", "-i", "-", ...codec, "-r", String(fps), o.out], { stdio: ["pipe", "inherit", "inherit"] });
  const done = new Promise((res, rej) => ff.on("close", (c) => (c === 0 ? res() : rej(new Error("ffmpeg exited " + c)))));

  for (let f = 0; f < frames; f++) {
    await page.evaluate((t) => window.__seek(t), from + f / fps);
    const buf = await shot();
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    if (f % fps === 0) process.stdout.write(`\r${f}/${frames} frames`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log(`\r${frames}/${frames} frames → ${o.out}`);
}

main().catch((e) => { console.error(e.message || e); process.exit(1); });
