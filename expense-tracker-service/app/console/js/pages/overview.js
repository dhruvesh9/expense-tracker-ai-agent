// Overview: the numbers that matter, a trend, where the money goes, who spends, and when.

import { get, lookupUsers, reports } from "../api.js";
import { areaChart, barChart, destroyCharts } from "../charts.js";
import { bucket, change, chartCard, denseDaily, insightCard, kpiCard, rankList, segmented } from "../components.js";
import { openExpenseDrawer } from "../expense-ui.js";
import { dateShort, money, monthLabel, num, pct, titleCase } from "../format.js";
import { currentRange, getState, previousRange, rangeLabel, rangeParams } from "../state.js";
import { avatar, categoryBadge, clear, emptyState, h } from "../ui.js";
import { skOverview } from "../skeletons.js";
import { icon } from "../icons.js";

export default {
  meta: () => ({ title: "Overview", sub: rangeLabel(), global: true }),

  async render(view, _params, ctx) {
    const { currency } = getState();
    const range = currentRange();
    const prev = previousRange(range);
    const base = { ...rangeParams(range), currency };
    const fmt = (v) => money(v, currency);
    const fmtCompact = (v) => money(v, currency, { compact: true });

    view.append(...skOverview());

    // Only compare with the previous period if data reaches back that far; otherwise
    // "up 350000%" would just mean "there was no history yet".
    const first = await get("/expenses", { currency, sort: "expense_date", page_size: 1, fields: "expense_date" });
    const dataStart = first.items[0]?.expense_date;
    const before = prev && dataStart && prev.from >= dataStart ? { ...rangeParams(prev), currency } : null;

    const [summary, prevSummary, byMonth, byCategory, topUsers, byWeekday, byDay, top] = await Promise.all([
      reports.summary(base),
      before ? reports.summary(before) : null,
      reports.byMonth(base),
      reports.byCategory(base),
      reports.byUser({ ...base, limit: 8 }),
      reports.byWeekday(base),
      reports.byDay(base),
      get("/expenses", { ...base, sort: "-amount", page_size: 8 }),
    ]);
    if (!ctx.isCurrent()) return;
    const userMap = await lookupUsers(top.items.map((e) => e.user_id));
    if (!ctx.isCurrent()) return;
    clear(view);
    destroyCharts();

    const cur = summary.by_currency[0];
    if (!cur) {
      view.append(emptyState("No expenses in this period", `Nothing recorded in ${currency} for ${rangeLabel(range)}. Try a wider date range.`));
      return;
    }
    const prv = prevSummary?.by_currency[0];
    const daily = denseDaily(byDay.items, range);
    const countBuckets = bucket(daily.counts);
    const avgSpark = bucket(daily.totals).map((t, i) => t / Math.max(1, countBuckets[i]));

    // ---- header line ----
    view.append(h("div", { class: "toolbar" },
      h("p", { class: "muted" }, `${num(cur.count)} expenses from ${num(cur.users)} users in ${currency}, ${rangeLabel(range)}.`),
      h("a", { class: "btn toolbar-end", href: "#/present" }, icon("present"), "Present")));

    // ---- KPIs ----
    view.append(h("div", { class: "strip" },
      kpiCard({ label: "Total spend", value: cur.total, format: fmtCompact, delta: before ? change(cur.total, prv?.total) : undefined, goodWhenUp: false, spark: bucket(daily.totals), hint: "No prior period" }),
      kpiCard({ label: "Expenses", value: cur.count, format: (v) => num(Math.round(v)), delta: before ? change(cur.count, prv?.count) : undefined, goodWhenUp: true, spark: bucket(daily.counts), hint: "No prior period" }),
      kpiCard({ label: "Average expense", value: cur.average, format: fmt, delta: before ? change(cur.average, prv?.average) : undefined, goodWhenUp: false, spark: avgSpark, hint: "Per expense" }),
      kpiCard({ label: "Active users", value: cur.users, format: (v) => num(Math.round(v)), delta: before ? change(cur.users, prv?.users) : undefined, goodWhenUp: true, hint: "With spend" }),
      kpiCard({ label: "Largest expense", value: cur.maximum, format: fmtCompact, hint: `Smallest ${fmt(cur.minimum)}` })));

    // ---- insights ----
    const insights = [];
    const growth = before ? change(cur.total, prv?.total) : null;
    if (growth !== null) insights.push(insightCard("", `Spend ${growth >= 0 ? "up" : "down"} ${pct(Math.abs(growth))}`, "Compared with the previous period of equal length."));
    const catRows = [...byCategory.items].sort((a, b) => b.total - a.total);
    if (catRows[0]) insights.push(insightCard("", `${titleCase(catRows[0].category)} leads spending`, `${pct((catRows[0].total / cur.total) * 100, 0)} of the total, ${fmtCompact(catRows[0].total)}.`));
    const topUser = topUsers.items[0];
    if (topUser) insights.push(insightCard("", `${topUser.name} spends the most`, `${fmtCompact(topUser.total)}, ${pct((topUser.total / cur.total) * 100, 1)} of the total.`));
    const busiest = [...byWeekday.items].sort((a, b) => b.total - a.total)[0];
    if (busiest) insights.push(insightCard("", `${busiest.name} is the heaviest day`, `${fmtCompact(busiest.total)} across ${num(busiest.count)} expenses.`));
    view.append(h("div", { class: "strip" }, insights));

    // ---- trend + categories ----
    const monthCanvas = h("canvas");
    let monthChart;
    const drawMonths = (mode) => {
      monthChart?.destroy();
      const spend = mode === "spend";
      monthChart = areaChart(monthCanvas, {
        labels: byMonth.items.map((m) => monthLabel(m.month)),
        series: [{ label: spend ? "Spend" : "Expenses", data: byMonth.items.map((m) => (spend ? Number(m.total) : m.count)), color: "var(--chart-accent)" }],
        format: spend ? fmtCompact : (v) => num(Math.round(v)),
      });
    };
    const totalCat = catRows.reduce((a, c) => a + Number(c.total), 0);
    view.append(h("div", { class: "grid grid-main" },
      chartCard({ title: "Spending over time", sub: "Monthly totals by expense date", controls: segmented([{ id: "spend", label: "Spend" }, { id: "count", label: "Count" }], "spend", drawMonths), body: h("div", { class: "chart-box tall" }, monthCanvas) }),
      chartCard({ title: "Where the money goes", sub: "Share of spend by category", body: rankList(
        catRows.slice(0, 8).map((c) => ({ label: titleCase(c.category), value: Number(c.total), onClick: () => { location.hash = `#/expenses?currency=${currency}${c.category ? `&category=${encodeURIComponent(c.category)}` : ""}`; } })),
        { format: fmtCompact, total: totalCat }) })));
    drawMonths("spend");

    // ---- spenders + weekday ----
    const weekdayCanvas = h("canvas");
    const maxDay = Math.max(...byWeekday.items.map((d) => Number(d.total)));
    view.append(h("div", { class: "grid grid-half" },
      chartCard({ title: "Top spenders", sub: "Click a name to open the profile", body: rankList(
        topUsers.items.map((u) => ({ label: u.name, value: Number(u.total), onClick: () => { location.hash = `#/users/${u.user_id}`; } })),
        { format: fmtCompact, total: cur.total }) }),
      chartCard({ title: "Weekly rhythm", sub: "Total spend by weekday", body: h("div", { class: "chart-box" }, weekdayCanvas) })));
    barChart(weekdayCanvas, { labels: byWeekday.items.map((d) => d.name), data: byWeekday.items.map((d) => Number(d.total)), colors: byWeekday.items.map((d) => (Number(d.total) === maxDay ? "var(--chart-ink)" : "var(--chart-muted)")), format: fmtCompact });

    // ---- largest expenses ----
    const rows = top.items.map((e) => {
      const owner = userMap.get(e.user_id);
      return h("tr", { class: "clickable", onclick: () => openExpenseDrawer(e, { userMap, onChange: () => ctx.refresh() }) },
        h("td", {}, h("div", { class: "cell-user" }, avatar(owner?.name), h("strong", {}, owner?.name || `User #${e.user_id}`))),
        h("td", { class: "cell-clip" }, e.description || h("span", { class: "subtle" }, "No description")),
        h("td", { class: "cell-clip" }, e.merchant || h("span", { class: "subtle" }, "-")),
        h("td", {}, categoryBadge(e.category)),
        h("td", { class: "muted" }, dateShort(e.expense_date)),
        h("td", { class: "num" }, money(e.amount, e.currency)));
    });
    view.append(chartCard({
      flush: true,
      title: "Largest expenses",
      sub: "Top 8 in this period",
      controls: h("a", { class: "btn sm", href: "#/expenses" }, "View all"),
      body: h("div", { class: "table-wrap" }, h("table", { class: "table" },
        h("thead", {}, h("tr", {}, ["User", "Description", "Merchant", "Category", "Date", "Amount"].map((t, i) => h("th", { class: i === 5 ? "num" : "" }, t)))),
        h("tbody", {}, rows))),
    }));
  },
};
