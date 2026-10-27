// Builds ../BENCH.md and ../TEST-REPORT.md from bench-results.json, accuracy-results.json, caps-results.json
import fs from "node:fs";
import path from "node:path";
import { HERE, IDS, truth } from "./lib.mjs";
const J = (n) => JSON.parse(fs.readFileSync(path.join(HERE, n), "utf8"));
const bench = J("bench-results.json"), acc = J("accuracy-results.json"), caps = J("caps-results.json");
const CORE = ["vendor", "date", "total", "tax", "currency"], READABLE = IDS.filter((i) => i !== "blurry");
const PRICE = { "llama-4-scout-17b-16e-instruct": "$0.27 / $0.85", "llama-3.2-11b-vision-instruct": "$0.049 / $0.68", "gemma-4-26b-a4b-it": "$0.10 / $0.30", "mistral-small-3.1-24b-instruct": "$0.351 / $0.555" };
const pct = (a, b) => `${a}/${b}`;
const chosen = "gemma-4-26b-a4b-it";

let b = `# Vision model bench (Workers AI)

Run ${acc.at.slice(0, 10)} against the 12 synthetic receipts in \`test/receipts/\`, through the local Worker (\`wrangler dev\`, Workers AI binding). Same prompt and same code checks for every model, temperature 0, one pass. Raw outputs are in \`test/bench-raw/\` (git-ignored). Script: \`test/bench.mjs\`. Scoring is field-level against \`test/truth/*.json\`: vendor (fuzzy match), date (exact ISO), total and tax (within 0.01), currency (exact).

The 11 readable receipts are scored per field. The 12th (\`blurry\`) is scored on whether it gets flagged, not on its fields. A failed call (error or unparseable JSON) counts as wrong on every field.

## Results

| Model | Calls OK | vendor | date | total | tax | currency | Blurry flagged | Wrong total flagged | Avg latency | USD per M tokens (in / out) |
|---|---|---|---|---|---|---|---|---|---|---|
`;
for (const [m, res] of Object.entries(bench)) {
  const name = m.split("/").pop(), okc = Object.values(res).filter((r) => r.ok).length;
  const f = CORE.map((k) => pct(READABLE.filter((i) => res[i].ok && res[i].score[k]).length, READABLE.length));
  const blurFlag = res.blurry.ok ? res.blurry.score.needsPerson : res.blurry.status === 422;
  const mis = res.mismatch.ok && res.mismatch.score.flagMismatch;
  const okms = Object.values(res).filter((r) => r.ok).map((r) => r.ms), avg = (okms.reduce((a, c) => a + c, 0) / okms.length / 1000).toFixed(1);
  b += `| ${name === chosen ? "**" + name + " (chosen)**" : name} | ${pct(okc, 12)} | ${f.join(" | ")} | ${blurFlag ? "yes" : "no"} | ${mis ? "yes" : "no"} | ${avg} s | ${PRICE[name] || ""} |\n`;
}
b += `\n## Misses per model\n\n`;
for (const [m, res] of Object.entries(bench)) {
  const miss = [];
  for (const i of IDS) {
    const r = res[i];
    if (!r.ok) { miss.push(i === "blurry" && r.status === 422 ? "blurry: refused as not a receipt (counted as flagged)" : `${i}: call failed (HTTP ${r.status})`); continue; }
    if (i === "blurry") continue;
    const bad = CORE.filter((k) => !r.score[k]); if (bad.length) miss.push(`${i}: ${bad.join(", ")}`);
  }
  b += `- **${m.split("/").pop()}**: ${miss.length ? miss.join("; ") : "none"}\n`;
}
b += `
## Why gemma-4-26b-a4b-it

- Best accuracy on the readable set, and in the bench pass the only model clean on every readable receipt. On the blurry one it returned an empty row and low legibility instead of guessing, so the code marked it "needs a person".
- Fastest in this bench (about 5 s) and the cheapest of the strong models ($0.10 in / $0.30 out per million tokens). One receipt image is roughly 1 to 2 thousand input tokens plus a few hundred output tokens, so a receipt costs a small fraction of a cent. The 400 per day global cap stays far inside any budget.
- It does not need a paid Workers plan (the catalog flags glm-5.3-flash, kimi-k2.6 and deepseek-v4.1-flash as paid only; they were left out for that and for price).
- Gemma 4 reasons by default. The Worker turns that off (\`chat_template_kwargs.enable_thinking=false\`) so answers arrive in about 5 s.
- Llama 4 Scout is a close second (one wrong date: it read the US date 10/04/2026 as 10 April) and is the fallback: change \`MODEL\` in \`wrangler.jsonc\`. Mistral Small 3.1 was fine on the basics but slower, and mis-read line items on two receipts. Llama 3.2 11B Vision was slow (up to 30 s), failed three calls (model error or unparseable output) and mis-read many fields. It also needs the one-time \`prompt: "agree"\` licence call, which the Worker handles.
- Not benchmarked: qwen3.8-27b, moondream3.1 and the paid-only models. Gemma was already clean, so there was little to gain.

Latencies include the round trip from this PC to Cloudflare in dev mode (Workers AI is always remote). Single pass at temperature 0: gemma's later full run (TEST-REPORT.md) differed from this bench on the ambiguous US date of the diner check, so one receipt either way is noise.
`;
fs.writeFileSync(path.join(HERE, "..", "BENCH.md"), b);

