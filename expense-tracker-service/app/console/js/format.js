// Number, money and date formatting. Amounts arrive from the API as exact decimal
// strings; Number() is fine for DISPLAY (never use it for arithmetic you persist).

const CURRENCY_LOCALE = "en-IN";

export function money(value, currency = "INR", { compact = false, decimals } = {}) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "-";
  return new Intl.NumberFormat(CURRENCY_LOCALE, {
    style: "currency",
    currency,
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: decimals ?? (compact ? 1 : 2),
    minimumFractionDigits: decimals ?? (compact ? 0 : 2),
  }).format(n);
}

export const num = (n, opts) => new Intl.NumberFormat("en-IN", opts).format(Number(n) || 0);
export const pct = (n, digits = 1) => `${(Number(n) || 0).toFixed(digits)}%`;

export function dateShort(iso) {
  if (!iso) return "-";
  const d = iso.length === 10 ? new Date(`${iso}T00:00:00`) : new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}
export function dateTime(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
export function monthLabel(ym, long = false) {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("en-GB", long ? { month: "long", year: "numeric" } : { month: "short", year: "2-digit" });
}

export const initials = (name) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
export const titleCase = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : "Uncategorised");

/** Percent change from `previous` to `current`; null when there is no baseline. */
export function change(current, previous) {
  const c = Number(current), p = Number(previous);
  if (!Number.isFinite(p) || p === 0) return null;
  return ((c - p) / p) * 100;
}

// Stable colours so a category/user looks the same on every chart.
const CATEGORY_ORDER = ["food", "groceries", "transport", "bills", "entertainment", "shopping", "wellness", "travel", "education", "rent"];
export function categoryColor(category) {
  if (!category) return "var(--chart-neutral)";
  let i = CATEGORY_ORDER.indexOf(category);
  if (i < 0) i = [...category].reduce((a, c) => a + c.charCodeAt(0), 0) % 10;
  return `var(--chart-${(i % 10) + 1})`;
}
export const userColor = (id) => `var(--chart-${(id % 10) + 1})`;

// ---- countries (ISO 3166-1 alpha-2) ----
const regionNames = new Intl.DisplayNames(["en"], { type: "region" });
export function countryName(code) {
  if (!code) return "Unassigned";
  try { return regionNames.of(code) || code; } catch { return code; }
}
export const COUNTRY_CODES = ["AE", "AU", "BR", "CA", "CH", "DE", "ES", "FR", "GB", "IE", "IN", "IT", "JP", "KR", "MX", "NL", "NZ", "SA", "SE", "SG", "US", "ZA"];

// ---- payment methods ----
export const PAYMENT_METHODS = [
  { id: "digital_wallet", label: "Digital wallet" },
  { id: "credit_card", label: "Credit card" },
  { id: "debit_card", label: "Debit card" },
  { id: "bank_transfer", label: "Bank transfer" },
  { id: "cash", label: "Cash" },
  { id: "other", label: "Other" },
];
export const paymentLabel = (id) => PAYMENT_METHODS.find((m) => m.id === id)?.label || "Not recorded";
export const paymentColor = (id) => `var(--chart-${((PAYMENT_METHODS.findIndex((m) => m.id === id) + 8) % 10) + 1})`;
