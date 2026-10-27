import { read } from "./lib.mjs";
const [id, model] = process.argv.slice(2);
const r = await read("http://127.0.0.1:8812", id, { model });
console.log(JSON.stringify(r, null, 1).slice(0, 5000));
