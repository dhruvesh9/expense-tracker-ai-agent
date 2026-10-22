// Analytics: growth & engagement, budgets, merchants, payment habits, fixed vs flexible spend,
// category trends, a spending calendar, countries and currencies.

import { reports } from "../api.js";
import { areaChart, barChart, destroyCharts, stackedBarChart } from "../charts.js";
import { chartCard, partsBar, rankList } from "../components.js";
import { categoryColor, countryName, dateShort, money, monthLabel, num, paymentLabel, pct, titleCase } from "../format.js";
import { addDays, currentRange, getState, iso, rangeLabel, rangeParams } from "../state.js";
import { avatar, clear, emptyState, h, hideTooltip, showTooltip } from "../ui.js";
import { skAnalytics } from "../skeletons.js";

const thisMonth = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`; };

/** GitHub-style calendar: one cell per day, darker = more spent. */
function calendarHeatmap(items, currency) {
  const byDay = new Map(items.map((i) => [i.day, i]));
  const end = new Date();
  let start = addDays(end, -364);
  start = addDays(start, -((start.getDay() + 6) % 7)); // back to Monday
  const weeks = Math.ceil(((end - start) / 86400000 + 1) / 7);

  const totals = items.map((i) => Number(i.total)).sort((a, b) => a - b);
  const at = (q) => totals[Math.min(totals.length - 1, Math.floor(q * totals.length))] || 0;
  const [t1, t2, t3] = [at(0.25), at(0.5), at(0.8)];
  const level = (v) => (v <= 0 ? 0 : v <= t1 ? 1 : v <= t2 ? 2 : v <= t3 ? 3 : 4);

  const months = h("div", { class: "heat-months" });
  const grid = h("div", { class: "heat", role: "img", "aria-label": "Daily spending calendar" });
  let lastMonth = -1;
  for (let w = 0; w < weeks; w += 1) {
    const monday = addDays(start, w * 7);
    const label = monday.getMonth() !== lastMonth && monday <= end ? monday.toLocaleDateString("en-GB", { month: "short" }) : "";
    if (label) lastMonth = monday.getMonth();
    months.append(h("span", { style: { "grid-column": String(w + 1) } }, label));
    for (let d = 0; d < 7; d += 1) {
      const date = addDays(monday, d);
      if (date > end) { grid.append(h("span", { class: "heat-cell", style: { visibility: "hidden" } })); continue; }
      const key = iso(date);
      const hit = byDay.get(key);
      const text = hit ? `${dateShort(key)}: ${money(hit.total, currency)} across ${num(hit.count)} expense${hit.count === 1 ? "" : "s"}` : `${dateShort(key)}: no spending`;
      grid.append(h("span", {
        class: "heat-cell", dataset: { level: level(hit ? Number(hit.total) : 0) },
        onmousemove: (e) => showTooltip(e, text), onmouseleave: hideTooltip,
        onclick: () => { location.hash = `#/expenses?date_from=${key}&date_to=${key}&currency=${currency}`; },
        style: { cursor: "pointer" },
      }));
    }
  }
  const legend = h("div", { class: "heat-legend" }, "Less", [0, 1, 2, 3, 4].map((l) => h("span", { class: "heat-cell", dataset: { level: l } })), "More");
  return h("div", { class: "stack" }, h("div", { class: "heat-scroll" }, months, grid), legend);
}

