import { createHash } from "node:crypto";

export const AI_RE = /\b(?:ai|agi|llms?|gpt|chatgpt|claude|gemini|deepseek|qwen|kimi|llama|mistral|agents?|agentic|inference|prompts?|rag|mcp|openai|anthropic|deepmind|hugging\s*face|transformers?|diffusion|multimodal|reasoning|fine-?tun(?:e|ing)|vibe\s*coding|copilot|cursor|codex|sora|midjourney)\b|人工智能|大模型|模型|智能体|提示词|推理|开源|多模态|生成式|机器学习|深度学习|微调|算力|芯片|具身/i;

const ENTITIES = new Map([
	["amp", "&"],
	["lt", "<"],
	["gt", ">"],
	["quot", "\""],
	["apos", "'"],
	["nbsp", " "],
	["hellip", "…"],
	["mdash", "—"],
	["ndash", "–"],
	["rsquo", "’"],
	["lsquo", "‘"],
	["ldquo", "“"],
	["rdquo", "”"],
]);

export function decodeEntities(value) {
	return String(value ?? "").replace(/&(#x?[0-9a-f]+|[a-z]+);/gi, (whole, body) => {
		if (body[0] === "#") {
			const code = body[1].toLowerCase() === "x" ? Number.parseInt(body.slice(2), 16) : Number.parseInt(body.slice(1), 10);
			if (!Number.isFinite(code) || code < 0 || code > 0x10ffff) return whole;
			try {
				return String.fromCodePoint(code);
			} catch {
				return whole;
			}
		}
		return ENTITIES.get(body.toLowerCase()) ?? whole;
	});
}

export function stripHtml(value) {
	let text = String(value ?? "");
	text = text.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1");
	text = text.replace(/<(script|style)\b[\s\S]*?<\/\1>/gi, " ");
	text = text.replace(/<br\s*\/?>/gi, " ");
	text = text.replace(/<\/p>/gi, " ");
	text = text.replace(/<[^>]+>/g, " ");
	text = decodeEntities(text);
	return text.replace(/\s+/g, " ").trim();
}

export function truncate(value, limit) {
	const text = String(value ?? "").replace(/\s+/g, " ").trim();
	if (text.length <= limit) return text;
	return `${text.slice(0, Math.max(0, limit - 1)).trimEnd()}…`;
}

export function hashId(value) {
	return createHash("sha1").update(String(value)).digest("hex").slice(0, 12);
}

export function normalizeUrl(value) {
	const raw = String(value ?? "").trim();
	if (!raw) return "";
	try {
		const url = new URL(raw);
		if (url.protocol !== "http:" && url.protocol !== "https:") return "";
		url.hash = "";
		url.hostname = url.hostname.replace(/^www\./i, "").toLowerCase();
		for (const key of [...url.searchParams.keys()]) {
			if (/^(utm_|ref$|ref_|source$|spm$|from$)/i.test(key)) url.searchParams.delete(key);
		}
		url.pathname = url.pathname.replace(/\/+$/, "") || "/";
		return url.toString();
	} catch {
		return "";
	}
}

export function normalizeTitle(value) {
	return String(value ?? "")
		.toLowerCase()
		.replace(/[\s\p{P}\p{S}]+/gu, "")
		.slice(0, 90);
}

export function parseDate(value) {
	if (value === undefined || value === null || value === "") return null;
	if (typeof value === "number") {
		const ms = value > 1e12 ? value : value * 1000;
		const date = new Date(ms);
		return Number.isNaN(date.getTime()) ? null : date;
	}
	const date = new Date(String(value));
	return Number.isNaN(date.getTime()) ? null : date;
}

export function isoOrNull(value) {
	const date = parseDate(value);
	return date === null ? null : date.toISOString();
}

export function todayInZone(timeZone = "Asia/Shanghai") {
	try {
		return new Intl.DateTimeFormat("en-CA", {
			timeZone,
			year: "numeric",
			month: "2-digit",
			day: "2-digit",
		}).format(new Date());
	} catch {
		return new Date().toISOString().slice(0, 10);
	}
}

export function addDays(date, delta) {
	const time = Date.parse(`${date}T12:00:00Z`);
	if (!Number.isFinite(time)) return date;
	return new Date(time + delta * 86400000).toISOString().slice(0, 10);
}

