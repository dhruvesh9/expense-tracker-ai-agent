// Skeleton loading states. They reuse the REAL layout classes (strip, card, table, rank ...)
// so the page keeps the same geometry while data loads: no layout jump when content arrives.

import { h } from "./ui.js";

const SIZES = [64, 82, 58, 94, 70, 88, 52, 76]; // fixed widths: deterministic, no flicker on re-render

/** One shimmering placeholder block. */
export const bone = (width, height = 12, cls = "") =>
  h("span", { class: `bone ${cls}`.trim(), style: { width: typeof width === "number" ? `${width}px` : width, height: `${height}px` } });

const busy = (node) => { node.setAttribute("aria-busy", "true"); return node; };

export function skKpiStrip(n = 5) {
  return busy(h("div", { class: "strip", "aria-label": "Loading figures" }, Array.from({ length: n }, () =>
    h("div", { class: "kpi" }, bone(72, 11), bone(120, 28), h("div", { class: "kpi-foot" }, bone(88, 11), bone(72, 24))))));
}

export function skInsights(n = 3) {
  return busy(h("div", { class: "strip" }, Array.from({ length: n }, (_, i) =>
    h("div", { class: "insight" }, bone(150 + i * 12, 13), bone(210, 11)))));
}

/** A card with a title/subtitle skeleton header; `body` is any node. */
export function skCard({ body, sub = true, controls = false, flush = false } = {}) {
  return busy(h("section", { class: `card${flush ? " flush" : ""}` },
    h("div", { class: "card-header" },
      h("div", { class: "stack", style: { gap: "8px" } }, bone(130, 14), sub ? bone(190, 11) : null),
      controls ? bone(96, 32) : null),
    body));
}

/** Chart placeholder: faint gridlines with an area shape (or bars). */
export function skChart({ height = 280, bars = false } = {}) {
  const body = bars
    ? h("div", { class: "sk-bars" }, SIZES.slice(0, 7).map((s) => bone("100%", Math.round((s / 100) * height * 0.9))))
    : (() => {
      const wrap = h("div");
      wrap.innerHTML = '<svg viewBox="0 0 100 40" preserveAspectRatio="none"><path class="sk-area" d="M0 30 C 10 22, 18 26, 28 20 S 46 12, 56 17 S 76 8, 86 14 S 96 10, 100 8 L100 40 L0 40Z"/></svg>';
      return wrap.firstChild;
    })();
  return h("div", { class: "sk-chart", style: { height: `${height}px` } }, body);
}

export function skRank(rows = 6) {
  return h("div", { class: "rank" }, Array.from({ length: rows }, (_, i) =>
    h("div", { class: "rank-row" }, bone(SIZES[i % SIZES.length] + 40, 12), bone(46, 12), bone(28, 11), h("div", { class: "rank-bar" }, bone(`${90 - i * 9}%`, 2)))));
}

/** Table rows. cols: [{w, avatar?, num?}] */
export function skTable(rows = 8, cols = [{ w: 140, avatar: true }, { w: 120 }, { w: 90 }, { w: 80, num: true }]) {
  const head = h("tr", {}, cols.map((c) => h("th", { class: c.num ? "num" : "" }, bone(Math.max(40, c.w * 0.5), 10, c.num ? "end" : ""))));
  const body = Array.from({ length: rows }, (_, r) => h("tr", {}, cols.map((c, i) =>
    h("td", { class: c.num ? "num" : "" }, c.avatar
      ? h("div", { class: "cell-user" }, bone(28, 28, "round"), bone(c.w - 28 + ((r * 13) % 30), 12))
      : bone(c.w + ((r * 17 + i * 7) % 28), 12, c.num ? "end" : "")))));
  return busy(h("div", { class: "table-wrap" }, h("table", { class: "table" }, h("thead", {}, head), h("tbody", {}, body))));
}

