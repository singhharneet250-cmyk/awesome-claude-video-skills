/* Brand gradients on everything (owner, 2026-11-26: "gradient colour scheme in fonts as well as glass cards", then
 * "gradient colour scheme for overall things").
 * render.cjs adds this to every template and runs it after each __seek(t), so every template gets it without edits.
 * The brand's text colours become vertical gradients in the same family (top lighter, bottom deeper):
 *   ink    #46668C → #202B38 → #121922   headlines, labels, card copy
 *   orange #FDA65C → #F0782B → #DA5A1A   kickers, units, the accent word
 *   slate  #7C90A6 → #596879             body copy, sub-lines, source notes
 * Vertical, so a line animated word by word (or letter by letter) still reads as one ramp. Text on a pill, chip or
 * button (an element with its own background) keeps its solid colour, and any text in another colour (white on
 * orange, mist placeholders) is left exactly as it is. Re-checked every frame, so a colour that animates follows.
 *
 * Fills: every solid fill becomes a soft diagonal gradient of itself, lighter at the top left (where the light is) and
 * deeper at the bottom right: orange pills, toggles, bars and dots; ink buttons; ice tracks; white knobs, chips and
 * tiles (white to ice). Brand ink and orange use their exact ramps; any other colour (a toggle mid-way between ice
 * and orange) gets the same treatment from its own colour, so nothing pops while it animates.
 * SVG: orange and ink fills and strokes (rings, ticks, icons, cursor) take the same ramps through a shared <defs>.
 * Never on the logo (an <img>), photos or video.
 */