export function isDate(value) {
	return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(`${value}T12:00:00Z`));
}

export function weekdayCn(date) {
	const names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
	const time = Date.parse(`${date}T12:00:00Z`);
	if (!Number.isFinite(time)) return "";
	return names[new Date(time).getUTCDay()];
}

export function formatDateTime(value, timeZone = "Asia/Shanghai") {
	const date = parseDate(value);
	if (date === null) return "";
	try {
		return new Intl.DateTimeFormat("zh-CN", {
			timeZone,
			month: "2-digit",
			day: "2-digit",
			hour: "2-digit",
			minute: "2-digit",
			hour12: false,
		}).format(date);
	} catch {
		return date.toISOString().slice(5, 16).replace("T", " ");
	}
}

export async function fetchText(url, { timeoutMs = 15000, signal, accept = "*/*", attempts = 2 } = {}) {
	let lastError;
	for (let attempt = 1; attempt <= Math.max(1, attempts); attempt += 1) {
		const timeout = AbortSignal.timeout(timeoutMs);
		const combined = signal === undefined ? timeout : AbortSignal.any([signal, timeout]);
		try {
			const response = await fetch(url, {
				redirect: "follow",
				signal: combined,
				headers: {
					"user-agent": "SignalForge/0.1 (+DeepSeek Harness plugin; daily AI intelligence)",
					accept,
					"accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
				},
			});
			if (!response.ok) throw new Error(`HTTP ${response.status}`);
			return await response.text();
		} catch (error) {
			lastError = error;
			if (signal?.aborted || attempt >= attempts) break;
			const message = error instanceof Error ? error.message : String(error);
			if (/^HTTP \d/.test(message) || error?.name === "TimeoutError") break;
			await new Promise((resolve) => setTimeout(resolve, 350));
		}
	}
	throw lastError;
}

export async function fetchJson(url, options = {}) {
	const text = await fetchText(url, { ...options, accept: "application/json" });
	return JSON.parse(text);
}

function pickTag(block, names) {
	for (const name of names) {
		const match = block.match(new RegExp(`<${name}(?:\\s[^>]*)?>([\\s\\S]*?)</${name}>`, "i"));
		if (match && match[1].trim()) return stripHtml(match[1]);
	}
	return "";
}

/** Parse RSS 2.0 and Atom into a small common item shape. */
export function parseFeed(xml) {
	const items = [];
	const blocks = String(xml ?? "").match(/<(item|entry)\b[\s\S]*?<\/\1>/gi) ?? [];
	for (const block of blocks) {
		const title = pickTag(block, ["title"]);
		if (!title) continue;

		let link = pickTag(block, ["link"]);
		if (!link) {
			const attr = block.match(/<link\b[^>]*\bhref=["']([^"']+)["']/i);
			if (attr) link = decodeEntities(attr[1]).trim();
		}
		if (!link) {
			const guid = pickTag(block, ["guid", "id"]);
			if (/^https?:\/\//i.test(guid)) link = guid;
		}

		const summary = pickTag(block, [
			"description",
			"summary",
			"content:encoded",
			"content",
			"media:description",
		]);
		const published = pickTag(block, ["pubDate", "published", "updated", "dc:date", "date"]);
		items.push({ title, link, summary, published });
	}
	return items;
}

export function applyTemplate(template, values) {
	return template.replace(/\{(\w+)\}/g, (_, key) => String(values[key] ?? ""));
}

/** Human-facing bucket used by the "all intel" cards and filters. */
export function categoryOf(item) {
	const type = item?.source_type;
	const source = String(item?.source ?? "");
	if (type === "arxiv" || type === "paper") return "论文";
	if (type === "repo" || type === "github") return "仓库";
	if (type === "model") return "模型";
	if (type === "wechat") return "微信公众号资讯";
	if (type === "investor") return "投资者资讯";
	if (type === "smolai" || source === "Smol AI News") return "Smol 资讯";
	if (type === "blog") {
		const official = item?.metadata?.official === true
			|| ["OpenAI News", "Google DeepMind", "Google AI Blog", "Hugging Face Blog", "Anthropic Blog"].includes(source);
		return official ? "AI公司博客" : "资讯";
	}
	return "资讯";
}
