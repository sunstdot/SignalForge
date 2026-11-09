import { isDate } from "./util.js";

const PREFIX = "/signalforge/api";

function sendJson(res, status, value) {
	const body = Buffer.from(JSON.stringify(value));
	res.writeHead(status, {
		"content-type": "application/json; charset=utf-8",
		"content-length": String(body.length),
		"cache-control": "no-store",
		"x-content-type-options": "nosniff",
	});
	res.end(body);
}

async function readJsonBody(req) {
	const chunks = [];
	let size = 0;
	for await (const chunk of req) {
		size += chunk.length;
		if (size > 16384) throw new Error("请求体过大");
		chunks.push(chunk);
	}
	if (chunks.length === 0) return {};
	const text = Buffer.concat(chunks).toString("utf8").trim();
	if (!text) return {};
	try {
		return JSON.parse(text);
	} catch {
		throw new Error("请求体不是合法 JSON");
	}
}

/**
 * Same-origin JSON API used by the sidebar panel. It stays deliberately small:
 * bootstrap/digest reads, one job submission, polling, and cancellation.
 */
export function registerApi(ctx, { pipeline, store, config }) {
	return ctx.effect(
		() => ctx.webServer.register({
			kind: "prefix",
			path: PREFIX,
			handler: (req, res) => handle(req, res, { pipeline, store, config }).catch((error) => {
				if (res.headersSent) {
					res.end();
					return;
				}
				sendJson(res, 500, { error: error instanceof Error ? error.message : String(error) });
			}),
		}),
		"signalforge: JSON API",
	);
}

async function handle(req, res, { pipeline, store, config }) {
	const url = new URL(req.url ?? "/", "http://localhost");
	if (!url.pathname.startsWith(PREFIX)) {
		sendJson(res, 404, { error: "not found" });
		return;
	}
	const tail = url.pathname.slice(PREFIX.length) || "/";
	const method = req.method ?? "GET";

	if (method === "GET" && tail === "/bootstrap") {
		const today = pipeline.today();
		const requested = url.searchParams.get("date");
		const date = isDate(requested) ? requested : today;
		const [digest, allDates] = await Promise.all([store.loadDigest(date), store.listDates()]);
		const dates = allDates.filter((item) => (item.signals ?? 0) > 0 || (item.business ?? 0) > 0 || (item.rdev ?? 0) > 0);
		sendJson(res, 200, {
			today,
			date,
			timezone: pipeline.settings.timezone,
			maxSignals: pipeline.settings.maxSignals,
			dates,
			digest,
			job: pipeline.current(),
		});
		return;
	}

	if (method === "GET" && tail === "/digest") {
		const date = url.searchParams.get("date");
		if (!isDate(date)) {
			sendJson(res, 400, { error: "date 必须是 YYYY-MM-DD" });
			return;
		}
		const digest = await store.loadDigest(date);
		if (!digest) {
			sendJson(res, 404, { error: "这一天还没有生成情报" });
			return;
		}
		sendJson(res, 200, digest);
		return;
	}

	if (method === "POST" && tail === "/jobs") {
		const body = await readJsonBody(req);
		const today = pipeline.today();
		const date = isDate(body?.date) ? body.date : today;
		const mode = body?.mode === "enrich" ? "enrich" : "full";
		try {
			const result = mode === "enrich" ? await pipeline.startEnrich(date) : pipeline.start(date);
			sendJson(res, result.reused ? 200 : 202, result);
		} catch (error) {
			sendJson(res, 400, { error: error instanceof Error ? error.message : String(error) });
		}
		return;
	}

	const jobMatch = tail.match(/^\/jobs\/([A-Za-z0-9-]+)$/);
	if (jobMatch) {
		const id = jobMatch[1];
		if (method === "GET") {
			const job = pipeline.get(id);
			if (!job) {
				sendJson(res, 404, { error: "任务不存在或已过期" });
				return;
			}
			sendJson(res, 200, job);
			return;
		}
		if (method === "DELETE") {
			const cancelled = pipeline.cancel(id);
			sendJson(res, cancelled ? 200 : 404, cancelled ? { ok: true } : { error: "没有可取消的任务" });
			return;
		}
	}

	if (method === "GET" && tail === "/health") {
		sendJson(res, 200, {
			ok: true,
			timezone: pipeline.settings.timezone,
			today: pipeline.today(),
			dataDir: config?.dataDir ?? null,
		});
		return;
	}

	sendJson(res, 404, { error: "not found" });
}
