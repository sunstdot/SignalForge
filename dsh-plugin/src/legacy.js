import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { categoryOf, todayInZone, truncate } from "./util.js";

async function readJson(file) {
	try {
		return JSON.parse(await readFile(file, "utf8"));
	} catch (error) {
		if (error?.code === "ENOENT" || error instanceof SyntaxError) return null;
		throw error;
	}
}

function asArray(value) {
	return Array.isArray(value) ? value : [];
}

function legacyTrack(card) {
	if (card.track === "execution" || card.track === "inspiration") return card.track;
	return ["arxiv", "paper", "repo", "model", "blog"].includes(card.source_type) ? "execution" : "inspiration";
}

function legacySignals(briefing) {
	const raw = briefing?.signals;
	const cards = Array.isArray(raw)
		? raw
		: [
			...asArray(raw?.inspiration),
			...asArray(raw?.execution),
		];
	const seen = new Set();
	const signals = [];
	for (const card of cards) {
		if (!card || typeof card !== "object" || !card.title || !card.url) continue;
		const key = card.id || `${card.url}|${card.title}`;
		if (seen.has(key)) continue;
		seen.add(key);
		const finding = String(card.finding || card.takeaway || card.summary || "").trim();
		const whyRead = String(card.why_read || card.so_what || "").trim();
		if (!finding || !whyRead) continue;
		signals.push({
			id: String(card.id || key),
			title: String(card.title),
			url: String(card.url),
			source: String(card.source || "历史归档"),
			source_type: String(card.source_type || "news"),
			published_at: card.published_at || null,
			relevance_score: Number(card.relevance_score ?? 6),
			track: legacyTrack(card),
			tags: asArray(card.tags).filter((tag) => typeof tag === "string").slice(0, 3),
			finding,
			why_read: whyRead,
			evidence_note: String(card.evidence_note || card.why || "历史归档数据，建议核对原文。"),
			details: asArray(card.details || card.facts).filter((item) => typeof item === "string").slice(0, 4),
			takeaway: String(card.takeaway || finding),
			evidence: String(card.evidence || ""),
			rank: signals.length + 1,
			legacy: true,
		});
	}
	return signals;
}

function legacyItems(briefing) {
	return asArray(briefing?.items)
		.filter((item) => item && typeof item === "object" && item.title && item.url)
		.map((item) => ({
			id: String(item.id || `${item.url}|${item.title}`),
			title: String(item.title),
			url: String(item.url),
			source: String(item.source || "历史归档"),
			source_type: String(item.source_type || "news"),
			category: categoryOf(item),
			published_at: item.published_at || item.created_at || null,
			relevance_score: Number(item.relevance_score ?? 6),
			summary: truncate(item.summary || item.original_content || "", 420),
			metadata: {},
			legacy: true,
		}));
}

function legacyBusiness(entry) {
	if (!entry || typeof entry !== "object") return null;
	const title = String(entry.opportunity_title || entry.title || "").trim();
	const insight = String(entry.core_insight || "").trim();
	if (!title || !insight) return null;
	const scores = entry.scores && typeof entry.scores === "object" ? entry.scores : {};
	return {
		title,
		trigger: String(entry.trigger || "").trim(),
		core_insight: insight,
		product_form: String(entry.product_form || "").trim(),
		target_users: String(entry.target_users || "").trim(),
		mvp_features: asArray(entry.mvp_features).filter((item) => typeof item === "string").slice(0, 4),
		business_model: String(entry.business_model || "").trim(),
		risks: String(entry.risks || "").trim(),
		scores,
		total_score: Number(entry.total_score ?? 0),
		source_title: String(entry.source_title || "").trim(),
		source_url: String(entry.source_url || "").trim(),
		source_name: String(entry.source || "").trim(),
		legacy: true,
	};
}

