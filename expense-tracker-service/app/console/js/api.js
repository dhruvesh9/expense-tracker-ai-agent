// Thin client for the Expense Tracker REST API (same origin, so no CORS needed).

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(status, body) {
    super(body?.error?.message || `Request failed (${status})`);
    this.status = status;
    this.code = body?.error?.code;
    this.details = body?.error?.details;
    this.requestId = body?.error?.request_id;
  }
}

/** Build "?a=1&b=2" from an object. Skips empty values; arrays repeat the key. */
export function qs(params = {}) {
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) value.forEach((v) => sp.append(key, v));
    else sp.append(key, value);
  }
  const text = sp.toString();
  return text ? `?${text}` : "";
}

async function request(method, path, { params, body } = {}) {
  const res = await fetch(`${BASE}${path}${qs(params)}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

export const get = (path, params) => request("GET", path, { params });
export const post = (path, body) => request("POST", path, { body });
export const patch = (path, body) => request("PATCH", path, { body });
export const del = (path, params) => request("DELETE", path, { params });

/** Fetch every page of a list endpoint (page_size 100), up to `limit` rows. */
export async function getAll(path, params = {}, limit = 5000) {
  const items = [];
  let page = 1;
  for (;;) {
    const data = await get(path, { ...params, page, page_size: 100 });
    items.push(...data.items);
    if (page >= data.pages || items.length >= limit) return items.slice(0, limit);
    page += 1;
  }
}

// ---- user lookups (never "load all users": the user base can be huge) ----
const USER_FIELDS = "id,name,country,city,default_currency,monthly_budget,created_at";
const userCache = new Map();

/** Resolve user ids to {id, name, ...}, fetching only the ones not seen before. */
export async function lookupUsers(ids) {
  const wanted = [...new Set(ids)].filter((id) => id !== null && id !== undefined);
  const missing = wanted.filter((id) => !userCache.has(id));
  for (let i = 0; i < missing.length; i += 100) {
    const data = await get("/users", { id: missing.slice(i, i + 100), page_size: 100, fields: USER_FIELDS });
    data.items.forEach((u) => userCache.set(u.id, u));
  }
  return new Map(wanted.filter((id) => userCache.has(id)).map((id) => [id, userCache.get(id)]));
}

/** Typeahead search by name (a few results; the API does the filtering). */
export async function searchUsers(text, limit = 8) {
  const data = await get("/users", { name: text, page_size: limit, sort: "name", fields: USER_FIELDS });
  data.items.forEach((u) => userCache.set(u.id, u));
  return data.items;
}

/** Forget cached users after an edit or delete. */
export const invalidateUsers = () => userCache.clear();

let categoriesCache = { at: 0, items: null };
/** Category list with a 60 s cache (it changes rarely; the form and filters both need it). */
export async function getCategories() {
  if (!categoriesCache.items || Date.now() - categoriesCache.at > 60000) {
    categoriesCache = { at: Date.now(), items: await get("/categories", { sort: "-count" }) };
  }
  return categoriesCache.items;
}
export const invalidateCategories = () => { categoriesCache = { at: 0, items: null }; };

export const reports = {
  summary: (p) => get("/reports/summary", p),
  byMonth: (p) => get("/reports/by-month", p),
  byCategory: (p) => get("/reports/by-category", p),
  byCategoryMonth: (p) => get("/reports/by-category-month", p),
  byUser: (p) => get("/reports/by-user", p),
  byMerchant: (p) => get("/reports/by-merchant", p),
  byPaymentMethod: (p) => get("/reports/by-payment-method", p),
  activeUsers: (p) => get("/reports/active-users", p),
  userGrowth: (p) => get("/reports/user-growth", p),
  budgets: (p) => get("/reports/budgets", p),
  byCountry: (p) => get("/reports/by-country", p),
  byWeekday: (p) => get("/reports/by-weekday", p),
  byDay: (p) => get("/reports/by-day", p),
};

export async function checkReady() {
  try {
    const res = await fetch("/ready");
    return res.ok;
  } catch {
    return false;
  }
}
