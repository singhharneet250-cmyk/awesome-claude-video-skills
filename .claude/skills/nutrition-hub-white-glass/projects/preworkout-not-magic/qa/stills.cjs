// QA: render stills at given times (deviceScaleFactor 1).
// usage: node qa/stills.cjs <outdir> 0.6 5.5 ...
const { chromium } = require("playwright");
const path = require("node:path");
(async () => {
  const [outdir, ...rest] = process.argv.slice(2);
  const times = rest.map(Number);
  const b = await chromium.launch({ args: ["--allow-file-access-from-files"] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on("console", (m) => m.type() === "error" && console.error("[page]", m.text()));
  p.on("pageerror", (e) => console.error("[pageerror]", e.message));
  await p.goto("file://" + path.resolve(__dirname, "../index.html"));
  await p.waitForFunction(() => typeof window.__seek === "function" && window.__logoStatus !== "loading", null, { timeout: 15000 });
  console.log("logo:", await p.evaluate(() => window.__logoStatus));
  for (const t of times) {
    await p.evaluate((t) => window.__seek(t), t);
    await p.screenshot({ path: path.join(outdir, `t${t.toFixed(2).padStart(5, "0")}.png`) });
  }
  await b.close();
})();