function legacyRdev(entry) {
	if (!entry || typeof entry !== "object") return null;
	const title = String(entry.title || "").trim();
	const scenario = String(entry.scenario || "").trim();
	if (!title || !scenario) return null;
	const scores = entry.scores && typeof entry.scores === "object" ? entry.scores : {};
	return {
		type: entry.type === "业务赋能" ? "业务赋能" : "研发提效",
		title,
		trigger: String(entry.trigger || "").trim(),
		scenario,
		ai_solution: String(entry.ai_solution || "").trim(),
		implementation: String(entry.implementation || "").trim(),
		audience: asArray(entry.audience).filter((item) => typeof item === "string").slice(0, 4),
		impact: String(entry.impact || "").trim(),
		difficulty: ["低", "中", "高"].includes(entry.difficulty) ? entry.difficulty : "中",
		resistance: String(entry.resistance || "").trim(),
		scores,
		total_score: Number(entry.total_score ?? scores.overall ?? 0),
		source_title: String(entry.source_title || "").trim(),
		source_url: String(entry.source_url || "").trim(),
		source_name: String(entry.source || "").trim(),
		legacy: true,
	};
}

async function legacyOpportunities(repoRoot, date) {
	const [businessFile, rdevFile] = await Promise.all([
		readJson(path.join(repoRoot, "data", "opportunities", `${date}.json`)),
		readJson(path.join(repoRoot, "data", "rdev_opportunities", `${date}.json`)),
	]);
	const business = asArray(businessFile?.opportunities)
		.map(legacyBusiness)
		.filter(Boolean)
		.sort((a, b) => b.total_score - a.total_score)
		.slice(0, 3);
	const rdev = asArray(rdevFile?.solutions)
		.map(legacyRdev)
		.filter(Boolean)
		.sort((a, b) => b.total_score - a.total_score)
		.slice(0, 3);
	return { business, rdev };
}

/**
 * Convert already-generated SignalForge briefings into plugin digests.
 * Dates without selected signals are skipped: those are exactly the archive
 * entries that should not appear in the day picker.
 */
export async function importLegacy({ repoRoot, store, force = false, includeToday = false } = {}) {
	const today = todayInZone("Asia/Shanghai");
	const briefingsDir = path.join(repoRoot, "data", "briefings");
	let names;
	try {
		names = await readdir(briefingsDir);
	} catch {
		return { imported: 0, skipped: 0, missing: true };
	}
	let imported = 0;
	let skipped = 0;
	for (const name of names.sort()) {
		const match = name.match(/^(\d{4}-\d{2}-\d{2})\.json$/);
		if (!match) continue;
		const date = match[1];
		if (date === today && !includeToday) {
			skipped += 1;
			continue;
		}
		if (!force && await store.loadDigest(date)) {
			skipped += 1;
			continue;
		}
		const briefing = await readJson(path.join(briefingsDir, name));
		if (!briefing) {
			skipped += 1;
			continue;
		}
		const signals = legacySignals(briefing);
		if (signals.length === 0) {
			skipped += 1;
			continue;
		}
		const opportunities = await legacyOpportunities(repoRoot, date);
		const generatedAt = briefing.generated_at || `${date}T12:00:00.000Z`;
		await store.saveDigest({
			version: 1,
			date,
			timezone: "Asia/Shanghai",
			generatedAt,
			legacy: true,
			analysis: {
				provider: null,
				model: null,
				maxSignals: signals.length,
				warning: null,
				opportunitiesError: null,
				legacy: true,
			},
			stats: {
				candidates: asArray(briefing.items).length,
				selected: signals.length,
				okSources: 0,
				sourceTotal: 0,
				sources: [],
				legacy: true,
			},
			items: legacyItems(briefing),
			signals,
			opportunities: {
				generatedAt: opportunities.business.length + opportunities.rdev.length > 0 ? generatedAt : null,
				business: opportunities.business,
				rdev: opportunities.rdev,
				legacy: true,
			},
		});
		imported += 1;
	}
	return { imported, skipped, missing: false };
}
