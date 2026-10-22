// Entry point: app shell (nav, theme, global filters) and the hash router.

import { checkReady, reports } from "./api.js";
import { destroyCharts } from "./charts.js";
import { icon } from "./icons.js";
import { openPalette } from "./palette.js";
import { openExpenseForm } from "./expense-ui.js";
import { openUserForm } from "./user-ui.js";
import { PRESETS, addDays, getState, iso, rangeLabel, setState, todayIso } from "./state.js";
import { shared } from "./shared.js";
import { $, clear, errorBox, h, toast } from "./ui.js";

import overview from "./pages/overview.js";
import expenses from "./pages/expenses.js";
import users from "./pages/users.js";
import userDetail from "./pages/user-detail.js";
import analytics from "./pages/analytics.js";
import present from "./pages/present.js";

const routes = [
  { name: "overview", test: /^\/overview$/, page: overview },
  { name: "expenses", test: /^\/expenses$/, page: expenses },
  { name: "users", test: /^\/users$/, page: users },
  { name: "users", test: /^\/users\/(\d+)$/, page: userDetail },
  { name: "analytics", test: /^\/analytics$/, page: analytics },
  { name: "present", test: /^\/present$/, page: present },
];

let renderToken = 0;
let cleanup = null;

function parseHash() {
  const raw = location.hash.replace(/^#/, "") || "/overview";
  const [path, query = ""] = raw.split("?");
  return { path, params: Object.fromEntries(new URLSearchParams(query)) };
}

async function render() {
  const token = ++renderToken;
  const isCurrent = () => token === renderToken;
  const { path, params } = parseHash();

  if (cleanup) { try { cleanup(); } catch { /* ignore */ } cleanup = null; }
  destroyCharts();

  let match = null;
  for (const route of routes) {
    const m = route.test.exec(path);
    if (m) { match = { route, args: m.slice(1) }; break; }
  }
  if (!match) { location.hash = "#/overview"; return; }

  const { route, args } = match;
  document.querySelectorAll(".nav a[data-route]").forEach((a) => {
    if (a.dataset.route === route.name) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  $("#sidebar").classList.remove("open");

  const ctx = { isCurrent, refresh: render, args };
  const meta = route.page.meta ? route.page.meta(params, ctx) : { title: route.name };
  $("#page-title").textContent = meta.title;
  $("#page-sub").textContent = meta.sub || "";
  document.title = `${meta.title} - Expense Tracker Console`;
  renderControls(meta.global);

  const view = $("#view");
  clear(view);
  view.classList.remove("view-enter");
  void view.offsetWidth; // restart the enter animation
  view.classList.add("view-enter");

  try {
    const result = await route.page.render(view, params, ctx);
    if (isCurrent() && typeof result === "function") cleanup = result;
    else if (typeof result === "function") result();
  } catch (err) {
    if (!isCurrent()) return;
    console.error(err);
    clear(view).append(errorBox(err));
  }
  if (isCurrent()) window.scrollTo({ top: 0 });
}

// ---------- global filters in the top bar ----------
function renderControls(show) {
  const host = clear($("#topbar-controls"));
  if (!show) return;
  const s = getState();

  const currency = h("select", { class: "select", "aria-label": "Currency", onchange: (e) => { setState({ currency: e.target.value }); render(); } },
    shared.currencies.map((c) => h("option", { value: c, selected: c === s.currency }, c)));

  const preset = h("select", { class: "select", "aria-label": "Date range", onchange: (e) => { setState({ preset: e.target.value }); render(); } },
    PRESETS.map((p) => h("option", { value: p.id, selected: p.id === s.preset }, p.label)));

  host.append(currency, preset);

  if (s.preset === "custom") {
    host.append(
      h("input", { class: "input", type: "date", value: s.from, max: todayIso(), "aria-label": "From date", onchange: (e) => { setState({ from: e.target.value }); render(); } }),
      h("input", { class: "input", type: "date", value: s.to, max: todayIso(), "aria-label": "To date", onchange: (e) => { setState({ to: e.target.value }); render(); } }),
    );
  }
  host.append(h("button", { class: "btn icon", "aria-label": "Refresh", title: "Refresh data", onclick: () => { render(); toast("Data refreshed", "success"); } }, icon("refresh")));
}

// ---------- theme ----------
function currentTheme() {
  return document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}
function paintThemeButton() {
  const btn = clear($("#theme-btn"));
  btn.append(icon(currentTheme() === "dark" ? "sun" : "moon"));
}
function initTheme() {
  try {
    const saved = localStorage.getItem("expense.theme");
    if (saved) document.documentElement.dataset.theme = saved;
  } catch { /* ignore */ }
  paintThemeButton();
  $("#theme-btn").addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("expense.theme", next); } catch { /* ignore */ }
    paintThemeButton();
    render(); // charts read colours at creation time, so redraw
  });
}

// ---------- API health ----------
async function pollHealth() {
  const ok = await checkReady();
  $("#api-dot").className = `dot ${ok ? "ok" : "bad"}`;
  $("#api-status").textContent = ok ? "API operational" : "API unreachable";
}

async function boot() {
  document.querySelectorAll("[data-icon]").forEach((el) => el.replaceWith(icon(el.dataset.icon)));
  $("#menu-btn").append(icon("menu"));
  $("#menu-btn").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
  initTheme();
  $("#search-icon").replaceWith(icon("search"));
  const isMac = /Mac|iPhone|iPad/.test(navigator.platform);
  $("#search-kbd").textContent = isMac ? "⌘K" : "Ctrl K";
  const openSearch = () => openPalette({ actions: [
    { label: "New expense", icon: "plus", run: () => openExpenseForm({ onSaved: render }) },
    { label: "New user", icon: "plus", run: () => openUserForm({ onSaved: render }) },
    { label: "Toggle light / dark theme", icon: "moon", run: () => $("#theme-btn").click() },
  ] });
  $("#search-btn").addEventListener("click", openSearch);
  document.addEventListener("keydown", (e) => {
    const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName || "");
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openSearch(); }
    else if (e.key === "/" && !typing && !document.querySelector(".overlay")) { e.preventDefault(); openSearch(); }
  });
  pollHealth();
  setInterval(pollHealth, 30000);

  try {
    // Currencies present in the data (most-used first) feed every currency selector.
    // A recent window keeps this instant even with millions of rows.
    const recent = iso(addDays(new Date(), -45));
    const summary = await reports.summary({ date_from: recent });
    shared.currencies = summary.by_currency.sort((a, b) => b.count - a.count).map((c) => c.currency);
    if (!shared.currencies.length) shared.currencies = ["INR"];
    if (!shared.currencies.includes(getState().currency)) setState({ currency: shared.currencies[0] });
  } catch (err) {
    toast(`Cannot reach the API: ${err.message}`, "error");
  }

  window.addEventListener("hashchange", render);
  render();
}

boot();
