// Benchmarks vision models through the local Worker (owner key + x-model override). node bench.mjs <model> [<model>...]
import fs from "node:fs";
import path from "node:path";
import { IDS, HERE, truth, read, score, CORE } from "./lib.mjs";
const base = "http://127.0.0.1:8812";
const models = process.argv.slice(2);
fs.mkdirSync(path.join(HERE, "bench-raw"), { recursive: true });
const all = fs.existsSync(path.join(HERE, "bench-results.json")) ? JSON.parse(fs.readFileSync(path.join(HERE, "bench-results.json"), "utf8")) : {};
for (const model of models) {
  const res = {};
  for (const id of IDS) {
    const t = truth(id), r = await read(base, id, { model });
    fs.writeFileSync(path.join(HERE, "bench-raw", `${model.split("/").pop()}__${id}.json`), JSON.stringify(r, null, 1));
    const s = r.ok ? score(t, r) : null;
    res[id] = { ok: !!r.ok, status: r.status, ms: r.ms, flagsStatus: r.status, score: s, err: r.ok ? null : (r.detail || r.message || r.error), unflag: r.ok ? (r.flags || []).map((f) => f.code) : null };
    console.log(model.split("/").pop(), id.padEnd(9), r.ok ? CORE.map((k) => (s[k] ? "Y" : "n")).join("") + ` inv:${s.invoice ? "Y" : "n"} cat:${s.category ? "Y" : "n"} items:${s.items ? "Y" : "n"} st:${r.status} flags:${(r.flags || []).map((f) => f.code).join(",")}` : "FAIL " + String(r.detail || r.message).slice(0, 160), r.ms + "ms");
  }
  all[model] = res; fs.writeFileSync(path.join(HERE, "bench-results.json"), JSON.stringify(all, null, 1));
}