export function skPager() {
  return h("div", { class: "pager" }, bone(90, 12), h("div", { class: "row" }, bone(84, 30), bone(30, 30), bone(80, 12), bone(30, 30)));
}

export function skFilters(n = 11) {
  return busy(h("section", { class: "card" },
    h("div", { class: "filters" }, Array.from({ length: n }, (_, i) =>
      h("div", { class: `field${i === 0 ? " wide" : ""}` }, bone(56, 11), bone("100%", 36)))),
    h("div", { class: "filter-footer" }, h("span"), bone(88, 28))));
}

export function skToolbar() {
  return h("div", { class: "toolbar" }, bone(340, 13), h("div", { class: "toolbar toolbar-end" }, bone(110, 36), bone(120, 36)));
}

// ---------- whole-page skeletons (arrays of nodes to `view.append(...)`) ----------

export function skOverview() {
  return [
    h("div", { class: "toolbar" }, bone(380, 13), h("span", { class: "toolbar-end" }, bone(96, 36))),
    skKpiStrip(5), skInsights(3),
    h("div", { class: "grid grid-main" }, skCard({ controls: true, body: skChart({ height: 340 }) }), skCard({ body: skRank(8) })),
    h("div", { class: "grid grid-half" }, skCard({ body: skRank(8) }), skCard({ body: skChart({ bars: true, height: 240 }) })),
    skCard({ flush: true, controls: true, body: skTable(8, [{ w: 130, avatar: true }, { w: 120 }, { w: 110 }, { w: 80 }, { w: 80 }, { w: 80, num: true }]) }),
  ];
}

export function skAnalytics() {
  return [
    h("div", { class: "grid grid-half" }, skCard({ body: skChart({ bars: true, height: 240 }) }), skCard({ body: skChart({ height: 240 }) })),
    skCard({ flush: true, body: skTable(5, [{ w: 130, avatar: true }, { w: 140, num: true }, { w: 160 }, { w: 90 }]) }),
    skCard({ body: skChart({ height: 120, bars: true }) }),
    skCard({ body: skChart({ height: 340, bars: true }) }),
    h("div", { class: "grid grid-half" }, skCard({ body: skRank(8) }), skCard({ body: skRank(8) })),
    h("div", { class: "grid grid-half" }, skCard({ body: skRank(3) }), skCard({ body: skRank(6) })),
  ];
}

export function skExpenses() {
  return [
    skToolbar(), skFilters(),
    skCard({ flush: true, sub: false, body: h("div", {}, skTable(10, [{ w: 50 }, { w: 90 }, { w: 130, avatar: true }, { w: 110 }, { w: 120 }, { w: 80 }, { w: 90 }, { w: 80, num: true }]), skPager()) }),
  ];
}

export function skProfile() {
  return [
    h("div", { class: "page-head" },
      h("div", { class: "row", style: { gap: "var(--space-5)" } }, bone(56, 56, "round"), h("div", { class: "stack", style: { gap: "10px" } }, bone(200, 24), bone(280, 12))),
      h("div", { class: "toolbar" }, bone(120, 36), bone(70, 36), bone(80, 36), bone(120, 36))),
    skKpiStrip(4),
    h("div", { class: "grid grid-main" }, skCard({ body: skChart({ height: 260 }) }), skCard({ body: skRank(3) })),
    h("div", { class: "grid grid-half" }, skCard({ body: skRank(6) }), skCard({ body: skRank(6) })),
    skCard({ flush: true, body: skTable(6, [{ w: 90 }, { w: 130 }, { w: 110 }, { w: 80 }, { w: 80, num: true }]) }),
  ];
}

export function skPresent() {
  return [h("div", { class: "stack", style: { gap: "20px", paddingTop: "40px" } }, bone(110, 12), bone(520, 44), bone(380, 20), h("div", { class: "row", style: { gap: "48px", marginTop: "24px" } }, bone(220, 80), bone(220, 80), bone(220, 80)))];
}
