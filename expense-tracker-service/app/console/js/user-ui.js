// User create/edit form and delete flow (shared by the Users pages).

import { ApiError, del, invalidateUsers, patch, post } from "./api.js";
import { COUNTRY_CODES, countryName } from "./format.js";
import { shared } from "./shared.js";
import { h, modal, toast, confirmDialog } from "./ui.js";

export async function openUserForm({ user = null, onSaved } = {}) {
  const editing = Boolean(user);
  const name = h("input", { class: "input", name: "name", value: user?.name || "", maxlength: "100", placeholder: "Full name", required: true });
  const country = h("select", { class: "select", name: "country" },
    h("option", { value: "" }, "Not set"),
    COUNTRY_CODES.slice().sort((a, b) => countryName(a).localeCompare(countryName(b))).map((c) => h("option", { value: c, selected: c === user?.country }, `${countryName(c)} (${c})`)));
  const city = h("input", { class: "input", name: "city", value: user?.city || "", maxlength: "80", placeholder: "e.g. Pune", autocomplete: "off" });
  const currency = h("input", { class: "input", name: "default_currency", list: "user-currency-list", maxlength: "3", value: user?.default_currency || shared.currencies[0] || "INR", style: { "text-transform": "uppercase" } });
  const budget = h("input", { class: "input", name: "monthly_budget", inputmode: "decimal", placeholder: "No budget", value: user?.monthly_budget || "", autocomplete: "off" });
  const errors = Object.fromEntries(["name", "country", "city", "default_currency", "monthly_budget"].map((k) => [k, h("span", { class: "field-error" })]));
  const controls = { name, country, city, default_currency: currency, monthly_budget: budget };
  const save = h("button", { class: "btn primary", type: "button" }, editing ? "Save changes" : "Create user");
  let close;

  async function submit(e) {
    e?.preventDefault();
    for (const key of Object.keys(errors)) { errors[key].textContent = ""; controls[key].removeAttribute("aria-invalid"); }
    save.disabled = true;
    const body = { name: name.value, country: country.value || null, city: city.value.trim() || null, default_currency: currency.value.trim(), monthly_budget: budget.value.trim() || null };
    try {
      const saved = editing ? await patch(`/users/${user.id}`, body) : await post("/users", body);
      invalidateUsers();
      toast(editing ? "User updated" : `${saved.name} added`, "success");
      close();
      onSaved?.(saved);
    } catch (err) {
      if (err instanceof ApiError && Array.isArray(err.details)) {
        for (const d of err.details) {
          const key = d.location.split(".").pop();
          if (errors[key]) { errors[key].textContent = d.message; controls[key].setAttribute("aria-invalid", "true"); }
        }
      } else toast(err.message, "error");
    } finally {
      save.disabled = false;
    }
  }

  const form = h("form", { class: "stack", onsubmit: submit, novalidate: true },
    h("label", { class: "field" }, h("span", { class: "label" }, "Name"), name, errors.name),
    h("div", { class: "form-grid" },
      h("label", { class: "field" }, h("span", { class: "label" }, "Country"), country, errors.country),
      h("label", { class: "field" }, h("span", { class: "label" }, "City"), city, errors.city)),
    h("div", { class: "form-grid" },
      h("label", { class: "field" }, h("span", { class: "label" }, "Default currency"), currency, errors.default_currency),
      h("label", { class: "field" }, h("span", { class: "label" }, "Monthly budget (optional)"), budget, errors.monthly_budget)),
    h("datalist", { id: "user-currency-list" }, ["INR", "USD", "EUR", "GBP", "AED", "SGD", "AUD", "CAD", "BRL", ...shared.currencies].map((c) => h("option", { value: c }))));
  close = modal({
    title: editing ? "Edit user" : "New user",
    body: form,
    actions: [h("button", { class: "btn", type: "button", onclick: () => close() }, "Cancel"), save],
  });
  save.addEventListener("click", submit);
}

/** Delete a user. If they still have expenses the API answers 409; we then offer a cascade. */
export async function deleteUserFlow(user, onDone) {
  if (!(await confirmDialog({ title: `Delete ${user.name}?`, message: "This user will be permanently removed.", confirmLabel: "Delete", danger: true }))) return;
  try {
    await del(`/users/${user.id}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 409) {
      const count = err.details?.expense_count ?? "their";
      const cascade = await confirmDialog({ title: "Also delete their expenses?", message: `${user.name} still has ${count} expense(s). Deleting will permanently remove the user AND all of those expenses.`, confirmLabel: "Delete everything", danger: true });
      if (!cascade) return;
      try { await del(`/users/${user.id}`, { delete_expenses: true }); } catch (e2) { toast(e2.message, "error"); return; }
    } else { toast(err.message, "error"); return; }
  }
  invalidateUsers();
  toast(`${user.name} deleted`, "success");
  onDone?.();
}