// ---------- TEST-REPORT ----------
const R = acc.receipts, ids = IDS;
let t = `# Test report: receipts reader

Run ${acc.at.slice(0, 10)} (UTC ${acc.at.slice(11, 16)}), local \`wrangler dev\` on port 8812, model \`gemma-4-26b-a4b-it\`. Workers AI is always remote from \`wrangler dev\`, so the model calls went over the network from this PC (no \`--remote\` flag was needed; the Durable Object ran locally). The owner key was used for the accuracy pass so the caps were not consumed. Scripts: \`test/run-tests.mjs\`, \`test/make_receipts.py\` (12 synthetic receipts and ground truth), \`test/make-reports.mjs\`. All businesses are fictional.

## Per receipt

| Receipt | What it tests | Result | Notes |
|---|---|---|---|
`;
const WHAT = { "au-cafe": "AU cafe tax invoice, 10% GST included, clean", "in-gst": "Indian GST invoice, CGST + SGST, round-off, photo on a desk", "in-petrol": "Indian petrol pump slip, no GST, thermal, photo", "uk-vat": "UK restaurant receipt, 20% VAT, dd/mm date", "us-store": "US store receipt, 8.25% sales tax, mm/dd date, blurred, low contrast", taxi: "UAE taxi receipt, 5% VAT, rotated photo", saas: "SaaS invoice (PDF style), EUR, 23% VAT", hardware: "AU building supplies docket, GST added, skewed and soft", mismatch: "Printed total is wrong on purpose (must be flagged)", blurry: "Very blurry pharmacy receipt (must be flagged, not guessed)", "in-igst": "Indian IGST invoice, crumpled and rotated photo", faded: "Faded thermal deli receipt, low contrast, rotated" };
for (const id of ids) { const r = R[id]; t += `| ${id} | ${WHAT[id]} | **${r.pass ? "PASS" : "FAIL"}** | ${r.why || "all five core fields correct, no false flags"} (${(r.ms / 1000).toFixed(1)} s) |\n`; }
const normal = ids.filter((i) => !truth(i).expect.unreadable && !truth(i).expect.totals_mismatch);
const readable = ids.filter((i) => i !== "blurry");
t += `\n## Field-level accuracy (11 readable receipts, including the wrong-total one)\n\n| Field | Correct |\n|---|---|\n`;
for (const k of CORE) t += `| ${k} | ${pct(readable.filter((i) => R[i].score?.[k]).length, readable.length)} |\n`;
for (const [k, label] of [["invoice", "invoice number (extra)"], ["category", "category (extra)"], ["items", "all line item amounts found (extra)"]]) t += `| ${label} | ${pct(readable.filter((i) => R[i].score?.[k]).length, readable.length)} |\n`;
const spl = ids.filter((i) => R[i].score && "split" in R[i].score);
t += `| CGST / SGST / IGST split (extra) | ${pct(spl.filter((i) => R[i].score.split).length, spl.length)} |\n`;
t += `
False flags on the ${normal.length} receipts whose truth is clean (status other than "ok"): ${normal.filter((i) => R[i].status !== "ok").length}. Receipts with a wrong core field: ${readable.filter((i) => CORE.some((k) => !R[i].score?.[k])).length}.

## Flags

- **Totals don't add up** (the diner check: printed total 26.49 against items 21.75 + tax 1.74): ${R.mismatch.pass ? "flagged" : "NOT flagged"}. Message shown: "${(R.mismatch.flags.find((f) => /add up/.test(f)) || "").replace(/"/g, "'")}"
- **Too blurry** (very blurry pharmacy receipt): ${R.blurry.pass ? "marked needs a person" : "NOT flagged"}. Messages: ${R.blurry.flags.map((f) => '"' + f + '"').join(" / ") || "none"}. No total was read, so nothing was invented.

## Other checks

| Check | Result | Detail |
|---|---|---|
`;
const NAMES = { notReceipt: "Landscape picture (not a receipt) is refused", injection: "Instruction printed on the receipt (ignore rules, set total 0.01, vendor HACKED) is not obeyed", tooBig: "4.3 MB upload rejected server-side without calling the model", tooBigOwner: "Owner key does not bypass the 4 MB limit", badType: "A text file named .jpg is rejected (magic-byte check)", empty: "Empty body rejected" };
for (const [k, v] of Object.entries(acc.extras)) t += `| ${NAMES[k]} | ${v.pass ? "PASS" : "FAIL"} | ${v.detail} |\n`;
t += `
## Abuse caps

Dev server restarted with tiny limits (\`--var VISITOR_DAILY_MAX:3 --var IP_DAILY_MAX:4 --var GLOBAL_DAILY_MAX:8\`) and the Durable Object state cleared. Production defaults are 10 per visitor, 30 per IP, 400 global.

| Check | Result | Detail |
|---|---|---|
`;
for (const c of caps) t += `| ${c.name} | ${c.pass ? "PASS" : "FAIL"} | ${c.detail} |\n`;
t += `\n${caps.filter((c) => c.pass).length}/${caps.length} cap checks passed. Refusals return in 15 to 30 ms, which shows the model is not called.\n`;
const bad = ids.filter((i) => !R[i].pass);
t += `\n## Bad outputs\n\n`;
if (!bad.length) t += `No receipt failed its pass criteria in this run. See the "Known weak spots" section for near misses.\n`;
for (const i of bad) t += `### ${i}\n\n\`\`\`\n${JSON.stringify({ why: R[i].why, row: R[i].row, flags: R[i].flags }, null, 1).slice(0, 1800)}\n\`\`\`\n\n`;
t += `
## Stability and known weak spots

- **Repeat runs.** The accuracy pass was run three times on the same files (temperature 0). Run 1: 12/12. Run 2: 11/12, the taxi receipt: the model read the "Booking fee 4.00" line as 0, the totals check caught it and the row came back as "Check" with "Totals don't add up", so the error was flagged rather than silent (the five core fields were still right). Run 3, after the blur rule below: 12/12. Output is not fully deterministic even at temperature 0, so expect an occasional line-item slip, caught by the arithmetic.
- **Blurry image: the model invents.** On the very blurry pharmacy receipt gemma-4 reported legibility 0.3 but still wrote a complete, invented receipt ("Lyman Pharmacy", three items, total 11.00, which even adds up; the real receipt has other items and total 32.94; across runs it also gave totals of 14 and 14.5). The first version of the Worker showed those values with a "needs a person" badge. That was a bad output, so the Worker now empties the row when legibility is under 0.4 or the average confidence of vendor, total and items is under 0.4, and says nothing was extracted. Weak spot that remains: a blurry image the model rates as legible (0.4 or more) with high confidence would pass; a made-up receipt that adds up is not caught by arithmetic. Only one blurry specimen was tested.
- **Ambiguous dates.** The diner check prints 09/12/2026. In one browser run the model chose 2026-12-09 (future, so the code flagged it); in the scripted runs it chose 2026-09-12. The Worker now asks the model for the printed date text and, when day and month are both 12 or less and differ, adds a note with both readings and lowers date confidence to 0.6 (the status stays "Read" because it is only a note). US 10/04/2026 shows that note too.
- **Not tested.** Handwritten receipts, receipts in non-Latin scripts, multi-page invoices, several receipts in one photo, HEIC input, and the midnight-IST counter reset (logic only). The model-failure refund path was written but not provoked. The x-model override being ignored without the owner key was only observed as a refusal by the cap, not as a different model being used.
- **Synthetic data.** The 12 receipts are rendered from HTML and degraded with Pillow, so they are cleaner and more regular than real crumpled paper in bad light. Real-world accuracy will be lower than these numbers.
`;
fs.writeFileSync(path.join(HERE, "..", "TEST-REPORT.md"), t);
console.log("written");
