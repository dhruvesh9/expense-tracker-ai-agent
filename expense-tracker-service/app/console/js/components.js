// Reusable dashboard building blocks used by several pages.

import { sparkline } from "./charts.js";
import { addDays, iso, parseIso } from "./state.js";
import { change, pct } from "./format.js";
import { icon } from "./icons.js";
import { animateNumber, h } from "./ui.js";

/** Plain coloured text: arrow + percent. `goodWhenUp=false` for costs (spend rising is "bad"). */
export function deltaPill(value, { goodWhenUp = true, note = "vs previous period" } = {}) {
  if (value === null || value === undefined || !Number.isFinite(value)) return h("span", { class: "delta flat" }, "No baseline");
  if (Math.abs(value) < 0.05) return h("span", { class: "delta flat" }, "0.0%", h("span", { class: "delta-note" }, note));
  const up = value > 0;
  const good = up === goodWhenUp;
  return h("span", { class: `delta ${good ? "up" : "down"}`, title: note },
    icon(up ? "arrowUp" : "arrowDown"), Math.abs(value) > 999 ? "999%+" : pct(Math.abs(value)), h("span", { class: "delta-note" }, "vs prior"));
}

/** One KPI cell (put several inside a `.strip`). `spark` is an array of numbers (optional). */
export function kpiCard({ label, value, format, delta, goodWhenUp = true, spark, hint }) {
  const valueEl = h("div", { class: "kpi-value" }, format(0));
  const canvas = spark?.length > 1 ? h("canvas", { "aria-hidden": "true" }) : null;
  const cell = h("div", { class: "kpi" },
    h("div", { class: "kpi-label" }, label),
    valueEl,
    h("div", { class: "kpi-foot" },
      delta === undefined ? h("span", {}, hint || "") : deltaPill(delta, { goodWhenUp }),
      canvas ? h("div", { class: "spark-box" }, canvas) : null));
  animateNumber(valueEl, Number(value) || 0, format);
  if (canvas) requestAnimationFrame(() => canvas.isConnected && sparkline(canvas, spark));
  return cell;
}

export function chartCard({ title, sub, controls, body, flush = false }) {
  return h("section", { class: `card${flush ? " flush" : ""}` },
    h("div", { class: "card-header" },
      h("div", {}, h("h3", { class: "card-title" }, title), sub ? h("p", { class: "card-sub" }, sub) : null),
      controls || null),
    body);
}

export function segmented(options, value, onChange) {
  const wrap = h("div", { class: "segmented", role: "group" });
  const buttons = options.map((o) => h("button", { type: "button", "aria-pressed": String(o.id === value), onclick: () => {
    buttons.forEach((b, i) => b.setAttribute("aria-pressed", String(options[i].id === o.id)));
    onChange(o.id);
  } }, o.label));
  wrap.append(...buttons);
  return wrap;
}

/**
 * Ranked list with hairline bars: the quiet replacement for pie charts.
 * items: [{label, value, onClick?}]. Bars are relative to the largest value;
 * the percentage is the share of `total`.
 */
export function rankList(items, { format, total, compact = false, limit }) {
  const rows = limit ? items.slice(0, limit) : items;
  const sum = total ?? items.reduce((a, i) => a + Number(i.value), 0);
  const max = Math.max(1, ...rows.map((i) => Number(i.value)));
  const list = h("div", { class: `rank${compact ? " compact" : ""}` });
  rows.forEach((item) => {
    const tag = item.onClick ? "button" : "div";
    list.append(h(tag, { class: "rank-row", type: item.onClick ? "button" : undefined, onclick: item.onClick },
      h("span", { class: "rank-label", title: item.label }, item.label),
      h("span", { class: "rank-value" }, format(item.value)),
      h("span", { class: "rank-share" }, pct(sum ? (Number(item.value) / sum) * 100 : 0, 0)),
      h("div", { class: "rank-bar" }, h("span", { style: { width: `${(Number(item.value) / max) * 100}%` } }))));
  });
  return list;
}

/** One stacked bar showing parts of a whole, with a legend. parts: [{label, value, count, color}] */
export function partsBar(parts, { format }) {
  const total = parts.reduce((a, p) => a + p.value, 0) || 1;
  return h("div", {},
    h("div", { class: "parts-bar" }, parts.map((p) => h("span", { style: { width: `${(p.value / total) * 100}%`, "--part": p.color }, title: `${p.label}: ${format(p.value)}` }))),
    h("div", { class: "parts-legend" }, parts.map((p) => h("div", { class: "item" },
      h("span", { class: "swatch", style: { "--swatch": p.color } }), h("span", {}, p.label),
      h("span", { class: "muted" }, format(p.value)), h("span", { class: "subtle" }, pct((p.value / total) * 100, 0))))));
}

// ---------- series helpers ----------

/** Aggregate by-day report items (one currency) into dense arrays between min and max day. */
export function denseDaily(items, range) {
  const byDay = new Map(items.map((i) => [i.day, i]));
  const days = items.map((i) => i.day).sort();
  const start = range?.from || days[0];
  const end = range?.to || days[days.length - 1];
  if (!start || !end) return { days: [], totals: [], counts: [] };
  const out = { days: [], totals: [], counts: [] };
  for (let d = parseIso(start); d <= parseIso(end); d = addDays(d, 1)) {
    const key = iso(d);
    const item = byDay.get(key);
    out.days.push(key);
    out.totals.push(item ? Number(item.total) : 0);
    out.counts.push(item ? item.count : 0);
  }
  return out;
}

/** Sum consecutive values so a long series becomes at most `max` points. */
export function bucket(values, max = 30) {
  if (values.length <= max) return values;
  const size = Math.ceil(values.length / max);
  const out = [];
  for (let i = 0; i < values.length; i += size) out.push(values.slice(i, i + size).reduce((a, b) => a + b, 0));
  return out;
}

export { change };

/** A plain insight cell: one sentence and a muted detail line (put several in a `.strip`). */
export function insightCard(_iconName, headline, detail) {
  return h("div", { class: "insight" }, h("b", {}, headline), h("span", {}, detail));
}
