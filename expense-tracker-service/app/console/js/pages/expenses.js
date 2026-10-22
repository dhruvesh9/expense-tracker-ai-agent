// Expense explorer: filter, sort, paginate, inspect, create, edit, delete, export CSV.

import { get, getAll, getCategories, lookupUsers } from "../api.js";
import { openExpenseDrawer, openExpenseForm } from "../expense-ui.js";
import { PAYMENT_METHODS, dateShort, money, num, paymentLabel, titleCase } from "../format.js";
import { icon } from "../icons.js";
import { shared } from "../shared.js";
import { avatar, categoryBadge, clear, downloadText, emptyState, errorBox, h, toast, userPicker } from "../ui.js";
import { skExpenses, skPager, skTable } from "../skeletons.js";

const FILTER_KEYS = ["q", "merchant", "user_id", "category", "currency", "payment_method", "is_recurring", "date_from", "date_to", "min_amount", "max_amount"];
const COLUMNS = [
  { label: "ID", sort: "id" },
  { label: "Date", sort: "expense_date" },
  { label: "User" },
  { label: "Description" },
  { label: "Merchant" },
  { label: "Category" },
  { label: "Paid with" },
  { label: "Amount", sort: "amount", cls: "num" },
];

export default {
  meta: () => ({ title: "Expenses", sub: "Search, filter and manage every record" }),

  async render(view, params, ctx) {
    const st = { q: "", merchant: "", user_id: "", category: "", currency: "", payment_method: "", is_recurring: "", date_from: "", date_to: "", min_amount: "", max_amount: "", sort: "-expense_date", page: 1, page_size: 20 };
    for (const key of FILTER_KEYS) if (params[key]) st[key] = params[key];

    view.append(...skExpenses()); // shown immediately; replaced once filters data is ready
    const categories = await getCategories();
    const initialUser = st.user_id ? (await lookupUsers([Number(st.user_id)])).get(Number(st.user_id)) : null;
    if (!ctx.isCurrent()) return;

    const results = h("div");
    const chipsHost = h("div", { class: "chips" });
    const inputs = {};
    const userLabel = { current: initialUser?.name };

    const control = (key, label, el, cls = "") => {
      inputs[key] = el;
      return h("div", { class: `field ${cls}` }, h("span", { class: "label" }, label), el);
    };
    const onChange = () => { st.page = 1; load(); };
    let timer;
    const debounced = () => { clearTimeout(timer); timer = setTimeout(onChange, 300); };
    const search = h("input", { class: "input", type: "search", placeholder: "Search descriptions...", value: st.q, oninput: (e) => { st.q = e.target.value; debounced(); } });
    const bind = (key) => (e) => { st[key] = e.target.value; onChange(); };
    const picker = userPicker({ initial: initialUser, placeholder: "Anyone", onSelect: (u) => { st.user_id = u ? String(u.id) : ""; userLabel.current = u?.name; onChange(); } });

    const filters = h("div", { class: "filters" },
      control("q", "Search", h("div", { class: "input-icon" }, icon("search"), search), "wide"),
      control("merchant", "Merchant", h("input", { class: "input", placeholder: "e.g. Uber", value: st.merchant, oninput: (e) => { st.merchant = e.target.value; debounced(); } })),
      control("user_id", "User", picker.el),
      control("category", "Category", h("select", { class: "select", onchange: bind("category") }, h("option", { value: "" }, "All categories"), categories.map((c) => h("option", { value: c.category, selected: c.category === st.category }, `${titleCase(c.category)} (${num(c.count)})`)))),
      control("currency", "Currency", h("select", { class: "select", onchange: bind("currency") }, h("option", { value: "" }, "All"), shared.currencies.map((c) => h("option", { value: c, selected: c === st.currency }, c)))),
      control("payment_method", "Paid with", h("select", { class: "select", onchange: bind("payment_method") }, h("option", { value: "" }, "Any method"), PAYMENT_METHODS.map((m) => h("option", { value: m.id, selected: m.id === st.payment_method }, m.label)))),
      control("is_recurring", "Type", h("select", { class: "select", onchange: bind("is_recurring") }, h("option", { value: "" }, "All"), h("option", { value: "true", selected: st.is_recurring === "true" }, "Recurring only"), h("option", { value: "false", selected: st.is_recurring === "false" }, "One-off only"))),
      control("date_from", "From", h("input", { class: "input", type: "date", value: st.date_from, onchange: bind("date_from") })),
      control("date_to", "To", h("input", { class: "input", type: "date", value: st.date_to, onchange: bind("date_to") })),
      control("min_amount", "Min amount", h("input", { class: "input", inputmode: "decimal", placeholder: "0", value: st.min_amount, onchange: bind("min_amount") })),
      control("max_amount", "Max amount", h("input", { class: "input", inputmode: "decimal", placeholder: "Any", value: st.max_amount, onchange: bind("max_amount") })));

    function clearKey(key) {
      st[key] = "";
      if (key === "q") search.value = "";
      else if (key === "user_id") picker.set(null);
      else if (inputs[key]?.tagName === "SELECT" || inputs[key]?.tagName === "INPUT") inputs[key].value = "";
    }
    const reset = () => { FILTER_KEYS.forEach(clearKey); onChange(); };

    function chips() {
      clear(chipsHost);
      const label = {
        q: (v) => `Search: ${v}`,
        merchant: (v) => `Merchant: ${v}`,
        payment_method: (v) => `Paid with: ${paymentLabel(v)}`,
        is_recurring: (v) => (v === "true" ? "Recurring only" : "One-off only"),
        user_id: () => `User: ${userLabel.current || "selected"}`,
        category: (v) => `Category: ${v}`,
        currency: (v) => `Currency: ${v}`,
        date_from: (v) => `From ${dateShort(v)}`,
        date_to: (v) => `To ${dateShort(v)}`,
        min_amount: (v) => `Min ${v}`,
        max_amount: (v) => `Max ${v}`,
      };
      for (const key of FILTER_KEYS) {
        if (!st[key]) continue;
        chipsHost.append(h("span", { class: "chip" }, label[key](st[key]),
          h("button", { "aria-label": `Remove ${key} filter`, onclick: () => { clearKey(key); onChange(); } }, "×")));
      }
    }

    const apiParams = () => ({ ...Object.fromEntries(FILTER_KEYS.map((k) => [k, st[k]])), sort: st.sort, page: st.page, page_size: st.page_size });

    async function load() {
      chips();
      clear(results).append(skTable(Math.min(st.page_size, 12), [{ w: 50 }, { w: 90 }, { w: 130, avatar: true }, { w: 110 }, { w: 120 }, { w: 80 }, { w: 90 }, { w: 80, num: true }]), skPager());
      try {
        const data = await get("/expenses", apiParams());
        const userMap = await lookupUsers(data.items.map((e) => e.user_id));
        if (!ctx.isCurrent()) return;
        paint(data, userMap);
      } catch (err) {
        if (ctx.isCurrent()) clear(results).append(errorBox(err));
      }
    }

    function sortHeader(col) {
      if (!col.sort) return h("th", { class: col.cls || "" }, col.label);
      const active = st.sort.replace("-", "") === col.sort;
      const desc = st.sort.startsWith("-");
      return h("th", { class: `sortable ${col.cls || ""}`, "aria-sort": active ? (desc ? "descending" : "ascending") : null, onclick: () => {
        st.sort = active && desc ? col.sort : `-${col.sort}`;
        st.page = 1;
        load();
      } }, col.label, h("span", { class: "arrow" }, active ? (desc ? "↓" : "↑") : "↕"));
    }

    function paint(data, userMap) {
      const rows = data.items.map((e) => {
        const owner = userMap.get(e.user_id);
        return h("tr", { class: "clickable", onclick: () => openExpenseDrawer(e, { userMap, onChange: load }) },
          h("td", { class: "muted" }, `#${e.id}`),
          h("td", {}, dateShort(e.expense_date)),
          h("td", {}, h("div", { class: "cell-user" }, avatar(owner?.name), owner?.name || `User #${e.user_id}`)),
          h("td", { class: "cell-clip" }, e.description || h("span", { class: "subtle" }, "-")),
          h("td", { class: "cell-clip" }, e.merchant || h("span", { class: "subtle" }, "-"), e.is_recurring ? h("span", { class: "pill", style: { "margin-left": "8px" }, title: "Recurring" }, "↻") : null),
          h("td", {}, categoryBadge(e.category)),
          h("td", { class: "muted" }, paymentLabel(e.payment_method)),
          h("td", { class: "num" }, money(e.amount, e.currency)));
      });
      const from = data.total ? (data.page - 1) * data.page_size + 1 : 0;
      const to = Math.min(data.total, data.page * data.page_size);
      const go = (page) => { st.page = page; load(); };
      clear(results).append(
        h("div", { class: "table-wrap" }, data.items.length
          ? h("table", { class: "table" }, h("thead", {}, h("tr", {}, COLUMNS.map(sortHeader))), h("tbody", {}, rows))
          : emptyState("No expenses match these filters", "Try removing a filter or widening the date range.")),
        h("div", { class: "pager" },
          h("span", {}, data.total ? `${num(from)}-${num(to)} of ${num(data.total)}` : "0 results"),
          h("div", { class: "row" },
            h("select", { class: "select", "aria-label": "Rows per page", onchange: (e) => { st.page_size = Number(e.target.value); st.page = 1; load(); } },
              [10, 20, 50, 100].map((n) => h("option", { value: n, selected: n === st.page_size }, `${n} / page`))),
            h("button", { class: "btn sm icon", "aria-label": "Previous page", disabled: data.page <= 1, onclick: () => go(data.page - 1) }, icon("left")),
            h("span", {}, `Page ${num(data.page)} of ${num(Math.max(1, data.pages))}`),
            h("button", { class: "btn sm icon", "aria-label": "Next page", disabled: data.page >= data.pages, onclick: () => go(data.page + 1) }, icon("right")))));
    }

    async function exportCsv() {
      toast("Preparing export...");
      try {
        const { page: _p, page_size: _s, ...rest } = apiParams();
        const items = await getAll("/expenses", rest, 5000);
        const userMap = await lookupUsers(items.map((e) => e.user_id));
        const esc = (v) => {
          let s = v === null || v === undefined ? "" : String(v);
          if (/^[=+\-@]/.test(s)) s = `'${s}`; // neutralise spreadsheet formula injection
          return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
        };
        const header = ["id", "user_id", "user", "expense_date", "amount", "currency", "category", "merchant", "payment_method", "is_recurring", "description", "created_at"];
        const lines = items.map((e) => [e.id, e.user_id, userMap.get(e.user_id)?.name, e.expense_date, e.amount, e.currency, e.category, e.merchant, e.payment_method, e.is_recurring, e.description, e.created_at].map(esc).join(","));
        downloadText(`expenses-${new Date().toISOString().slice(0, 10)}.csv`, [header.join(","), ...lines].join("\n"));
        toast(`Exported ${num(items.length)} expenses${items.length >= 5000 ? " (limit 5,000)" : ""}`, "success");
      } catch (err) { toast(err.message, "error"); }
    }

    clear(view).append(
      h("div", { class: "toolbar" },
        h("p", { class: "muted" }, "Every filter combines with the others. Click a row for details."),
        h("div", { class: "toolbar toolbar-end" },
          h("button", { class: "btn", onclick: exportCsv }, icon("download"), "Export CSV"),
          h("button", { class: "btn primary", onclick: () => openExpenseForm({ onSaved: load }) }, icon("plus"), "New expense"))),
      h("section", { class: "card" }, filters, h("div", { class: "filter-footer" }, chipsHost, h("button", { class: "btn ghost sm", onclick: reset }, "Reset filters"))),
      h("section", { class: "card flush" }, results));
    await load();
  },
};