export default {
  meta: () => ({ title: "Analytics", sub: rangeLabel(), global: true }),

  async render(view, _params, ctx) {
    const { currency } = getState();
    const range = currentRange();
    const base = { ...rangeParams(range), currency };
    const fmt = (v) => money(v, currency);
    const fmtCompact = (v) => money(v, currency, { compact: true });
    const yearAgo = iso(addDays(new Date(), -364));

    view.append(...skAnalytics());

    const [growth, active, budgets, byDay, byCatMonth, byMerchant, byPayment, recurring, oneOff, byCountry, byCategory, markets] = await Promise.all([
      reports.userGrowth({}),
      reports.activeUsers({}),
      reports.budgets({ month: thisMonth(), limit: 8 }),
      reports.byDay({ currency, date_from: yearAgo }),
      reports.byCategoryMonth(base),
      reports.byMerchant(base),
      reports.byPaymentMethod(base),
      reports.summary({ ...base, is_recurring: true }),
      reports.summary({ ...base, is_recurring: false }),
      reports.byCountry(base),
      reports.byCategory(base),
      reports.summary(rangeParams(range)),
    ]);
    if (!ctx.isCurrent()) return;
    clear(view);
    destroyCharts();

    // ---- 1. growth & engagement (all users, all currencies) ----
    const growthCanvas = h("canvas");
    const activeCanvas = h("canvas");
    const totalUsers = growth.items.at(-1)?.total_users ?? 0;
    const lastActive = active.items.at(-1);
    view.append(h("div", { class: "grid grid-half" },
      chartCard({ title: "User growth", sub: `${num(totalUsers)} users in total. New signups per month`, body: h("div", { class: "chart-box" }, growthCanvas) }),
      chartCard({ title: "Monthly active users", sub: lastActive ? `${num(lastActive.active_users)} users logged expenses in ${monthLabel(lastActive.month, true)}` : "Users with at least one expense per month", body: h("div", { class: "chart-box" }, activeCanvas) })));
    barChart(growthCanvas, { labels: growth.items.map((g) => monthLabel(g.month)), data: growth.items.map((g) => g.new_users), colors: "var(--chart-ink)", format: (v) => num(Math.round(v)) });
    areaChart(activeCanvas, { labels: active.items.map((a) => monthLabel(a.month)), series: [{ label: "Active users", data: active.items.map((a) => a.active_users), color: "var(--chart-accent)" }], format: (v) => num(Math.round(v)) });

    // ---- 2. budgets this month ----
    const counts = budgets.counts;
    const watch = budgets.items.filter((b) => b.status !== "ok");
    const budgetRows = watch.map((b) => h("tr", { class: "clickable", onclick: () => { location.hash = `#/users/${b.user_id}`; } },
      h("td", {}, h("div", { class: "cell-user" }, avatar(b.name), h("strong", {}, b.name))),
      h("td", { class: "num" }, `${money(b.spent, b.currency)} / ${money(b.budget, b.currency)}`),
      h("td", { style: { "min-width": "160px" } }, h("div", { class: "share-bar" }, h("span", { style: { width: `${Math.min(100, b.percent_used)}%`, "--bar": b.status === "over" ? "var(--color-negative)" : "var(--color-warning)" } }))),
      h("td", {}, h("span", { class: `badge ${b.status === "over" ? "negative" : "warning"}` }, `${pct(b.percent_used, 0)} used`))));
    view.append(chartCard({
      flush: true, title: `Budget health, ${monthLabel(budgets.month, true)}`,
      sub: counts.total ? `${num(counts.ok)} on track · ${num(counts.near)} near limit · ${num(counts.over)} over budget, of ${num(counts.total)} budgets. Worst 8 shown; spend counted in each user's own currency.` : "No users have set a budget yet",
      body: counts.total
        ? (watch.length ? h("div", { class: "table-wrap" }, h("table", { class: "table" },
          h("thead", {}, h("tr", {}, ["User", "Spent / budget", "Progress", "Status"].map((t, i) => h("th", { class: i === 1 ? "num" : "" }, t)))), h("tbody", {}, budgetRows)))
          : emptyState("Everyone is on track", "No one is near or over their monthly budget."))
        : emptyState("No budgets set", "Users can set a monthly budget on their profile."),
    }));

    if (!byCatMonth.items.length) {
      view.append(emptyState(`No ${currency} expenses in this period`, "Pick another currency or a wider date range."));
      return;
    }

    // ---- 3. spending calendar ----
    view.append(chartCard({ title: "Spending calendar", sub: `Daily spend in ${currency}, last 12 months. Click a day to see its expenses`, body: calendarHeatmap(byDay.items, currency) }));

    // ---- 4. categories by month (stacked) ----
    const months = [...new Set(byCatMonth.items.map((i) => i.month))].sort();
    const catTotals = new Map();
    byCatMonth.items.forEach((i) => catTotals.set(i.category, (catTotals.get(i.category) || 0) + Number(i.total)));
    const cats = [...catTotals.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c);
    const stackCanvas = h("canvas");
    const legend = h("div", { class: "toolbar", style: { gap: "var(--space-2)" } });
    view.append(chartCard({ title: "Category trends", sub: "Monthly spend, stacked by category. Click a category to hide it", body: h("div", { class: "stack" }, h("div", { class: "chart-box tall" }, stackCanvas), legend) }));
    const stack = stackedBarChart(stackCanvas, {
      labels: months.map((m) => monthLabel(m)),
      datasets: cats.map((c) => ({ label: titleCase(c), color: categoryColor(c), data: months.map((m) => Number(byCatMonth.items.find((i) => i.month === m && i.category === c)?.total || 0)) })),
      format: fmtCompact,
    });
    cats.forEach((c, i) => {
      const chip = h("button", { type: "button", class: "chip-toggle", onclick: () => {
        stack.setDatasetVisibility(i, !stack.isDatasetVisible(i));
        stack.update();
        chip.classList.toggle("off", !stack.isDatasetVisible(i));
      } }, h("span", { class: "swatch", style: { "--swatch": categoryColor(c) } }), titleCase(c));
      legend.append(chip);
    });

    // ---- 5. merchants + payment methods ----
    const merchants = byMerchant.items.filter((m) => m.merchant).slice(0, 8);
    const pays = [...byPayment.items].sort((a, b) => b.total - a.total);
    const payTotal = pays.reduce((a, p) => a + Number(p.total), 0);
    const merchTotal = byMerchant.items.reduce((a, m) => a + Number(m.total), 0);
    view.append(h("div", { class: "grid grid-half" },
      chartCard({ title: "Top merchants", sub: "Click one to see its expenses", body: rankList(
        merchants.map((m) => ({ label: m.merchant, value: Number(m.total), onClick: () => { location.hash = `#/expenses?merchant=${encodeURIComponent(m.merchant)}&currency=${currency}`; } })),
        { format: fmtCompact, total: merchTotal }) }),
      chartCard({ title: "How people pay", sub: "Share of spend by payment method", body: rankList(
        pays.map((p) => ({ label: paymentLabel(p.payment_method), value: Number(p.total), onClick: () => { location.hash = `#/expenses?payment_method=${p.payment_method || ""}&currency=${currency}`; } })),
        { format: fmtCompact, total: payTotal }) })));

    // ---- 6. fixed vs flexible + countries ----
    const fixed = Number(recurring.by_currency[0]?.total || 0);
    const flexible = Number(oneOff.by_currency[0]?.total || 0);
    const countries = byCountry.items.filter((c) => c.country);
    const countryTotal = countries.reduce((a, c) => a + Number(c.total), 0);
    view.append(h("div", { class: "grid grid-half" },
      chartCard({ title: "Fixed vs flexible spending", sub: `Recurring bills and subscriptions are ${pct((fixed / Math.max(1, fixed + flexible)) * 100, 0)} of spend`, body: partsBar([
        { label: "Recurring (fixed)", value: fixed, color: "var(--chart-ink)" },
        { label: "One-off (flexible)", value: flexible, color: "var(--chart-muted)" },
      ], { format: fmtCompact }) }),
      chartCard({ title: "Spend by country", sub: `Where users are, in ${currency}`, body: countries.length
        ? rankList(countries.slice(0, 8).map((c) => ({ label: countryName(c.country), value: Number(c.total) })), { format: fmtCompact, total: countryTotal, compact: true })
        : emptyState("No country data for this currency", "") })));

    // ---- 7. category table ----
    const catRows = [...byCategory.items].sort((a, b) => b.total - a.total);
    const catSum = catRows.reduce((a, c) => a + Number(c.total), 0);
    view.append(chartCard({
      flush: true, title: "Category breakdown", sub: "Click a row to open its expenses",
      body: h("div", { class: "table-wrap" }, h("table", { class: "table" },
        h("thead", {}, h("tr", {}, ["Category", "Expenses", "Total", "Average", "Share"].map((t, i) => h("th", { class: i > 0 && i < 4 ? "num" : "" }, t)))),
        h("tbody", {}, catRows.map((c) => h("tr", { class: "clickable", onclick: () => { location.hash = `#/expenses?currency=${currency}${c.category ? `&category=${encodeURIComponent(c.category)}` : ""}`; } },
          h("td", {}, h("span", { class: "badge" }, c.category || "uncategorised")),
          h("td", { class: "num" }, num(c.count)),
          h("td", { class: "num" }, fmt(c.total)),
          h("td", { class: "num" }, fmt(c.total / c.count)),
          h("td", { style: { "min-width": "160px" } }, h("div", { class: "row" }, h("div", { class: "share-bar", style: { flex: 1 } }, h("span", { style: { width: `${(c.total / catSum) * 100}%` } })), h("span", { class: "muted" }, pct((c.total / catSum) * 100, 0))))))))),
    }));

    // ---- 8. markets / currencies ----
    view.append(chartCard({
      flush: true, title: "Markets and currencies", sub: "Each currency is reported separately; amounts are never converted or combined",
      body: h("div", { class: "table-wrap" }, h("table", { class: "table" },
        h("thead", {}, h("tr", {}, ["Currency", "Users", "Expenses", "Total", "Average", "Largest"].map((t, i) => h("th", { class: i > 0 ? "num" : "" }, t)))),
        h("tbody", {}, [...markets.by_currency].sort((a, b) => b.count - a.count).map((m) => h("tr", {},
          h("td", {}, h("strong", {}, m.currency)),
          h("td", { class: "num" }, num(m.users)),
          h("td", { class: "num" }, num(m.count)),
          h("td", { class: "num" }, money(m.total, m.currency)),
          h("td", { class: "num" }, money(m.average, m.currency)),
          h("td", { class: "num" }, money(m.maximum, m.currency))))))),
    }));
  },
};
