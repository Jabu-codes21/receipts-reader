// node run-tests.mjs accuracy [base]   full accuracy pass + extras (needs the dev server with default limits)
// node run-tests.mjs caps [base]       abuse caps; start the dev server first with tiny limits (command in the README)
import fs from "node:fs";
import path from "node:path";
import { IDS, HERE, truth, img, read, score, CORE, OWNER } from "./lib.mjs";
const [mode = "accuracy", base = "http://127.0.0.1:8812"] = process.argv.slice(2);
const save = (n, o) => fs.writeFileSync(path.join(HERE, n), JSON.stringify(o, null, 1));
const extra = (n) => fs.readFileSync(path.join(HERE, "extra", n));

if (mode === "accuracy") {
  const out = { at: new Date().toISOString(), receipts: {}, extras: {} };
  for (const id of IDS) {
    const t = truth(id), r = await read(base, id), s = r.ok ? score(t, r) : null;
    let pass, why = "";
    if (!r.ok) { pass = t.expect.unreadable ? r.error === "not_receipt" || r.status === 422 : false; why = `call failed: ${r.error || r.status} ${r.message || ""}`; }
    else if (t.expect.totals_mismatch) { pass = s.flagMismatch; why = pass ? "flagged totals don't add up" : "mismatch NOT flagged"; }
    else if (t.expect.unreadable) { pass = s.needsPerson; why = pass ? "marked needs a person" : `not flagged (status ${r.status})`; }
    else { const bad = CORE.filter((k) => !s[k]); pass = !bad.length && r.status === "ok"; why = bad.length ? "wrong: " + bad.join(", ") : r.status !== "ok" ? `false flag: ${(r.flags || []).map((f) => f.code).join(",")}` : ""; }
    out.receipts[id] = { pass, why, ms: r.ms, status: r.status, score: s, flags: (r.flags || []).map((f) => f.text), row: r.row, confidence: r.confidence, unreadable: r.unreadable, raw: pass ? undefined : r.raw };
    console.log(pass ? "PASS" : "FAIL", id.padEnd(10), why, r.ms + "ms");
  }
  const X = out.extras;
  let r = await read(base, null, { body: extra("not-a-receipt.jpg") });
  X.notReceipt = { pass: r.status === 422 && r.error === "not_receipt", detail: `${r.status} ${r.error}` };
  r = await read(base, null, { body: extra("injection.jpg") });
  X.injection = { pass: r.ok && r.row.vendor?.includes("Tin Roof") && r.row.total === 35.1 && r.row.category === "Meals", detail: r.ok ? `vendor=${r.row.vendor} total=${r.row.total} category=${r.row.category}` : `${r.status} ${r.error}` };
  r = await read(base, null, { body: extra("too-big.jpg"), owner: false });
  X.tooBig = { pass: r.status === 413 && r.ms < 3000, detail: `${r.status} ${r.error} in ${r.ms} ms` };
  r = await read(base, null, { body: extra("too-big.jpg") });
  X.tooBigOwner = { pass: r.status === 413, detail: `owner key does not bypass the size limit: ${r.status}` };
  r = await read(base, null, { body: extra("not-an-image.jpg"), owner: false });
  X.badType = { pass: r.status === 415, detail: `${r.status} ${r.error}` };
  r = await read(base, null, { body: Buffer.alloc(0), owner: false });
  X.empty = { pass: r.status === 400, detail: `${r.status} ${r.error}` };
  for (const [k, v] of Object.entries(X)) console.log(v.pass ? "PASS" : "FAIL", k, v.detail);
  save("accuracy-results.json", out);
}

if (mode === "caps") {
  const res = [];
  const ok = (name, pass, detail) => { res.push({ name, pass, detail }); console.log(pass ? "PASS" : "FAIL", name, detail); };
  const call = async (cookie, ip, body = img("au-cafe")) => { const t0 = Date.now(); const r = await fetch(base + "/api/read", { method: "POST", headers: { "content-type": "image/jpeg", cookie: "rr_vid=" + cookie, "cf-connecting-ip": ip }, body }); const j = await r.json().catch(() => ({})); return { status: r.status, ms: Date.now() - t0, ...j }; };
  const ck = (c) => c.repeat(16).slice(0, 16);
  // size and type rejects happen before anything is counted
  let r = await call(ck("a"), "198.51.100.1", extra("too-big.jpg")); ok("4 MB reject (413, no model call, not counted)", r.status === 413 && r.ms < 3000, `${r.status} ${r.error} in ${r.ms} ms`);
  r = await call(ck("a"), "198.51.100.1", extra("not-an-image.jpg")); ok("non-image rejected (415, not counted)", r.status === 415, `${r.status}`);
  // IP backstop (cap 4): fresh cookie each time from one IP; cookie-clearing must not help
  let n = 0, hit = null;
  for (let i = 0; i < 6 && !hit; i++) { r = await call(ck("b" + i), "203.0.113.9"); n++; if (r.status === 429) hit = r; }
  ok("per-IP cap beats cookie clearing", hit?.limited === "ip" && n === 5 && hit.ms < 1500, `refused on call ${n}, limited=${hit?.limited}, ${hit?.ms} ms`);
  // per-visitor cap (3): same cookie, different IPs
  const v = []; for (let i = 0; i < 4; i++) v.push(await call(ck("c"), "192.0.2." + (10 + i)));
  ok("per-visitor daily cap (cookie)", v.slice(0, 3).every((x) => x.ok) && v[3].status === 429 && v[3].limited === "visitor" && v[3].ms < 1500, `calls 1-3 ok, 4th: ${v[3].status} limited=${v[3].limited} in ${v[3].ms} ms; left after 1st=${v[0].left}`);
  ok("refusal text is the fixed polite message", /limit for this demo/.test(v[3].message || ""), `"${(v[3].message || "").slice(0, 90)}"`);
  // other visitor unaffected (global used so far: 4 + 3 = 7 of 8)
  r = await call(ck("d"), "192.0.2.50"); ok("a different visitor is unaffected", r.ok, `status ${r.status} left=${r.left}`);
  // global cap (8): now exhausted for everyone, fast, no model
  const g1 = await call(ck("e"), "192.0.2.60"), g2 = await call(ck("f"), "192.0.2.61");
  ok("global daily cap refuses everyone without calling the model", g1.limited === "global" && g2.limited === "global" && g1.ms < 1500 && g2.ms < 1500, `limited=${g1.limited}/${g2.limited} in ${g1.ms}/${g2.ms} ms`);
  // owner key bypass
  const o = await read(base, "au-cafe"); ok("OWNER_KEY bypasses the caps", o.ok, `status ${o.status}`);
  const bad = await fetch(base + "/api/read", { method: "POST", headers: { "content-type": "image/jpeg", "x-owner-key": "wrong", cookie: "rr_vid=" + ck("g"), "cf-connecting-ip": "192.0.2.70" }, body: img("au-cafe") }).then((x) => x.status);
  ok("wrong owner key does not bypass", bad === 429, `status ${bad}`);
  const nomodel = await fetch(base + "/api/read", { method: "POST", headers: { "content-type": "image/jpeg", "x-model": "@cf/meta/llama-4-scout-17b-16e-instruct", cookie: "rr_vid=" + ck("g"), "cf-connecting-ip": "192.0.2.71" }, body: img("au-cafe") }).then((x) => x.status);
  ok("x-model override ignored without owner key", nomodel === 429, `status ${nomodel} (refused by cap, model not chosen by visitor)`);
  save("caps-results.json", res);
  console.log(`\n${res.filter((x) => x.pass).length}/${res.length} cap checks passed`);
}
