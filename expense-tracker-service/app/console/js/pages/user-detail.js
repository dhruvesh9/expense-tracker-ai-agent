// Single user profile: budget health, KPIs, trend, categories, merchants, payment methods, recent expenses.

import { get, lookupUsers, reports } from "../api.js";
import { areaChart, destroyCharts } from "../charts.js";
import { chartCard, kpiCard, rankList } from "../components.js";
import { openExpenseDrawer, openExpenseForm } from "../expense-ui.js";
import { countryName, dateShort, money, monthLabel, num, paymentLabel, pct, titleCase } from "../format.js";
import { icon } from "../icons.js";
import { currentRange, getState, rangeLabel, rangeParams } from "../state.js";
import { deleteUserFlow, openUserForm } from "../user-ui.js";
import { avatar, categoryBadge, clear, emptyState, h } from "../ui.js";
import { skProfile } from "../skeletons.js";

const thisMonth = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`; };
const STATUS_TEXT = { ok: "On track", near: "Close to the limit", over: "Over budget" };
const STATUS_COLOR = { ok: "var(--color-primary)", near: "var(--color-warning)", over: "var(--color-negative)" };

function budgetCard(user, status, onEdit) {
  if (!user.monthly_budget) {
    return chartCard({ title: "Monthly budget", sub: "Not set", body: h("div", { class: "empty" }, h("strong", {}, "No budget yet"),
      h("span", {}, "Set a monthly budget to track progress."), h("button", { class: "btn sm", onclick: onEdit }, "Set a budget")) });
  }
  const used = status?.percent_used ?? 0;
  const bad = status?.status === "over" ? "negative" : status?.status === "near" ? "warning" : "";
  return chartCard({
    title: "Monthly budget",
    sub: `${monthLabel(thisMonth(), true)} · in ${user.default_currency}`,
    body: h("div", { class: "stack" },
      h("div", { class: "row spread" }, h("div", { class: "kpi-value" }, pct(used, 0)), h("span", { class: `badge ${bad || "positive"}` }, STATUS_TEXT[status?.status] || "On track")),
      h("div", { class: "share-bar", style: { height: "6px" }, role: "progressbar", "aria-valuenow": Math.min(100, Math.round(used)), "aria-valuemin": 0, "aria-valuemax": 100 },
        h("span", { style: { width: `${Math.min(100, used)}%`, "--bar": STATUS_COLOR[status?.status || "ok"] } })),
      h("div", { class: "row spread muted" },
        h("span", {}, `Spent ${money(status?.spent ?? 0, user.default_currency)}`),
        h("span", {}, `Budget ${money(user.monthly_budget, user.default_currency)}`)),
      h("div", {}, status && Number(status.remaining) < 0
        ? h("span", { class: "negative", style: { color: "var(--color-negative)" } }, `${money(Math.abs(status.remaining), user.default_currency)} over`)
        : h("span", { class: "muted" }, `${money(status?.remaining ?? user.monthly_budget, user.default_currency)} left this month`))),
  });
}

export default {
  meta: () => ({ title: "User profile", sub: rangeLabel(), global: true }),

  async render(view, _params, ctx) {
    const id = Number(ctx.args[0]);
    const { currency } = getState();
    const range = currentRange();
    const base = { ...rangeParams(range), currency, user_id: id };
    const fmt = (v) => money(v, currency);
    const fmtCompact = (v) => money(v, currency, { compact: true });

    view.append(...skProfile());

    let user;
    try {
      user = await get(`/users/${id}`);
    } catch (err) {
      if (!ctx.isCurrent()) return;
      clear(view).append(emptyState("User not found", err.message), h("a", { class: "btn", href: "#/users" }, "Back to users"));
      return;
    }
    const [summary, byMonth, byCategory, byMerchant, byPayment, budgets, recent] = await Promise.all([
      reports.summary(base),
      reports.byMonth(base),
      reports.byCategory(base),
      reports.byMerchant(base),
      reports.byPaymentMethod(base),
      reports.budgets({ id, month: thisMonth() }),
      get("/expenses", { ...base, sort: "-expense_date", page_size: 10 }),
    ]);
    if (!ctx.isCurrent()) return;
    const userMap = await lookupUsers([id]);
    clear(view);
    destroyCharts();
    document.getElementById("page-title").textContent = user.name;
    const refreshAll = () => ctx.refresh();

    view.append(h("div", { class: "page-head" },
      h("div", { class: "row", style: { gap: "var(--space-5)" } },
        avatar(user.name, true),
        h("div", {}, h("h2", {}, user.name),
          h("p", {}, [[user.city, user.country ? countryName(user.country) : null].filter(Boolean).join(", ") || "Location not set", `Spends in ${user.default_currency}`, `Joined ${dateShort(user.created_at)}`].join(" · ")))),
      h("div", { class: "toolbar" },
        h("a", { class: "btn", href: `#/expenses?user_id=${user.id}` }, icon("receipt"), "All expenses"),
        h("button", { class: "btn", onclick: () => openUserForm({ user, onSaved: refreshAll }) }, icon("edit"), "Edit"),
        h("button", { class: "btn danger", onclick: () => deleteUserFlow(user, () => { location.hash = "#/users"; }) }, icon("trash"), "Delete"),
        h("button", { class: "btn primary", onclick: () => openExpenseForm({ defaults: { user_id: user.id, currency: user.default_currency }, onSaved: refreshAll }) }, icon("plus"), "Add expense"))));

    const cur = summary.by_currency[0];
    if (!cur) {
      view.append(budgetCard(user, budgets.items[0], () => openUserForm({ user, onSaved: refreshAll })), emptyState(`No ${currency} expenses in this period`, "Change the currency or date range, or add an expense."));
      return;
    }
    view.append(h("div", { class: "strip" },
      kpiCard({ label: "Total spend", value: cur.total, format: fmtCompact, hint: rangeLabel(range) }),
      kpiCard({ label: "Expenses", value: cur.count, format: (v) => num(Math.round(v)), hint: "Recorded in period" }),
      kpiCard({ label: "Average expense", value: cur.average, format: fmt, hint: "Per expense" }),
      kpiCard({ label: "Largest expense", value: cur.maximum, format: fmtCompact, hint: `Smallest ${fmt(cur.minimum)}` })));

    const monthCanvas = h("canvas");
    const cats = [...byCategory.items].sort((a, b) => b.total - a.total);
    const catTotal = cats.reduce((a, c) => a + Number(c.total), 0);
    view.append(h("div", { class: "grid grid-main" },
      chartCard({ title: "Spending over time", sub: "Monthly totals", body: h("div", { class: "chart-box" }, monthCanvas) }),
      budgetCard(user, budgets.items[0], () => openUserForm({ user, onSaved: refreshAll }))));
    areaChart(monthCanvas, { labels: byMonth.items.map((m) => monthLabel(m.month)), series: [{ label: "Spend", data: byMonth.items.map((m) => Number(m.total)), color: "var(--chart-accent)" }], format: fmtCompact });

    const merchants = byMerchant.items.filter((m) => m.merchant);
    const pays = [...byPayment.items].sort((a, b) => b.total - a.total);
    view.append(h("div", { class: "grid grid-half" },
      chartCard({ title: "Categories", sub: "Where this user spends", body: rankList(cats.slice(0, 8).map((c) => ({ label: titleCase(c.category), value: Number(c.total) })), { format: fmtCompact, total: catTotal }) }),
      chartCard({ title: "Top merchants", sub: "By total spend", body: rankList(merchants.slice(0, 8).map((m) => ({ label: m.merchant, value: Number(m.total) })), { format: fmtCompact, total: catTotal }) })));
    view.append(chartCard({ title: "How they pay", sub: "Share of spend by payment method", body: rankList(pays.map((p) => ({ label: paymentLabel(p.payment_method), value: Number(p.total) })), { format: fmtCompact, total: catTotal, compact: true }) }));

    const rows = recent.items.map((e) => h("tr", { class: "clickable", onclick: () => openExpenseDrawer(e, { userMap, onChange: refreshAll }) },
      h("td", {}, dateShort(e.expense_date)),
      h("td", { class: "cell-clip" }, e.description || h("span", { class: "subtle" }, "-")),
      h("td", {}, e.merchant || h("span", { class: "subtle" }, "-")),
      h("td", {}, categoryBadge(e.category)),
      h("td", { class: "num" }, money(e.amount, e.currency))));
    view.append(chartCard({
      flush: true, title: "Recent expenses", sub: "Latest 10 in this period",
      controls: h("a", { class: "btn sm", href: `#/expenses?user_id=${user.id}` }, "View all"),
      body: h("div", { class: "table-wrap" }, h("table", { class: "table" },
        h("thead", {}, h("tr", {}, ["Date", "Description", "Merchant", "Category", "Amount"].map((t, i) => h("th", { class: i === 4 ? "num" : "" }, t)))),
        h("tbody", {}, rows))),
    }));
  },
};
