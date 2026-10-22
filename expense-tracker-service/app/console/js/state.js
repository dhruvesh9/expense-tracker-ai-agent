// Global console state (currency + date range), persisted in localStorage.

const KEY = "expense.console.v1";
const defaults = { currency: "INR", preset: "12m", from: "", to: "" };

function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; }
}

let state = { ...defaults, ...load() };
const subscribers = new Set();

export const getState = () => state;
export function setState(patch) {
  state = { ...state, ...patch };
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* private mode */ }
  subscribers.forEach((fn) => fn(state));
}
export function subscribe(fn) {
  subscribers.add(fn);
  return () => subscribers.delete(fn);
}

export const PRESETS = [
  { id: "30d", label: "Last 30 days" },
  { id: "90d", label: "Last 90 days" },
  { id: "12m", label: "Last 12 months" },
  { id: "ytd", label: "Year to date" },
  { id: "all", label: "All time" },
  { id: "custom", label: "Custom range" },
];

// ---- date helpers (local calendar days, formatted YYYY-MM-DD) ----
export const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
export const parseIso = (s) => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
export const addDays = (d, n) => { const c = new Date(d); c.setDate(c.getDate() + n); return c; };
export const todayIso = () => iso(new Date());

/** The active range as {from,to} ISO strings, or null for "all time". */
export function currentRange(s = state) {
  const today = new Date();
  switch (s.preset) {
    case "30d": return { from: iso(addDays(today, -29)), to: iso(today) };
    case "90d": return { from: iso(addDays(today, -89)), to: iso(today) };
    case "12m": return { from: iso(addDays(today, -364)), to: iso(today) };
    case "ytd": return { from: `${today.getFullYear()}-01-01`, to: iso(today) };
    case "custom": return s.from || s.to ? { from: s.from || "", to: s.to || "" } : null;
    default: return null;
  }
}

/** The equally long period immediately before the active range (for "vs previous"). */
export function previousRange(range = currentRange()) {
  if (!range || !range.from || !range.to) return null;
  const days = Math.round((parseIso(range.to) - parseIso(range.from)) / 86400000) + 1;
  const to = addDays(parseIso(range.from), -1);
  return { from: iso(addDays(to, -(days - 1))), to: iso(to) };
}

export const rangeParams = (range = currentRange()) => ({ date_from: range?.from || undefined, date_to: range?.to || undefined });

export function rangeLabel(range = currentRange()) {
  if (!range) return "All time";
  const fmt = (s) => parseIso(s).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  return `${range.from ? fmt(range.from) : "Beginning"} to ${range.to ? fmt(range.to) : "today"}`;
}
