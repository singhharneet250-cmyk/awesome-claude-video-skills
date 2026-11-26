/* Gradient type (owner, 2026-11-26: "use gradient colour scheme in fonts as well as glass cards").
 * render.cjs adds this to every template and runs it after each __seek(t), so every template gets it without edits.
 * The brand's text colours become vertical gradients in the same family (top lighter, bottom deeper):
 *   ink    #46668C → #202B38 → #121922   headlines, labels, card copy
 *   orange #FDA65C → #F0782B → #DA5A1A   kickers, units, the accent word
 *   slate  #7C90A6 → #596879             body copy, sub-lines, source notes
 * Vertical, so a line animated word by word (or letter by letter) still reads as one ramp. Text on a pill, chip or
 * button (an element with its own background) keeps its solid colour, and any text in another colour (white on
 * orange, mist placeholders) is left exactly as it is. Re-checked every frame, so a colour that animates follows.
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
  window.__nhGrad = (root = document.body) => {
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
  if (typeof window.__seek === "function" && !window.__seek.nhGrad) {
    const seek = window.__seek;
    window.__seek = (t) => { const r = seek(t); window.__nhGrad(); return r; };
    window.__seek.nhGrad = true;
  }
  window.__nhGrad();
})();
