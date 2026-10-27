# Receipts reader: AI receipts-to-expenses demo (portfolio)

A public, clickable demo. A visitor uploads or snaps a photo of a receipt or tax invoice and gets back a clean expense row: vendor, date (ISO), invoice number, line items, subtotal, tax (GST, VAT or sales tax, with a CGST, SGST and IGST split for Indian invoices), total, currency, payment method, an expense category and a 0 to 1 confidence per field, plus a list of what it could not read. The page keeps a running table of the visitor's receipts in the browser (localStorage), with per-cell edit and CSV download. Every page carries the banner "Demo. Upload your own receipt or try a sample. Images are not stored. Built by Eklavya Shetty" linking to eklavyashetty.com. Four fictional sample receipts can be clicked instead of uploading.

Built by Eklavya Shetty. Style, abuse caps and fonts follow the sibling demo [ivy-enquiry-agent](https://github.com/Jabu-codes21/ivy-enquiry-agent) (Martel and Martel Sans).

## How it works
- **One Workers AI vision call reads the image**, model `@cf/google/gemma-4-26b-a4b-it` (`MODEL` in `wrangler.jsonc`). Picked from a four-model bench: see `BENCH.md`. No API keys; the `AI` binding does it.
- **Checks are plain code in `src/worker.js`, not prompt hopes** (`normalise` then `judge`):
  - line items plus tax (or tax-included prices) plus round-off must equal the total within rounding, else the flag "Totals don't add up" with the arithmetic shown;
  - the date must be a real calendar date, not in the future; a day/month-ambiguous date such as 10/04/2026 gets a note and a lower confidence;
  - CGST + SGST + IGST must equal the tax total;
  - a missing total, or an image the model says it can hardly read, means "Needs a person". For a smeared image the row is emptied rather than showing values the model may have invented;
  - category is forced into Meals, Travel, Fuel, Office supplies, Software, Materials, Utilities or Other; strings are cleaned; numbers parsed defensively; text printed on the receipt is treated as data, never as instructions.
- **Event chips** under each result show what happened (read, checked, split, flagged, added to table), as in the enquiry demo.
- **Images are never stored.** The browser shrinks the photo (long edge at most 1600 px, under 1.5 MB, JPEG), the Worker checks size (4 MB hard limit) and file signature, base64s it into the model call, and drops it. The only server state is the anonymous daily counter, keyed by one-way daily hashes of the cookie and IP, which reset every midnight IST.

## Abuse limits (it is public, so they live inside the Worker)
| Limit | Default | Var |
|---|---|---|
| Receipts per visitor per day (cookie `rr_vid`, else IP) | 10 | `VISITOR_DAILY_MAX` |
| Receipts per IP per day (backstop for cookie clearing) | 30 | `IP_DAILY_MAX` |
| Receipts per day, all visitors | 400 | `GLOBAL_DAILY_MAX` |
| Image size, server side | 4 MB | `MAX_IMAGE_BYTES` |

Counters live in a small Durable Object (`Counter`). Over a cap the Worker returns a fixed polite message (HTTP 429) and does not call the model. If the model call fails, the receipt is given back to the visitor's count. Header `x-owner-key` equal to the `OWNER_KEY` secret bypasses the three counters (not the size limit) and lets the owner pick a model with `x-model` and see the raw model text, which is how the bench runs. If `OWNER_KEY` is unset, nobody is the owner.

## Run it locally
```
npm install
copy .dev.vars.example .dev.vars      (set OWNER_KEY to any local value; git-ignored)
npx wrangler dev --port 8812          (page at http://127.0.0.1:8812/)
```
Workers AI is always remote, even in `wrangler dev`: you must be logged in (`npx wrangler login`) and it uses a little of the account's allocation. With several Cloudflare accounts, set `CLOUDFLARE_ACCOUNT_ID=8f5947a7b20b2cad2137ae8d9b187094` first. Nothing here was run with `--remote`.

## Tests
- `python test/make_receipts.py` rebuilds the 12 synthetic receipts (HTML to PNG with headless Edge, then Pillow degradation) and their ground truth in `test/truth/`. All businesses and tax numbers are fictional.
- `node test/run-tests.mjs accuracy` scores field-level accuracy (vendor, date, total, tax, currency), the wrong-total and blurry cases, a non-receipt, an injection attempt and the 4 MB reject. Needs the dev server on 8812 with default limits and an owner key in `.dev.vars`.
- `node test/run-tests.mjs caps` checks all three caps, the owner bypass and the size reject. Start the server with tiny limits first:
  `npx wrangler dev --port 8812 --var VISITOR_DAILY_MAX:3 --var IP_DAILY_MAX:4 --var GLOBAL_DAILY_MAX:8` (delete `.wrangler/state/v3/do` first for a clean counter).
- `node test/bench.mjs <model> ...` benchmarks models through the Worker; `node test/make-reports.mjs` rewrites `BENCH.md` and `TEST-REPORT.md` from the saved results.
- Results: `TEST-REPORT.md`, `BENCH.md`.

## Deploy (done 2026-10-27; redeploy the same way)
```
npx wrangler deploy
printf '%s' "$(cat .owner-key)" | npx wrangler secret put OWNER_KEY      (Git Bash; never pipe from PowerShell, it adds a CRLF)
```
`wrangler.jsonc` already names the Worker `receipts-reader-demo`, turns `workers_dev` on and declares the custom domain `receipts.allforone.co.in`, so the first deploy will also create that DNS record on the account's zone. Remove the `routes` line if you would rather start on the workers.dev address only. The CSP lets eklavyashetty.com and its subdomains embed the page in an iframe.

## Files
- `src/worker.js`: the reader, the checks, the `Counter` Durable Object, limits and router
- `public/index.html`: the whole UI (upload, camera, samples, result slip, table, CSV)
- `public/samples/`: the four built-in samples (copies of files from `test/receipts/`)
- `test/`: generators, 12 test receipts and truth, bench and test scripts, saved results
- `BENCH.md`, `TEST-REPORT.md`, `wrangler.jsonc`, `.gitignore`, `.dev.vars.example`

## Things to know
- A vision model can misread a line item. The totals check catches most of these and marks the row "Check" instead of passing a silent error (this happened once in testing on a taxi receipt). It cannot catch a wrong number that still adds up.
- Dates printed as 03/04/2026 cannot be settled by the paper alone. The reader uses the currency to choose the order and flags the ambiguity as a note.
- The table is per browser. It is not synced and disappears if the visitor clears site data.
- Receipts a visitor uploads do go to Cloudflare Workers AI for reading; the footer asks people not to upload anything sensitive.

## Live (2026-10-27 19:05 IST)
- https://receipts.allforone.co.in, also https://receipts-reader-demo.afoaofa.workers.dev.
- Cloudflare account 8f5947a7… (same as agent. and eklavyashetty.com). Version e70b38a3.
- OWNER_KEY is set as a Worker secret. The local copy is in `.owner-key` (gitignored, never print it). Send it as header `x-owner-key` to skip the caps.
- Live check: the in-gst sample read correctly as a visitor (8.1 s), and mismatch.jpg was flagged "Totals don't add up" plus the ambiguous-date note.
