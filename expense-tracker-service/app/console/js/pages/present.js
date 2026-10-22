// Presentation mode: a full-screen, keyboard-driven deck built from live data.
// Keys: Left/Right (or Space) to move, F for fullscreen, Esc to exit.

import { get, reports } from "../api.js";
import { areaChart, destroyCharts } from "../charts.js";
import { change, rankList } from "../components.js";
import { money, monthLabel, num, paymentLabel, pct, titleCase } from "../format.js";
import { icon } from "../icons.js";
import { currentRange, getState, previousRange, rangeLabel, rangeParams } from "../state.js";
import { animateNumber, h } from "../ui.js";
import { skPresent } from "../skeletons.js";

/** Shrink a number's font until it fits its column (long values must never overlap neighbours). */
function fitToCell(el) {
  el.style.fontSize = "";
  let size = parseFloat(getComputedStyle(el).fontSize);
  while (el.scrollWidth > el.parentElement.clientWidth && size > 22) {
    size -= 3;
    el.style.fontSize = `${size}px`;
  }
}

const thisMonth = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`; };

export default {
  meta: () => ({ title: "Presentation", sub: "", global: false }),

  async render(view, _params, ctx) {
    const { currency } = getState();
    const range = currentRange();
    const prev = previousRange(range);
    const base = { ...rangeParams(range), currency };
    const fmt = (v) => money(v, currency);
    const fmtCompact = (v) => money(v, currency, { compact: true });

    view.append(...skPresent());
    // Compare with the previous period only if data reaches back that far.
    const first = await get("/expenses", { currency, sort: "expense_date", page_size: 1, fields: "expense_date" });
    const dataStart = first.items[0]?.expense_date;
    const comparePrev = prev && dataStart && prev.from >= dataStart;
    const [summary, prevSummary, byMonth, byCategory, topUsers, growth, active, budgets, byMerchant, byPayment] = await Promise.all([
      reports.summary(base),
      comparePrev ? reports.summary({ ...rangeParams(prev), currency }) : null,
      reports.byMonth(base),
      reports.byCategory(base),
      reports.byUser({ ...base, limit: 1 }),
      reports.userGrowth({}),
      reports.activeUsers({}),
      reports.budgets({ month: thisMonth(), limit: 1 }),
      reports.byMerchant(base),
      reports.byPaymentMethod(base),
    ]);
    if (!ctx.isCurrent()) return;
    view.replaceChildren();
    destroyCharts();

    const cur = summary.by_currency[0];
    if (!cur) {
      view.append(h("p", { class: "muted" }, `No ${currency} expenses in this period, so there is nothing to present.`));
      return;
    }
    const growthPct = change(cur.total, prevSummary?.by_currency[0]?.total);
    const cats = [...byCategory.items].sort((a, b) => b.total - a.total);
    const topCat = cats[0];
    const total = cats.reduce((a, c) => a + Number(c.total), 0);
    const merchants = byMerchant.items.filter((m) => m.merchant).slice(0, 6);
    const payments = [...byPayment.items].sort((a, b) => b.total - a.total);
    const counts = budgets.counts;
    const totalUsers = growth.items.at(-1)?.total_users ?? 0;
    const lastActive = active.items.at(-1);
    const topUser = topUsers.items[0];

    const slides = [];
    const stage = h("div", { class: "deck-stage" });
    const dots = h("div", { class: "dots" });
    const progress = h("div", { class: "deck-progress" });
    let index = 0;
    const draws = new Map();
    const drawn = new Set();
    const add = (content, draw) => {
      const el = h("section", { class: "slide" }, content);
      slides.push(el);
      stage.append(el);
      if (draw) draws.set(slides.length - 1, draw);
    };

    // 1. Title
    add([
      h("div", { class: "eyebrow" }, `Expense Tracker · ${rangeLabel(range)}`),
      h("h1", {}, "Understand ", h("span", { class: "accent" }, "your spending")),
      h("p", { class: "lede" }, `${num(cur.count)} expenses from ${num(cur.users)} people, tracked in ${currency}. Here is how spending looks.`),
    ]);

    // 2. Headline numbers
    const stats = [
      { v: cur.total, f: fmtCompact, l: "Total spend", delta: growthPct },
      { v: cur.count, f: (x) => num(Math.round(x)), l: "Expenses recorded" },
      { v: totalUsers, f: (x) => num(Math.round(x)), l: "Total users" },
      { v: cur.average, f: fmt, l: "Average expense" },
    ];
    const statEls = stats.map((s) => h("div", { class: "big-stat" }, h("div", { class: "v" }, s.f(0)), h("div", { class: "l" }, s.l,
      s.delta !== null && s.delta !== undefined ? h("span", { class: `delta ${s.delta >= 0 ? "down" : "up"}` }, icon(s.delta >= 0 ? "arrowUp" : "arrowDown"), pct(Math.abs(s.delta))) : null)));
    add([h("div", { class: "eyebrow" }, "The numbers"), h("h2", {}, "The headline figures"), h("div", { class: "big-stats" }, statEls)],
      () => statEls.forEach((el, i) => {
        const value = el.firstChild;
        value.textContent = stats[i].f(stats[i].v); // measure the FINAL text, then fit it to the cell
        fitToCell(value);
        animateNumber(value, Number(stats[i].v), stats[i].f, 1400);
      }));

    // 3. Growth
    const growthCanvas = h("canvas");
    add([
      h("div", { class: "eyebrow" }, "Growth"),
      h("h2", {}, `${num(totalUsers)} users, ${lastActive ? num(lastActive.active_users) + " active this month" : "and growing"}`),
      h("div", { class: "slide-split" },
        h("div", { class: "chart-box" }, growthCanvas),
        h("p", { class: "lede" }, lastActive ? `${monthLabel(lastActive.month, true)}: ${num(lastActive.active_users)} users logged ${num(lastActive.expenses)} expenses, about ${num(Math.round(lastActive.expenses / Math.max(1, lastActive.active_users)))} each.` : "")),
    ], () => areaChart(growthCanvas, { labels: active.items.map((a) => monthLabel(a.month)), series: [{ label: "Monthly active users", data: active.items.map((a) => a.active_users), color: "var(--chart-accent)" }], format: (v) => num(Math.round(v)) }));

    // 4. Spending trend
    const trendCanvas = h("canvas");
    add([
      h("div", { class: "eyebrow" }, "Spending"),
      h("h2", {}, growthPct === null || growthPct === undefined ? "How spending moves month to month" : `Spend is ${growthPct >= 0 ? "up" : "down"} ${pct(Math.abs(growthPct))} on the previous period`),
      h("div", { class: "chart-box" }, trendCanvas),
    ], () => areaChart(trendCanvas, { labels: byMonth.items.map((m) => monthLabel(m.month)), series: [{ label: "Spend", data: byMonth.items.map((m) => Number(m.total)), color: "var(--chart-accent)" }], format: fmtCompact }));

    // 5. Categories
    add([
      h("div", { class: "eyebrow" }, "Where the money goes"),
      h("h2", {}, topCat ? `${titleCase(topCat.category)} leads, at ${pct((topCat.total / total) * 100, 0)} of spend` : "Spending by category"),
      h("div", { style: { "max-width": "720px" } }, rankList(cats.slice(0, 6).map((c) => ({ label: titleCase(c.category), value: Number(c.total) })), { format: fmtCompact, total })),
    ]);

    // 6. Habits
    add([
      h("div", { class: "eyebrow" }, "Habits"),
      h("h2", {}, merchants[0] ? `${merchants[0].merchant} is the top merchant` : "Merchants and payment habits"),
      h("div", { class: "slide-split top" },
        rankList(merchants.map((m) => ({ label: m.merchant, value: Number(m.total) })), { format: fmtCompact, total }),
        rankList(payments.map((p) => ({ label: paymentLabel(p.payment_method), value: Number(p.total) })), { format: fmtCompact, total, compact: true })),
    ]);

    // 7. Budgets
    if (counts.total) {
      add([
        h("div", { class: "eyebrow" }, `Budgets · ${monthLabel(budgets.month, true)}`),
        h("h2", {}, `${num(counts.ok)} of ${num(counts.total)} users are on track this month`),
        h("div", { class: "big-stats three" },
          h("div", { class: "big-stat" }, h("div", { class: "v" }, num(counts.ok)), h("div", { class: "l" }, "On track")),
          h("div", { class: "big-stat" }, h("div", { class: "v", style: { color: "var(--color-warning)" } }, num(counts.near)), h("div", { class: "l" }, "Close to the limit")),
          h("div", { class: "big-stat" }, h("div", { class: "v", style: { color: "var(--color-negative)" } }, num(counts.over)), h("div", { class: "l" }, "Over budget"))),
      ]);
    }

    // 8. Takeaways
    const takeaways = [];
    if (growthPct !== null && growthPct !== undefined) takeaways.push(`Spend is ${growthPct >= 0 ? "up" : "down"} ${pct(Math.abs(growthPct))} versus the previous period.`);
    if (topCat) takeaways.push(`${titleCase(topCat.category)} is the biggest category at ${pct((topCat.total / total) * 100, 0)} of spend.`);
    if (topUser) takeaways.push(`The biggest spender accounts for ${pct((topUser.total / cur.total) * 100, 1)} of the total.`);
    if (counts.total) takeaways.push(`${num(counts.over + counts.near)} users need a budget nudge this month.`);
    takeaways.push(`${num(totalUsers)} users and growing. The next chapter is every market.`);
    add([h("div", { class: "eyebrow" }, "Takeaways"), h("h2", {}, "What to remember"), h("ul", { class: "takeaways" }, takeaways.map((t) => h("li", {}, t)))]);

    // ---- navigation ----
    const counter = h("span", { class: "muted" });
    function show(i) {
      index = Math.max(0, Math.min(slides.length - 1, i));
      slides.forEach((s, n) => { s.classList.toggle("active", n === index); s.classList.toggle("past", n < index); });
      [...dots.children].forEach((d, n) => d.setAttribute("aria-current", String(n === index)));
      counter.textContent = `${index + 1} / ${slides.length}`;
      progress.style.width = `${((index + 1) / slides.length) * 100}%`;
      if (!drawn.has(index) && draws.has(index)) { drawn.add(index); requestAnimationFrame(() => draws.get(index)()); }
    }
    slides.forEach((_, n) => dots.append(h("button", { "aria-label": `Go to slide ${n + 1}`, onclick: () => show(n) })));

    const exit = () => { location.hash = "#/overview"; };
    const toggleFullscreen = () => { if (document.fullscreenElement) document.exitFullscreen(); else deck.requestFullscreen?.(); };
    const deck = h("div", { class: "deck", role: "region", "aria-label": "Presentation" },
      progress,
      h("div", { class: "deck-top" },
        h("div", { class: "brand" }, h("div", { class: "brand-mark" }, "E"), h("div", { class: "brand-name" }, "Expense Tracker")),
        h("div", { class: "row" }, counter,
          h("button", { class: "btn icon", title: "Fullscreen (F)", "aria-label": "Fullscreen", onclick: toggleFullscreen }, icon("fullscreen")),
          h("button", { class: "btn", onclick: exit }, "Exit"))),
      stage,
      h("div", { class: "deck-bottom" },
        h("button", { class: "btn icon", "aria-label": "Previous slide", onclick: () => show(index - 1) }, icon("left")),
        dots,
        h("button", { class: "btn icon", "aria-label": "Next slide", onclick: () => show(index + 1) }, icon("right"))));
    document.body.append(deck);
    show(0);

    const onKey = (e) => {
      if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") { e.preventDefault(); show(index + 1); }
      else if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); show(index - 1); }
      else if (e.key === "Escape" && !document.fullscreenElement) exit();
      else if (e.key.toLowerCase() === "f") toggleFullscreen();
      else if (e.key === "Home") show(0);
      else if (e.key === "End") show(slides.length - 1);
    };
    document.addEventListener("keydown", onKey);
    const onResize = () => deck.querySelectorAll(".big-stat .v").forEach(fitToCell);
    window.addEventListener("resize", onResize);

    return () => {
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
      if (document.fullscreenElement) document.exitFullscreen();
      deck.remove();
    };
  },
};
