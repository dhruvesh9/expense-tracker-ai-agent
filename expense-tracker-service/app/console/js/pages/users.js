// Users directory: search, filter, sort, budget progress, per-user spend, create / edit / delete.
// Built for a large user base: it only ever fetches stats for the users on the visible page.

import { get, reports } from "../api.js";
import { segmented } from "../components.js";
import { COUNTRY_CODES, countryName, dateShort, money, num } from "../format.js";
import { icon } from "../icons.js";
import { deleteUserFlow, openUserForm } from "../user-ui.js";
import { avatar, clear, emptyState, errorBox, h } from "../ui.js";
import { skPager, skTable } from "../skeletons.js";

const SORTS = [
  { id: "name", label: "Name" },
  { id: "-created_at", label: "Newest" },
  { id: "created_at", label: "Oldest" },
  { id: "id", label: "ID" },
];
const STATUS = { ok: "", near: "warning", over: "negative" };
const thisMonth = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`; };

export default {
  meta: () => ({ title: "Users", sub: "Everyone using the app", global: false }),

  async render(view, _params, ctx) {
    const st = { name: "", has_expenses: "", has_budget: "", country: "", sort: "name", page: 1, page_size: 20 };
    const countries = COUNTRY_CODES.slice().sort((a, b) => countryName(a).localeCompare(countryName(b)));
    const results = h("div");
    let timer;

    const search = h("input", { class: "input", type: "search", placeholder: "Search by name...", oninput: (e) => { st.name = e.target.value; clearTimeout(timer); timer = setTimeout(() => { st.page = 1; load(); }, 300); } });

    async function load() {
      clear(results).append(skTable(Math.min(st.page_size, 10), [{ w: 130, avatar: true }, { w: 110 }, { w: 90, num: true }, { w: 130 }, { w: 60, num: true }, { w: 90, num: true }, { w: 80 }, { w: 40 }]), skPager());
      try {
        const page = await get("/users", { name: st.name, has_expenses: st.has_expenses, has_budget: st.has_budget, country: st.country, sort: st.sort, page: st.page, page_size: st.page_size });
        const ids = page.items.map((u) => u.id);
        // Stats only for the visible rows (a few queries over a handful of users).
        const [stats, budgets] = ids.length
          ? await Promise.all([reports.byUser({ user_id: ids }), reports.budgets({ id: ids, month: thisMonth(), limit: 100 })])
          : [{ items: [] }, { items: [] }];
        if (!ctx.isCurrent()) return;
        paint(page, stats.items, new Map(budgets.items.map((b) => [b.user_id, b])));
      } catch (err) {
        if (ctx.isCurrent()) clear(results).append(errorBox(err));
      }
    }

    function paint(page, statRows, budgetByUser) {
      const perUser = new Map();
      for (const r of statRows) {
        const s = perUser.get(r.user_id) || { count: 0, byCurrency: new Map() };
        s.count += r.count;
        s.byCurrency.set(r.currency, Number(r.total));
        perUser.set(r.user_id, s);
      }

      const rows = page.items.map((u) => {
        const s = perUser.get(u.id) || { count: 0, byCurrency: new Map() };
        const own = s.byCurrency.get(u.default_currency) || 0;
        const others = s.byCurrency.size - (s.byCurrency.has(u.default_currency) ? 1 : 0);
        const b = budgetByUser.get(u.id);
        return h("tr", { class: "clickable", onclick: () => { location.hash = `#/users/${u.id}`; } },
          h("td", {}, h("div", { class: "cell-user" }, avatar(u.name), h("div", {}, h("strong", {}, u.name), h("div", { class: "subtle", style: { "font-size": "var(--text-xs)" } }, `#${u.id}`)))),
          h("td", {}, u.city || u.country ? h("span", { title: countryName(u.country) }, [u.city, countryName(u.country)].filter(Boolean).join(", ")) : h("span", { class: "subtle" }, "-")),
          h("td", { class: "num" }, u.monthly_budget ? money(u.monthly_budget, u.default_currency) : h("span", { class: "subtle" }, "No budget")),
          h("td", { style: { "min-width": "150px" } }, b
            ? h("div", { class: "row", title: `${money(b.spent, b.currency)} of ${money(b.budget, b.currency)} this month` },
              h("div", { class: "share-bar", style: { flex: 1 } }, h("span", { style: { width: `${Math.min(100, b.percent_used)}%`, "--bar": b.status === "over" ? "var(--color-negative)" : b.status === "near" ? "var(--color-warning)" : "var(--color-primary)" } })),
              h("span", { class: `muted ${STATUS[b.status]}` }, `${Math.round(b.percent_used)}%`))
            : h("span", { class: "subtle" }, "-")),
          h("td", { class: "num" }, num(s.count)),
          h("td", { class: "num" }, own ? money(own, u.default_currency) : h("span", { class: "subtle" }, "-"),
            others ? h("span", { class: "pill", style: { "margin-left": "8px" }, title: "Also spends in other currencies" }, `+${others}`) : null),
          h("td", { class: "muted" }, dateShort(u.created_at)),
          h("td", {}, h("div", { class: "row", style: { "justify-content": "flex-end", gap: "2px" } },
            h("button", { class: "btn ghost icon sm", title: "Edit", "aria-label": `Edit ${u.name}`, onclick: (e) => { e.stopPropagation(); openUserForm({ user: u, onSaved: load }); } }, icon("edit")),
            h("button", { class: "btn ghost icon sm", title: "Delete", "aria-label": `Delete ${u.name}`, onclick: (e) => { e.stopPropagation(); deleteUserFlow(u, load); } }, icon("trash")))));
      });

      const from = page.total ? (page.page - 1) * page.page_size + 1 : 0;
      const to = Math.min(page.total, page.page * page.page_size);
      const go = (n) => { st.page = n; load(); };
      clear(results).append(
        page.items.length
          ? h("div", { class: "table-wrap" }, h("table", { class: "table" },
              h("thead", {}, h("tr", {}, [["User", ""], ["Location", ""], ["Monthly budget", "num"], ["Budget used this month", ""], ["Expenses", "num"], ["Total spend", "num"], ["Joined", ""], ["", ""]].map(([t, c]) => h("th", { class: c }, t)))),
              h("tbody", {}, rows)))
          : emptyState("No users found", "Try a different search or add someone new."),
        h("div", { class: "pager" },
          h("span", {}, page.total ? `${num(from)}-${num(to)} of ${num(page.total)}` : "0 results"),
          h("div", { class: "row" },
            h("select", { class: "select", "aria-label": "Rows per page", onchange: (e) => { st.page_size = Number(e.target.value); st.page = 1; load(); } },
              [20, 50, 100].map((n) => h("option", { value: n, selected: n === st.page_size }, `${n} / page`))),
            h("button", { class: "btn sm icon", "aria-label": "Previous page", disabled: page.page <= 1, onclick: () => go(page.page - 1) }, icon("left")),
            h("span", {}, `Page ${num(page.page)} of ${num(Math.max(1, page.pages))}`),
            h("button", { class: "btn sm icon", "aria-label": "Next page", disabled: page.page >= page.pages, onclick: () => go(page.page + 1) }, icon("right")))));
    }

    view.append(
      h("div", { class: "toolbar" },
        h("p", { class: "muted" }, "Each person's spend is shown in their own default currency. Click a row for the full profile."),
        h("button", { class: "btn primary toolbar-end", onclick: () => openUserForm({ onSaved: load }) }, icon("plus"), "New user")),
      h("div", { class: "toolbar" },
        h("div", { class: "input-icon", style: { width: "260px" } }, icon("search"), search),
        segmented([{ id: "", label: "All users" }, { id: "true", label: "With expenses" }, { id: "false", label: "No expenses" }], "", (v) => { st.has_expenses = v; st.page = 1; load(); }),
        h("select", { class: "select", "aria-label": "Country", onchange: (e) => { st.country = e.target.value; st.page = 1; load(); } },
          h("option", { value: "" }, "All countries"), countries.map((c) => h("option", { value: c }, countryName(c)))),
        h("select", { class: "select", "aria-label": "Budget", onchange: (e) => { st.has_budget = e.target.value; st.page = 1; load(); } },
          h("option", { value: "" }, "Any budget"), h("option", { value: "true" }, "Has budget"), h("option", { value: "false" }, "No budget")),
        h("select", { class: "select", "aria-label": "Sort", onchange: (e) => { st.sort = e.target.value; st.page = 1; load(); } },
          SORTS.map((s) => h("option", { value: s.id }, `Sort: ${s.label}`)))),
      h("section", { class: "card flush" }, results));
    await load();
  },
};
