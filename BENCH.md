# Vision model bench (Workers AI)

Run 2026-10-27 against the 12 synthetic receipts in `test/receipts/`, through the local Worker (`wrangler dev`, Workers AI binding). Same prompt and same code checks for every model, temperature 0, one pass. Raw outputs are in `test/bench-raw/` (git-ignored). Script: `test/bench.mjs`. Scoring is field-level against `test/truth/*.json`: vendor (fuzzy match), date (exact ISO), total and tax (within 0.01), currency (exact).

The 11 readable receipts are scored per field. The 12th (`blurry`) is scored on whether it gets flagged, not on its fields. A failed call (error or unparseable JSON) counts as wrong on every field.

## Results

| Model | Calls OK | vendor | date | total | tax | currency | Blurry flagged | Wrong total flagged | Avg latency | USD per M tokens (in / out) |
|---|---|---|---|---|---|---|---|---|---|---|
| llama-4-scout-17b-16e-instruct | 11/12 | 11/11 | 10/11 | 11/11 | 11/11 | 11/11 | yes | yes | 5.6 s | $0.27 / $0.85 |
| llama-3.2-11b-vision-instruct | 9/12 | 5/11 | 5/11 | 6/11 | 6/11 | 8/11 | yes | no | 13.4 s | $0.049 / $0.68 |
| **gemma-4-26b-a4b-it (chosen)** | 12/12 | 11/11 | 11/11 | 11/11 | 11/11 | 11/11 | yes | yes | 4.9 s | $0.10 / $0.30 |
| mistral-small-3.1-24b-instruct | 12/12 | 11/11 | 10/11 | 11/11 | 11/11 | 11/11 | yes | yes | 8.5 s | $0.351 / $0.555 |

## Misses per model

- **llama-4-scout-17b-16e-instruct**: us-store: date; blurry: refused as not a receipt (counted as flagged)
- **llama-3.2-11b-vision-instruct**: au-cafe: date; in-gst: vendor, total, tax; in-petrol: vendor, date; us-store: vendor; taxi: tax; saas: call failed (HTTP 503); hardware: call failed (HTTP 503); mismatch: total; in-igst: call failed (HTTP 503); faded: date
- **gemma-4-26b-a4b-it**: none
- **mistral-small-3.1-24b-instruct**: us-store: date

## Why gemma-4-26b-a4b-it

- Best accuracy on the readable set, and in the bench pass the only model clean on every readable receipt. On the blurry one it returned an empty row and low legibility instead of guessing, so the code marked it "needs a person".
- Fastest in this bench (about 5 s) and the cheapest of the strong models ($0.10 in / $0.30 out per million tokens). One receipt image is roughly 1 to 2 thousand input tokens plus a few hundred output tokens, so a receipt costs a small fraction of a cent. The 400 per day global cap stays far inside any budget.
- It does not need a paid Workers plan (the catalog flags glm-5.3-flash, kimi-k2.6 and deepseek-v4.1-flash as paid only; they were left out for that and for price).
- Gemma 4 reasons by default. The Worker turns that off (`chat_template_kwargs.enable_thinking=false`) so answers arrive in about 5 s.
- Llama 4 Scout is a close second (one wrong date: it read the US date 10/04/2026 as 10 April) and is the fallback: change `MODEL` in `wrangler.jsonc`. Mistral Small 3.1 was fine on the basics but slower, and mis-read line items on two receipts. Llama 3.2 11B Vision was slow (up to 30 s), failed three calls (model error or unparseable output) and mis-read many fields. It also needs the one-time `prompt: "agree"` licence call, which the Worker handles.
- Not benchmarked: qwen3.8-27b, moondream3.1 and the paid-only models. Gemma was already clean, so there was little to gain.

Latencies include the round trip from this PC to Cloudflare in dev mode (Workers AI is always remote). Single pass at temperature 0: gemma's later full run (TEST-REPORT.md) differed from this bench on the ambiguous US date of the diner check, so one receipt either way is noise.
