// Command palette (Cmd/Ctrl+K): jump to pages, run actions, or find a user by name.

import { searchUsers } from "./api.js";
import { icon } from "./icons.js";
import { $, h } from "./ui.js";

const PAGES = [
  { label: "Overview", hint: "Go to", href: "#/overview", icon: "grid" },
  { label: "Expenses", hint: "Go to", href: "#/expenses", icon: "receipt" },
  { label: "Users", hint: "Go to", href: "#/users", icon: "users" },
  { label: "Analytics", hint: "Go to", href: "#/analytics", icon: "chart" },
  { label: "Present", hint: "Go to", href: "#/present", icon: "present" },
];

export function openPalette({ actions = [] } = {}) {
  if ($(".palette")) return;
  const input = h("input", { class: "palette-input", placeholder: "Search pages, actions, or users...", "aria-label": "Command palette" });
  const list = h("div", { class: "palette-list", role: "listbox" });
  const overlay = h("div", { class: "overlay palette-host" },
    h("div", { class: "palette", role: "dialog", "aria-modal": "true", "aria-label": "Command palette" }, input, list,
      h("div", { class: "palette-foot" }, h("span", {}, "↑↓ navigate"), h("span", {}, "↵ open"), h("span", {}, "esc close"))));
  let items = [];
  let index = 0;
  let timer;

  const close = () => { overlay.remove(); document.removeEventListener("keydown", onKey, true); };
  const run = (item) => { close(); if (item.href) location.hash = item.href; else item.run?.(); };
  const paint = () => {
    list.replaceChildren();
    let group = "";
    items.forEach((item, i) => {
      if (item.group !== group) { group = item.group; list.append(h("div", { class: "palette-group" }, group)); }
      list.append(h("button", { type: "button", class: "palette-item", role: "option", "aria-selected": String(i === index), onmousemove: () => { if (index !== i) { index = i; paint(); } }, onclick: () => run(item) },
        icon(item.icon || "search"), h("span", {}, item.label), item.hint ? h("span", { class: "hint" }, item.hint) : null));
    });
    if (!items.length) list.append(h("div", { class: "picker-empty" }, "No results"));
    list.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" });
  };
  const build = async () => {
    const q = input.value.trim().toLowerCase();
    const base = [...PAGES.map((p) => ({ ...p, group: "Pages" })), ...actions.map((a) => ({ ...a, group: "Actions", hint: a.hint || "Run" }))]
      .filter((i) => !q || i.label.toLowerCase().includes(q));
    items = base;
    index = 0;
    paint();
    if (q.length >= 1) {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        try {
          const users = await searchUsers(input.value.trim(), 6);
          if (input.value.trim().toLowerCase() !== q) return;
          items = [...base, ...users.map((u) => ({ group: "Users", label: u.name, hint: [u.city, u.country].filter(Boolean).join(", "), icon: "users", href: `#/users/${u.id}` }))];
          paint();
        } catch { /* ignore */ }
      }, 160);
    }
  };
  const onKey = (e) => {
    if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); index = Math.min(items.length - 1, index + 1); paint(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); index = Math.max(0, index - 1); paint(); }
    else if (e.key === "Enter" && items[index]) { e.preventDefault(); run(items[index]); }
  };
  overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(); });
  input.addEventListener("input", build);
  document.addEventListener("keydown", onKey, true);
  $("#overlay-root").append(overlay);
  input.focus();
  build();
}
