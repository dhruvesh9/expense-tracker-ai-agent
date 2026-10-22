// Expense create/edit form and the expense detail drawer (shared by several pages).

import { ApiError, del, getCategories, invalidateCategories, lookupUsers, patch, post } from "./api.js";
import { PAYMENT_METHODS, dateShort, dateTime, money, paymentLabel, titleCase } from "./format.js";
import { shared } from "./shared.js";
import { todayIso } from "./state.js";
import { categoryBadge, confirmDialog, drawer, h, modal, toast, userPicker } from "./ui.js";

/** Map API validation errors (details[].location = "body.amount") to field names. */
function fieldErrors(err) {
  const map = {};
  if (err instanceof ApiError && Array.isArray(err.details)) {
    for (const d of err.details) map[d.location.split(".").pop()] = d.message;
  } else if (err instanceof ApiError && err.code === "invalid_reference") {
    map.user_id = err.message;
  }
  return map;
}

export async function openExpenseForm({ expense = null, defaults = {}, onSaved } = {}) {
  const categories = await getCategories();
  const editing = Boolean(expense);
  const v = expense || { user_id: defaults.user_id || "", amount: "", currency: shared.currencies[0] || "INR", category: "", description: "", expense_date: todayIso(), ...defaults };

  // Choosing a user pre-fills the currency with *their* default (unless it was edited by hand).
  let currencyTouched = editing;
  const ownerId = Number(v.user_id) || null;
  const owner = ownerId ? (await lookupUsers([ownerId])).get(ownerId) : null;
  const currency = h("input", { class: "input", name: "currency", list: "currency-list", maxlength: "3", value: v.currency, required: true, style: { "text-transform": "uppercase" } });
  currency.addEventListener("input", () => { currencyTouched = true; });
  const user = userPicker({
    initial: owner || null,
    placeholder: "Search users by name...",
    onSelect: (picked) => { if (picked && !currencyTouched) currency.value = picked.default_currency; },
  });
  if (editing) user.input.disabled = true; // an expense cannot move to another user

  const amount = h("input", { class: "input", name: "amount", inputmode: "decimal", placeholder: "0.00", value: v.amount, required: true, autocomplete: "off" });
  const currencyList = h("datalist", { id: "currency-list" }, ["INR", "USD", "EUR", "GBP", "AED", "SGD", "AUD", "CAD", "BRL", ...shared.currencies].map((c) => h("option", { value: c })));
  const date = h("input", { class: "input", type: "date", name: "expense_date", value: v.expense_date, required: true });
  const category = h("input", { class: "input", name: "category", list: "category-list", value: v.category || "", placeholder: "e.g. food", autocomplete: "off" });
  const categoryList = h("datalist", { id: "category-list" }, categories.map((c) => h("option", { value: c.category })));
  const merchant = h("input", { class: "input", name: "merchant", value: v.merchant || "", maxlength: "100", placeholder: "e.g. Starbucks", autocomplete: "off" });
  const payment = h("select", { class: "select", name: "payment_method" },
    h("option", { value: "" }, "Not recorded"),
    PAYMENT_METHODS.map((m) => h("option", { value: m.id, selected: m.id === v.payment_method }, m.label)));
  const recurring = h("input", { type: "checkbox", name: "is_recurring", checked: Boolean(v.is_recurring) });
  const description = h("textarea", { class: "textarea", name: "description", maxlength: "500", placeholder: "What was it for?" }, v.description || "");

  const errorSlots = {};
  const wrap = (label, control, name, cls = "") => {
    const slot = h("span", { class: "field-error" });
    errorSlots[name] = { slot, control: control.querySelector?.("input, select, textarea") || control };
    return h("div", { class: `field ${cls}` }, h("span", { class: "label" }, label), control, slot);
  };

  const form = h("form", { class: "form-grid", novalidate: true },
    wrap("User", user.el, "user_id", "full"),
    wrap("Amount", amount, "amount"),
    wrap("Currency", currency, "currency"),
    wrap("Expense date", date, "expense_date"),
    wrap("Category", category, "category"),
    wrap("Merchant", merchant, "merchant"),
    wrap("Paid with", payment, "payment_method"),
    h("label", { class: "checkbox full" }, recurring, h("span", {}, "Recurring (subscription, rent or bill)")),
    wrap("Description", description, "description", "full"),
    currencyList, categoryList);

  const save = h("button", { class: "btn primary", type: "button" }, editing ? "Save changes" : "Create expense");
  let close;

  async function submit(e) {
    e?.preventDefault();
    Object.values(errorSlots).forEach(({ slot, control }) => { slot.textContent = ""; control.removeAttribute("aria-invalid"); });
    const body = {
      amount: amount.value.trim(),
      currency: currency.value.trim(),
      expense_date: date.value,
      category: category.value.trim() || null,
      description: description.value.trim() || null,
      merchant: merchant.value.trim() || null,
      payment_method: payment.value || null,
      is_recurring: recurring.checked,
    };
    if (!editing) body.user_id = user.get()?.id || 0;
    save.disabled = true;
    try {
      const saved = editing ? await patch(`/expenses/${expense.id}`, body) : await post("/expenses", body);
      invalidateCategories();
      toast(editing ? `Expense #${saved.id} updated` : `Expense #${saved.id} created`, "success");
      close();
      onSaved?.(saved);
    } catch (err) {
      const errors = fieldErrors(err);
      const unmatched = Object.keys(errors).filter((k) => !errorSlots[k]);
      for (const [name, message] of Object.entries(errors)) {
        if (errorSlots[name]) { errorSlots[name].slot.textContent = message; errorSlots[name].control.setAttribute("aria-invalid", "true"); }
      }
      if (!Object.keys(errors).length || unmatched.length) toast(err.message, "error");
    } finally {
      save.disabled = false;
    }
  }
  form.addEventListener("submit", submit);

  close = modal({
    title: editing ? `Edit expense #${expense.id}` : "New expense",
    body: form,
    actions: [h("button", { class: "btn", type: "button", onclick: () => close() }, "Cancel"), save],
  });
  save.addEventListener("click", submit);
}

