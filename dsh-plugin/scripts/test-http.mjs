import { mkdtemp } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { Readable } from "node:stream";
import { DigestStore } from "../src/store.js";
import { createPipeline } from "../src/pipeline.js";
import { registerApi } from "../src/http.js";

const dir = await mkdtemp(path.join(os.tmpdir(), "signalforge-test-"));
const store = new DigestStore(dir);
await store.saveDigest({
	version: 1,
	date: "2026-11-04",
	timezone: "Asia/Shanghai",
	generatedAt: new Date().toISOString(),
	analysis: { model: "deepseek-flash", provider: "deepseek-account" },
	stats: { candidates: 107, okSources: 15, sources: [{ name: "arXiv", ok: true, count: 30 }] },
	signals: [{ id: "a", title: "T", url: "https://example.com", source: "arXiv", finding: "f", why_read: "w" }],
	opportunities: { business: [], rdev: [] },
});
console.log("dates", await store.listDates());

const ctx = { logger: console };
const pipeline = createPipeline({ ctx, store });
let handler;
const fakeCtx = {
	effect: (fn) => fn(),
	webServer: { register: (route) => { handler = route.handler; return () => {}; } },
};
registerApi(fakeCtx, { pipeline, store, config: {} });

async function call(method, url) {
	const req = Readable.from([]);
	req.method = method;
	req.url = url;
	const chunks = [];
	const res = {
		headersSent: false,
		writeHead(status, headers) { this.status = status; this.headers = headers; this.headersSent = true; },
		end(body) { if (body) chunks.push(Buffer.from(body)); this.body = Buffer.concat(chunks).toString("utf8"); },
	};
	await handler(req, res);
	return { status: res.status, body: JSON.parse(res.body) };
}

const boot = await call("GET", "/signalforge/api/bootstrap?date=2026-11-04");
console.log("bootstrap", boot.status, boot.body.today, boot.body.date, boot.body.digest?.signals?.length, boot.body.dates.length);
const missing = await call("GET", "/signalforge/api/digest?date=2026-11-03");
console.log("missing", missing.status, missing.body.error);
const bad = await call("POST", "/signalforge/api/jobs");
console.log("post-empty", bad.status);