(() => {
  const INK = "linear-gradient(180deg, #46668C 0%, #202B38 62%, #121922 100%)";
  const ORANGE = "linear-gradient(180deg, #FDA65C 0%, #F0782B 55%, #DA5A1A 100%)";
  const SLATE = "linear-gradient(180deg, #7C90A6 0%, #596879 100%)";
  const MAP = {
    "rgb(32, 43, 56)": INK, "rgb(17, 17, 19)": INK,          // brand ink, charcoal-scheme ink
    "rgb(230, 109, 42)": ORANGE, "rgb(240, 120, 43)": ORANGE, // orange text, signal orange
    "rgb(89, 104, 121)": SLATE,
  };
  const ownText = (el) => {
    for (const n of el.childNodes) if (n.nodeType === 3 && n.textContent.trim()) return true;
    return false;
  };
  function clear(el) {
    el.style.backgroundImage = ""; el.style.webkitBackgroundClip = ""; el.style.backgroundClip = "";
    el.style.backgroundSize = ""; el.style.backgroundRepeat = ""; el.style.backgroundOrigin = "";
    delete el.dataset.nhG;
  }
  const typeGrad = (root) => {
    for (const el of root.querySelectorAll("*")) {
      if (!ownText(el) || el.closest("svg")) continue;
      const cs = getComputedStyle(el);
      const c = cs.color;                                 // our gradient never changes "color", so this stays true
      if (el.dataset.nhC === c) continue;                 // unchanged since the last frame: nothing to do
      el.dataset.nhC = c;
      const g = MAP[c];
      const ownBg = !el.dataset.nhG && (cs.backgroundImage !== "none" || cs.backgroundColor !== "rgba(0, 0, 0, 0)");
      if (g && !ownBg) {
        el.style.backgroundImage = g;
        el.style.webkitBackgroundClip = "text"; el.style.backgroundClip = "text";
        // one ramp per line, not one across a whole paragraph: repeat it every line height from the first line
        const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2;
        el.style.backgroundSize = `100% ${lh}px`; el.style.backgroundRepeat = "repeat-y"; el.style.backgroundOrigin = "content-box";
        el.style.webkitTextFillColor = "transparent";
        el.dataset.nhG = "1";
      } else {
        if (el.dataset.nhG) clear(el);
        el.style.webkitTextFillColor = "currentcolor";    // never inherit a gradient parent's transparent fill
      }
    }
  };

  // ---- fills -------------------------------------------------------------------------------------------------
  const ORANGE_FILL = "linear-gradient(150deg, #FDAA62 0%, #F0782B 58%, #E2611F 100%)";
  const INK_FILL = "linear-gradient(150deg, #46668C 0%, #202B38 60%, #121922 100%)";
  const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const v = m[1].split(",").map((x) => parseFloat(x)); return { r: v[0], g: v[1], b: v[2], a: v.length > 3 ? v[3] : 1 }; };
  const rgba = (r, g, b, a) => `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${a})`;
  function fillGrad(c) {
    const { r, g, b, a } = c;
    if (r === 240 && g === 120 && b === 43) return ORANGE_FILL;                                                            // brand orange
    if (r === 32 && g === 43 && b === 56) return INK_FILL;                                            // brand ink
    if (r > 245 && g > 245 && b > 245)                                                                // white: to ice
      return `linear-gradient(150deg, ${rgba(255, 255, 255, a)} 0%, ${rgba(255, 255, 255, a)} 40%, ${rgba(234, 240, 247, a)} 100%)`;
    const L = (k) => rgba(r + (255 - r) * k, g + (255 - g) * k, b + (255 - b) * k, a), D = (k) => rgba(r * (1 - k), g * (1 - k), b * (1 - k), a);
    return `linear-gradient(150deg, ${L(0.26)} 0%, ${rgba(r, g, b, a)} 58%, ${D(0.08)} 100%)`;
  }
  const fills = (root) => {
    for (const el of root.querySelectorAll("*")) {
      if (el.closest("svg") || el.tagName === "IMG" || el.tagName === "VIDEO" || el.tagName === "CANVAS" || el.dataset.nhG) continue;
      const cs = getComputedStyle(el);
      const bg = cs.backgroundColor;
      if (el.dataset.nhF !== undefined) {                         // ours: keep it in step with an animating colour
        if (el.dataset.nhF === bg) continue;
      } else if (cs.backgroundImage !== "none") continue;         // the page's own gradient, glass, photo: leave it
      const c = parse(bg);
      if (!c || c.a < 0.05) { if (el.dataset.nhF !== undefined) { el.style.backgroundImage = ""; delete el.dataset.nhF; } continue; }
      el.style.backgroundImage = fillGrad(c);
      el.dataset.nhF = bg;
    }
  };
  // ---- SVG -----------------------------------------------------------------------------------------------------
  function defs() {
    if (document.getElementById("nhg-orange")) return;
    const ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg");
    svg.setAttribute("width", "0"); svg.setAttribute("height", "0"); svg.style.position = "absolute";
    svg.innerHTML = `<defs>
      <linearGradient id="nhg-orange" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FDAA62"/><stop offset=".58" stop-color="#F0782B"/><stop offset="1" stop-color="#E2611F"/></linearGradient>
      <linearGradient id="nhg-ink" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#46668C"/><stop offset=".6" stop-color="#202B38"/><stop offset="1" stop-color="#121922"/></linearGradient></defs>`;
    document.body.appendChild(svg);
  }
  const SVG_MAP = { "rgb(240, 120, 43)": "url(#nhg-orange)", "rgb(230, 109, 42)": "url(#nhg-orange)", "rgb(32, 43, 56)": "url(#nhg-ink)" };
  const svgs = (root) => {
    const shapes = root.querySelectorAll("svg path, svg circle, svg rect, svg ellipse, svg polygon, svg polyline");
    if (!shapes.length) return;
    defs();
    for (const el of shapes) {
      if (el.closest("defs")) continue;
      let box; try { box = el.getBBox(); } catch (e) { continue; }
      if (box.width < 2 || box.height < 2) continue;              // a flat line: a bounding-box gradient would vanish
      const cs = getComputedStyle(el);
      for (const prop of ["fill", "stroke"]) {
        const u = SVG_MAP[cs[prop]];
        if (u) el.style[prop] = u;
      }
    }
  };
  window.__nhGrad = (root = document.body) => { typeGrad(root); fills(root); svgs(root); };
  if (typeof window.__seek === "function" && !window.__seek.nhGrad) {
    const seek = window.__seek;
    window.__seek = (t) => { const r = seek(t); window.__nhGrad(); return r; };
    window.__seek.nhGrad = true;
  }
  window.__nhGrad();
})();