export function openExpenseDrawer(expense, { userMap, onChange } = {}) {
  const owner = userMap?.get(expense.user_id);
  let close;
  const body = h("div", { class: "stack", style: { gap: "var(--space-6)" } },
    h("div", { class: "stack", style: { gap: "var(--space-3)" } },
      h("div", {}, categoryBadge(expense.category)),
      h("div", { class: "drawer-amount" }, money(expense.amount, expense.currency))),
    h("dl", { class: "kv" },
      h("dt", {}, "Expense"), h("dd", {}, `#${expense.id}`),
      h("dt", {}, "User"), h("dd", {}, owner ? h("a", { href: `#/users/${owner.id}`, onclick: () => close() }, owner.name) : `User #${expense.user_id}`),
      h("dt", {}, "Spent on"), h("dd", {}, dateShort(expense.expense_date)),
      h("dt", {}, "Category"), h("dd", {}, titleCase(expense.category)),
      h("dt", {}, "Merchant"), h("dd", {}, expense.merchant || h("span", { class: "subtle" }, "Not recorded")),
      h("dt", {}, "Paid with"), h("dd", {}, paymentLabel(expense.payment_method)),
      h("dt", {}, "Recurring"), h("dd", {}, expense.is_recurring ? "Yes, repeats regularly" : "One-off"),
      h("dt", {}, "Description"), h("dd", {}, expense.description || h("span", { class: "subtle" }, "No description")),
      h("dt", {}, "Recorded"), h("dd", {}, dateTime(expense.created_at)),
      h("dt", {}, "Updated"), h("dd", {}, dateTime(expense.updated_at))));

  close = drawer({
    title: "Expense details",
    body,
    actions: [
      h("button", { class: "btn danger", onclick: async () => {
        if (!(await confirmDialog({ title: "Delete expense?", message: `Expense #${expense.id} (${money(expense.amount, expense.currency)}) will be permanently removed.`, confirmLabel: "Delete", danger: true }))) return;
        try { await del(`/expenses/${expense.id}`); toast(`Expense #${expense.id} deleted`, "success"); close(); onChange?.(); } catch (err) { toast(err.message, "error"); }
      } }, "Delete"),
      h("button", { class: "btn primary", onclick: () => { close(); openExpenseForm({ expense, onSaved: onChange }); } }, "Edit"),
    ],
  });
}
