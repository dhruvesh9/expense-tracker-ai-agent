// Tiny UI toolkit: an element builder (safe against XSS), toasts, modals, drawers.

import { searchUsers } from "./api.js";
import { initials } from "./format.js";
import { icon } from "./icons.js";

/**
 * h("div", {class: "card", onclick: fn}, "text", childElement, ...)
 * Strings become text nodes (never HTML), so data from the API can't inject markup.
 */
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "style" && typeof value === "object") Object.entries(value).forEach(([k, v]) => el.style.setProperty(k, v));
    else if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === "dataset") Object.assign(el.dataset, value);
    else if (value === true) el.setAttribute(key, "");
    else el.setAttribute(key, value);
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

export const clear = (el) => { el.replaceChildren(); return el; };
export const $ = (selector, root = document) => root.querySelector(selector);

// ---------- toasts ----------
export function toast(message, kind = "info") {
  const host = $("#toasts");
  const el = h("div", { class: `toast ${kind}`, role: "status" }, message);
  host.append(el);
  setTimeout(() => el.remove(), kind === "error" ? 6000 : 3200);
}

// ---------- tooltip (single shared element) ----------
export function showTooltip(event, text) {
  const tip = $("#tooltip");
  tip.textContent = text;
  tip.style.opacity = "1";
  const x = Math.min(event.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
  tip.style.left = `${x}px`;
  tip.style.top = `${event.clientY + 16}px`;
}
export const hideTooltip = () => { $("#tooltip").style.opacity = "0"; };

// ---------- modal / drawer ----------
function mountOverlay(content, { drawer = false } = {}) {
  const host = $("#overlay-root");
  const overlay = h("div", { class: `overlay${drawer ? " drawer-host" : ""}` }, content);
  const close = () => {
    overlay.remove();
    document.removeEventListener("keydown", onKey);
  };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(); });
  document.addEventListener("keydown", onKey);
  host.append(overlay);
  return close;
}

/** Generic modal. `body` is a node; `actions` is an array of buttons. Returns close(). */
export function modal({ title, body, actions = [] }) {
  let close;
  const dialog = h("div", { class: "modal", role: "dialog", "aria-modal": "true", "aria-label": title },
    h("div", { class: "modal-head" },
      h("h3", { class: "modal-title" }, title),
      h("button", { class: "btn ghost icon sm", "aria-label": "Close", onclick: () => close() }, icon("x"))),
    h("div", { class: "modal-body" }, body),
    actions.length ? h("div", { class: "modal-foot" }, actions) : null);
  close = mountOverlay(dialog);
  const first = dialog.querySelector("input, select, textarea");
  first?.focus();
  return close;
}

export function drawer({ title, body, actions = [] }) {
  let close;
  const panel = h("aside", { class: "drawer", role: "dialog", "aria-label": title },
    h("div", { class: "modal-head" },
      h("h3", { class: "modal-title" }, title),
      h("button", { class: "btn ghost icon sm", "aria-label": "Close", onclick: () => close() }, icon("x"))),
    h("div", { class: "drawer-body" }, body),
    actions.length ? h("div", { class: "modal-foot", style: { "border-radius": "0" } }, actions) : null);
  close = mountOverlay(panel, { drawer: true });
  return close;
}

/** Promise-based confirm dialog. Resolves true/false. */
export function confirmDialog({ title, message, confirmLabel = "Confirm", danger = false }) {
  return new Promise((resolve) => {
    let close;
    let settled = false;
    const done = (value) => { if (!settled) { settled = true; resolve(value); } close(); };
    close = modal({
      title,
      body: h("p", { class: "muted" }, message),
      actions: [
        h("button", { class: "btn", onclick: () => done(false) }, "Cancel"),
        h("button", { class: `btn ${danger ? "danger solid" : "primary"}`, onclick: () => done(true) }, confirmLabel),
      ],
    });
    // Closing via Esc/backdrop counts as cancel.
    const observer = new MutationObserver(() => {
      if (!document.body.contains($(".modal"))) { observer.disconnect(); done(false); }
    });
    observer.observe($("#overlay-root"), { childList: true });
  });
}

