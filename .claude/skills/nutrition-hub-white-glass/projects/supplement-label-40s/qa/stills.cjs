// QA: render stills at given times into qa/ (deviceScaleFactor 1)
const { chromium } = require("playwright");
const path = require("node:path");
(async () => {
  const times = process.argv.slice(2).map(Number);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on("console", (m) => m.type() === "error" && console.error("[page]", m.text()));
  p.on("pageerror", (e) => console.error("[pageerror]", e.message));
  await p.goto("file://" + path.resolve(__dirname, "../index.html"));
  await p.evaluate(() => document.fonts.ready);
  await p.waitForFunction(() => window.__logoStatus !== "loading");
  console.log("logo:", await p.evaluate(() => window.__logoStatus));
  for (const t of times) {
    await p.evaluate((t) => window.__seek(t), t);
    await p.screenshot({ path: path.join(__dirname, `t${t.toFixed(2)}.png`) });
  }
  await b.close();
})();
