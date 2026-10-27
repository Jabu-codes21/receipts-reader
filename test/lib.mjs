// shared helpers for bench.mjs and run-tests.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
export const HERE = path.dirname(fileURLToPath(import.meta.url));
export const IDS = ["au-cafe", "in-gst", "in-petrol", "uk-vat", "us-store", "taxi", "saas", "hardware", "mismatch", "blurry", "in-igst", "faded"];
export const truth = (id) => JSON.parse(fs.readFileSync(path.join(HERE, "truth", id + ".json"), "utf8"));
export const img = (id) => fs.readFileSync(path.join(HERE, "receipts", id + ".jpg"));
export const OWNER = fs.readFileSync(path.join(HERE, "..", ".dev.vars"), "utf8").match(/OWNER_KEY=(.*)/)[1].trim();

export async function read(base, id, { model, owner = true, headers = {}, body } = {}) {
  const h = { "content-type": "image/jpeg", ...headers };
  if (owner) h["x-owner-key"] = OWNER;
  if (model) h["x-model"] = model;
  const t0 = Date.now();
  const r = await fetch(base + "/api/read", { method: "POST", headers: h, body: body ?? img(id) });
  const j = await r.json().catch(() => ({}));
  return { status: r.status, ms: Date.now() - t0, ...j };
}

const norm = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
export function vendorOk(a, b) {
  a = norm(a); b = norm(b); if (!a || !b) return false;
  if (a.includes(b) || b.includes(a)) return true;
  const ta = new Set(a.split(" ")), tb = b.split(" ");
  return tb.filter((w) => ta.has(w)).length / tb.length >= 0.6;
}
const near = (a, b) => a != null && b != null && Math.abs(a - b) <= 0.011;
export function score(t, r) {
  const row = r.row || {};
  const taxP = row.tax?.total ?? null, taxT = t.tax ?? null;
  const out = {
    vendor: vendorOk(row.vendor, t.vendor),
    date: row.date === t.date,
    total: near(row.total, t.total),
    tax: (taxT == null || taxT === 0) ? (taxP == null || taxP === 0) : near(taxP, taxT),
    currency: row.currency === t.currency,
    // extras
    invoice: norm(row.invoice_number) === norm(t.invoice_number) || (norm(row.invoice_number) && norm(t.invoice_number).includes(norm(row.invoice_number))),
    category: row.category === t.category,
    items: (row.items || []).length === t.items.length && t.items.every((ti) => (row.items || []).some((pi) => near(pi.amount, ti.amount))),
  };
  if (t.tax_split) out.split = Object.entries(t.tax_split).every(([k, v]) => near(row.tax?.[k], v));
  const codes = (r.flags || []).map((f) => f.code);
  out.flagMismatch = codes.includes("totals_mismatch");
  out.needsPerson = r.status === "needs_person";
  return out;
}
export const CORE = ["vendor", "date", "total", "tax", "currency"];
