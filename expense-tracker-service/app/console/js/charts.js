// Chart.js wrappers in our look: ink and one accent, hairline grids, no chart junk.
// Colours come from the CSS design tokens so charts follow the light/dark theme. Chart.js
// draws on <canvas>, which can't read CSS `var(--x)`, so `resolve()` looks the value up first.

const registry = new Set();

export function resolve(color) {
  const match = /^var\((--[\w-]+)\)$/.exec(color);
  if (!match) return color;
  return getComputedStyle(document.documentElement).getPropertyValue(match[1]).trim();
}
const token = (name) => resolve(`var(${name})`);

/** Canvas can't parse CSS color-mix(), so build a plain rgba() from the resolved colour. */
function alpha(color, a) {
  const value = resolve(color);
  let r, g, b;
  if (value.startsWith("#")) {
    const hex = value.length === 4 ? [...value.slice(1)].map((c) => c + c).join("") : value.slice(1, 7);
    [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
  } else {
    [r, g, b] = (value.match(/[\d.]+/g) || [20, 20, 19]).slice(0, 3).map(Number);
  }
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

export function destroyCharts() {
  registry.forEach((chart) => chart.destroy());
  registry.clear();
}

function create(canvas, config) {
  const chart = new Chart(canvas, config);
  registry.add(chart);
  return chart;
}

function applyDefaults() {
  Chart.defaults.font.family = token("--font-sans");
  Chart.defaults.font.size = 11;
  Chart.defaults.color = token("--chart-label");
  // Modify the existing animation defaults; replacing the object drops Chart.js internals.
  Chart.defaults.animation.duration = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 600;
  Chart.defaults.animation.easing = "easeOutQuart";
}

/** A hairline vertical guide that follows the pointer on line charts. */
const crosshair = {
  id: "crosshair",
  afterDatasetsDraw(chart) {
    const active = chart.tooltip?.getActiveElements?.() || [];
    if (!active.length) return;
    const { ctx, chartArea } = chart;
    const x = active[0].element.x;
    ctx.save();
    ctx.strokeStyle = token("--chart-label");
    ctx.globalAlpha = 0.5;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(x, chartArea.top);
    ctx.lineTo(x, chartArea.bottom);
    ctx.stroke();
    ctx.restore();
  },
};

function tooltip(format, { multi = false } = {}) {
  return {
    backgroundColor: token("--color-tooltip-bg"),
    titleColor: token("--color-tooltip-text"),
    bodyColor: token("--color-tooltip-text"),
    padding: { x: 10, y: 8 },
    cornerRadius: 6,
    displayColors: multi,
    boxPadding: 4,
    titleFont: { weight: "500", size: 11 },
    bodyFont: { size: 12 },
    callbacks: { label: (ctx) => ` ${multi && ctx.dataset.label ? ctx.dataset.label + "  " : ""}${format(ctx.parsed.y ?? ctx.parsed.x ?? ctx.parsed)}` },
  };
}

const axes = (format, { horizontal = false, stacked = false } = {}) => {
  const value = { grid: { color: token("--chart-grid") }, border: { display: false }, beginAtZero: true, stacked, ticks: { callback: (v) => format(v), maxTicksLimit: 5, padding: 8 } };
  const category = { grid: { display: false }, border: { color: token("--chart-grid") }, stacked, ticks: { maxRotation: 0, autoSkip: true, padding: 6 } };
  return horizontal ? { x: value, y: category } : { x: category, y: value };
};

/** One quiet line with a faint fill. series: [{label, data, color}] */
export function areaChart(canvas, { labels, series, format }) {
  applyDefaults();
  return create(canvas, {
    type: "line",
    plugins: [crosshair],
    data: {
      labels,
      datasets: series.map((s) => ({
        label: s.label,
        data: s.data,
        borderColor: resolve(s.color),
        borderWidth: 1.75,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: token("--color-surface"),
        pointHoverBorderColor: resolve(s.color),
        pointHoverBorderWidth: 2,
        fill: true,
        backgroundColor: (ctx) => {
          const { chart } = ctx;
          if (!chart.chartArea) return alpha(s.color, 0.06);
          const g = chart.ctx.createLinearGradient(0, chart.chartArea.top, 0, chart.chartArea.bottom);
          g.addColorStop(0, alpha(s.color, 0.12));
          g.addColorStop(1, alpha(s.color, 0));
          return g;
        },
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: axes(format),
      plugins: { legend: { display: false }, tooltip: tooltip(format, { multi: series.length > 1 }) },
    },
  });
}

/** Bars. colors: array (one per bar) or a single colour. Default is ink. */
export function barChart(canvas, { labels, data, colors = "var(--chart-ink)", format, horizontal = false, onClick, label = "" }) {
  applyDefaults();
  const resolved = Array.isArray(colors) ? colors.map(resolve) : resolve(colors);
  return create(canvas, {
    type: "bar",
    data: { labels, datasets: [{ label, data, backgroundColor: resolved, borderRadius: 3, borderSkipped: false, maxBarThickness: horizontal ? 14 : 36 }] },
    options: {
      indexAxis: horizontal ? "y" : "x",
      responsive: true,
      maintainAspectRatio: false,
      scales: axes(format, { horizontal }),
      plugins: { legend: { display: false }, tooltip: tooltip(format) },
      onClick: onClick ? (_e, elements) => elements[0] && onClick(elements[0].index) : undefined,
      onHover: onClick ? (e, els) => { e.native.target.style.cursor = els.length ? "pointer" : "default"; } : undefined,
    },
  });
}

/** Stacked columns (the one place a multi-colour palette is needed). */
export function stackedBarChart(canvas, { labels, datasets, format }) {
  applyDefaults();
  return create(canvas, {
    type: "bar",
    data: { labels, datasets: datasets.map((d) => ({ label: d.label, data: d.data, backgroundColor: resolve(d.color), borderRadius: 2, borderSkipped: false, maxBarThickness: 40 })) },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: axes(format, { stacked: true }),
      plugins: { legend: { display: false }, tooltip: { ...tooltip(format, { multi: true }), itemSort: (a, b) => b.parsed.y - a.parsed.y, filter: (item) => item.parsed.y > 0 } },
    },
  });
}

export function sparkline(canvas, values, color = "var(--color-text-subtle)") {
  applyDefaults();
  return create(canvas, {
    type: "line",
    data: { labels: values.map((_, i) => i), datasets: [{ data: values, borderColor: resolve(color), borderWidth: 1.5, tension: 0.4, pointRadius: 0, fill: false }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      events: [],
      animation: { duration: 500 },
      scales: { x: { display: false }, y: { display: false, beginAtZero: true } },
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });
}