// ---------- small reusable pieces ----------
export const skeleton = (height = 120) => h("div", { class: "skeleton", style: { height: `${height}px` } });
export const emptyState = (title, hint) => h("div", { class: "empty" }, h("strong", {}, title), hint ? h("span", {}, hint) : null);
export const errorBox = (err) => h("div", { class: "error-box" }, `Could not load data: ${err.message}`);

export function field(label, control, error) {
  return h("label", { class: "field" }, h("span", { class: "label" }, label), control, error ? h("span", { class: "field-error" }, error) : null);
}

/** Neutral category label (colour is reserved for meaning, not decoration). */
export function categoryBadge(category) {
  return h("span", { class: "badge" }, category || "uncategorised");
}

export function avatar(name, large = false) {
  return h("span", { class: `avatar${large ? " lg" : ""}`, "aria-hidden": "true" }, initials(name || "?"));
}

/**
 * Typeahead for choosing one user without loading the whole user base: type a name, the
 * API returns a handful of matches. `onSelect(user | null)` fires on pick / clear.
 * Returns {el, input, get()} where get() is the selected user (or null).
 */
export function userPicker({ initial = null, placeholder = "Search users...", onSelect, invalid = false } = {}) {
  let selected = initial;
  let results = [];
  let index = -1;
  let timer;
  const input = h("input", { class: "input", type: "text", placeholder, autocomplete: "off", value: initial?.name || "", "aria-invalid": invalid ? "true" : null });
  const list = h("div", { class: "picker-list", role: "listbox", hidden: true });
  const el = h("div", { class: "picker" }, input, list);

  const close = () => { list.hidden = true; index = -1; };
  const choose = (user) => {
    selected = user;
    input.value = user ? user.name : "";
    close();
    onSelect?.(user);
  };
  const paint = () => {
    list.replaceChildren();
    if (!results.length) list.append(h("div", { class: "picker-empty" }, "No users found"));
    results.forEach((u, i) => list.append(h("button", { type: "button", class: "picker-item", role: "option", "aria-selected": String(i === index), onmousedown: (e) => { e.preventDefault(); choose(u); } },
      h("span", {}, u.name), h("span", { class: "subtle" }, [u.city, u.country].filter(Boolean).join(", ")))));
    list.hidden = false;
  };
  const run = async () => {
    list.replaceChildren(...[150, 120, 170].map((w) => h("div", { class: "picker-item" }, h("span", { class: "bone", style: { width: `${w}px`, height: "12px" } }))));
    list.hidden = false;
    try { results = await searchUsers(input.value.trim()); index = results.length ? 0 : -1; paint(); } catch { close(); }
  };
  input.addEventListener("input", () => {
    if (selected) { selected = null; onSelect?.(null); }
    clearTimeout(timer);
    timer = setTimeout(run, 180);
  });
  input.addEventListener("focus", () => { if (!selected) run(); });
  input.addEventListener("blur", () => setTimeout(close, 120));
  input.addEventListener("keydown", (e) => {
    if (list.hidden) return;
    if (e.key === "ArrowDown") { e.preventDefault(); index = Math.min(results.length - 1, index + 1); paint(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); index = Math.max(0, index - 1); paint(); }
    else if (e.key === "Enter" && results[index]) { e.preventDefault(); choose(results[index]); }
    else if (e.key === "Escape") { e.stopPropagation(); close(); }
  });
  return { el, input, get: () => selected, set: (user) => { selected = user; input.value = user?.name || ""; } };
}

export function animateNumber(el, to, format, duration = 900) {
  const start = performance.now();
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) { el.textContent = format(to); return; }
  const tick = (now) => {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = format(to * eased);
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

export function downloadText(filename, text, type = "text/csv") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = h("a", { href: url, download: filename });
  document.body.append(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
