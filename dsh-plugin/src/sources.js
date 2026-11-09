import {
	AI_RE,
	fetchJson,
	fetchText,
	hashId,
	isoOrNull,
	categoryOf,
	normalizeTitle,
	normalizeUrl,
	parseDate,
	parseFeed,
	stripHtml,
	truncate,
} from "./util.js";

/**
 * Curated, login-free sources for the first release. Every source is fetched in
 * parallel and a single failure only removes that source from the edition.
 */
export const FEEDS = [
	{ key: "openai", name: "OpenAI News", url: "https://openai.com/news/rss.xml", source_type: "blog", official: true, max: 6, lookbackHours: 336 },
	{ key: "deepmind", name: "Google DeepMind", url: "https://deepmind.google/blog/rss.xml", source_type: "blog", official: true, max: 6, lookbackHours: 336 },
	{ key: "googleai", name: "Google AI Blog", url: "https://blog.google/technology/ai/rss/", source_type: "blog", official: true, max: 6, lookbackHours: 336 },
	{ key: "hfblog", name: "Hugging Face Blog", url: "https://huggingface.co/blog/feed.xml", source_type: "blog", official: true, max: 6, lookbackHours: 336 },
	{ key: "googleresearch", name: "Google Research", url: "https://research.google/blog/rss/", source_type: "blog", official: true, max: 6, lookbackHours: 336 },
	{ key: "nvidia", name: "NVIDIA Developer", url: "https://developer.nvidia.com/blog/feed/", source_type: "blog", official: true, max: 6, lookbackHours: 336 },
	{ key: "appleml", name: "Apple Machine Learning", url: "https://machinelearning.apple.com/rss.xml", source_type: "blog", official: true, max: 6, lookbackHours: 336 },
	{ key: "langchain", name: "LangChain Blog", url: "https://blog.langchain.dev/rss.xml", source_type: "blog", official: true, max: 6, lookbackHours: 336 },
	{ key: "cloudflareai", name: "Cloudflare AI", url: "https://blog.cloudflare.com/tag/ai/rss/", source_type: "blog", official: true, max: 6, lookbackHours: 336 },
	{ key: "awsml", name: "AWS Machine Learning", url: "https://aws.amazon.com/blogs/machine-learning/feed/", source_type: "blog", official: true, max: 6, lookbackHours: 336 },
	{ key: "latent", name: "Latent Space", url: "https://www.latent.space/feed", source_type: "newsletter", official: false, max: 8 },
	{ key: "smol", name: "Smol AI News", url: "https://news.smol.ai/rss.xml", source_type: "newsletter", official: false, max: 6 },
	{ key: "decoder", name: "The Decoder", url: "https://the-decoder.com/feed/", source_type: "news", official: false, max: 8 },
	{ key: "techcrunch", name: "TechCrunch AI", url: "https://techcrunch.com/category/artificial-intelligence/feed/", source_type: "news", official: false, max: 8 },
	{ key: "simon", name: "Simon Willison", url: "https://simonwillison.net/atom/everything/", source_type: "blog", official: false, max: 6 },
	{ key: "oneusefulthing", name: "One Useful Thing", url: "https://www.oneusefulthing.org/feed", source_type: "newsletter", official: false, max: 4 },
	{ key: "importai", name: "Import AI", url: "https://importai.substack.com/feed", source_type: "newsletter", official: false, max: 4 },
	{ key: "interconnects", name: "Interconnects", url: "https://www.interconnects.ai/feed", source_type: "newsletter", official: false, max: 4 },
];

/**
 * Company blogs without a usable RSS/Atom feed. The listing page supplies
 * article URLs; each article page supplies title, description and date.
 */
export const HTML_SOURCES = [
	{
		key: "anthropic-news",
		name: "Anthropic News",
		listingUrl: "https://www.anthropic.com/news",
		patterns: [/^\/news\/[^/]+$/],
		exclude: [/^\/news\/(announcements|product|features|partnerships)\/?$/],
		max: 4,
		lookbackHours: 336,
	},
	{
		key: "anthropic-engineering",
		name: "Anthropic Engineering",
		listingUrl: "https://www.anthropic.com/engineering",
		patterns: [/^\/research\/[^/]+$/],
		max: 4,
		lookbackHours: 336,
	},
	{
		key: "cognition",
		name: "Cognition Blog",
		listingUrl: "https://cognition.ai/blog",
		patterns: [/^\/blog\/[^/]+\/?$/],
		exclude: [/^\/blog\/(tag|category|author)\/.+$/, /^\/blog\/?$/],
		max: 5,
		lookbackHours: 336,
	},
	{
		key: "meta-ai",
		name: "Meta AI Blog",
		listingUrl: "https://ai.meta.com/blog/",
		patterns: [/^\/blog\/[^/]+\/?$/],
		exclude: [/^\/blog\/?$/],
		max: 4,
		lookbackHours: 336,
	},
	{
		key: "cohere",
		name: "Cohere Blog",
		listingUrl: "https://cohere.com/blog",
		patterns: [/^\/blog\/[^/]+\/?$/],
		exclude: [/^\/blog\/tag\/.+$/, /^\/blog\/?$/],
		max: 5,
		lookbackHours: 336,
	},
];

const HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json";
const HN_ITEM = "https://hacker-news.firebaseio.com/v0/item";
const HN_SEARCH = "https://hn.algolia.com/api/v1/search_by_date";
const ARXIV_QUERY = "https://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.LG&start=0&max_results=30&sortBy=submittedDate&sortOrder=descending";
const HF_PAPERS = "https://huggingface.co/api/daily_papers";
const GITHUB_TRENDING = "https://github.com/trending?since=daily";

async function mapLimit(items, limit, worker) {
	const results = new Array(items.length);
	let next = 0;
	async function run() {
		while (next < items.length) {
			const index = next;
			next += 1;
			results[index] = await worker(items[index], index);
		}
	}
	await Promise.all(Array.from({ length: Math.min(limit, items.length) }, run));
	return results;
}

function makeCandidate({
	title,
	url,
	source,
	source_type,
	published_at,
	summary,
	metadata = {},
	baseScore = 6,
}) {
	const normalized = normalizeUrl(url);
	if (!normalized) return null;
	const cleanTitle = truncate(stripHtml(title), 220);
	if (!cleanTitle) return null;
	const cleanSummary = truncate(stripHtml(summary), 900);
	return {
		id: hashId(`${normalized}|${cleanTitle}`),
		title: cleanTitle,
		url: normalized,
		source,
		source_type,
		published_at,
		summary: cleanSummary,
		relevance_score: baseScore,
		metadata,
	};
}

function score(candidate, now) {
	let value = candidate.metadata.official ? 7 : 6;
	if (candidate.source_type === "repo") value += 0.4;
	if (candidate.source_type === "newsletter") value += 0.2;
	const points = Number(candidate.metadata.points ?? 0);
	if (points > 0) value += Math.min(2.6, Math.log10(points + 1) * 1.1);
	const stars = Number(candidate.metadata.stars ?? 0);
	if (stars > 0) value += Math.min(1.8, Math.log10(stars + 1) * 0.55);
	const published = parseDate(candidate.published_at);
	if (published !== null) {
		const hours = (now - published.getTime()) / 3600000;
		if (hours <= 12) value += 0.7;
		else if (hours <= 24) value += 0.35;
		else if (hours > 96) value -= 0.4;
	}
	candidate.relevance_score = Math.round(value * 10) / 10;
	return candidate.relevance_score;
}

function withinLookback(published, cutoff) {
	const date = parseDate(published);
	return date !== null && date.getTime() >= cutoff && date.getTime() <= Date.now() + 3600000;
}

function metaContent(html) {
	const map = new Map();
	for (const tag of String(html ?? "").match(/<meta\b[^>]*>/gi) ?? []) {
		const key = tag.match(/(?:property|name)=["']([^"']+)["']/i)?.[1]?.toLowerCase();
		const content = tag.match(/content=["']([^"']*)["']/i)?.[1];
		if (key && content !== undefined && !map.has(key)) map.set(key, stripHtml(content));
	}
	return map;
}

function firstParagraph(html) {
	const body = String(html ?? "").replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, " ");
	const paragraphs = [...body.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/gi)]
		.map((match) => stripHtml(match[1]))
		.filter((text) => text.length >= 40);
	return paragraphs[0] ?? "";
}

function extractArticleMeta(html, fallbackTitle) {
	const meta = metaContent(html);
	const titleTag = String(html ?? "").match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1] ?? "";
	const h1 = String(html ?? "").match(/<h1[^>]*>([\s\S]*?)<\/h1>/i)?.[1] ?? "";
	const paragraph = firstParagraph(html);
	const title = truncate(stripHtml(
		meta.get("og:title")
		|| meta.get("twitter:title")
		|| meta.get("title")
		|| titleTag
		|| h1
		|| fallbackTitle
		|| ""
	), 220);
	let summary = truncate(stripHtml(
		meta.get("og:description")
		|| meta.get("description")
		|| meta.get("twitter:description")
		|| paragraph
		|| ""
	), 700);
	if (/^Anthropic is an AI safety and research company/i.test(summary) && paragraph) {
		summary = truncate(paragraph, 700);
	}
	const jsonLdDate = String(html ?? "").match(/"datePublished"\s*:\s*"([^"]+)"/i)?.[1];
	const timeTag = String(html ?? "").match(/<time\b[^>]*datetime=["']([^"']+)["']/i)?.[1];
	const textDate = paragraph.match(/\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b/)?.[0];
	const published = meta.get("article:published_time") || jsonLdDate || timeTag || textDate || null;
	return {
		title,
		summary,
		published_at: isoOrNull(published),
	};
}

function extractListingLinks(html, source) {
	const origin = new URL(source.listingUrl).origin;
	const seen = new Set();
	const out = [];
	for (const match of String(html ?? "").matchAll(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi)) {
		let url;
		try {
			url = new URL(match[1], source.listingUrl);
		} catch {
			continue;
		}
		if (url.origin !== origin || !/^https?:$/.test(url.protocol)) continue;
		const pathname = url.pathname;
		if (!source.patterns.some((pattern) => pattern.test(pathname))) continue;
		if (source.exclude?.some((pattern) => pattern.test(pathname))) continue;
		const normalized = normalizeUrl(url.toString());
		if (!normalized || seen.has(normalized)) continue;
		seen.add(normalized);
		const title = truncate(stripHtml(match[2]), 200);
		out.push({ url: normalized, title });
		if (out.length >= source.max * 2) break;
	}
	return out;
}

async function collectHtmlBlog(source, { now, defaultLookbackHours, timeoutMs, signal }) {
	const listing = await fetchText(source.listingUrl, { timeoutMs, signal });
	const links = extractListingLinks(listing, source);
	const articles = await mapLimit(links, 4, async (link) => {
		try {
			const html = await fetchText(link.url, { timeoutMs, signal });
			const meta = extractArticleMeta(html, link.title);
			return {
				url: link.url,
				title: meta.title || link.title,
				summary: meta.summary,
				published_at: meta.published_at,
			};
		} catch {
			return { url: link.url, title: link.title, summary: "", published_at: null };
		}
	});
	const cutoff = now - (source.lookbackHours ?? defaultLookbackHours) * 3600000;
	const collected = [];
	for (const article of articles) {
		if (!article.title) continue;
		if (article.published_at) {
			const published = parseDate(article.published_at);
			if (published === null || published.getTime() < cutoff || published.getTime() > Date.now() + 3600000) continue;
		}
		const candidate = makeCandidate({
			title: article.title,
			url: article.url,
			source: source.name,
			source_type: "blog",
			published_at: article.published_at,
			summary: article.summary,
			metadata: { official: true, feed: source.key, html: true, engagement: "" },
			baseScore: 7,
		});
		if (candidate) collected.push(candidate);
		if (collected.length >= source.max) break;
	}
	return collected;
}

async function collectFeed(feed, { now, defaultLookbackHours, timeoutMs, signal }) {
	const cutoff = now - (feed.lookbackHours ?? defaultLookbackHours) * 3600000;
	const xml = await fetchText(feed.url, { timeoutMs, signal });
	const items = parseFeed(xml);
	const collected = [];
	for (const item of items) {
		if (collected.length >= feed.max) break;
		if (!withinLookback(item.published, cutoff)) continue;
		if (feed.requireAi === true && !AI_RE.test(`${item.title} ${item.summary}`)) continue;
		const candidate = makeCandidate({
			title: item.title,
			url: item.link,
			source: feed.name,
			source_type: feed.source_type,
			published_at: isoOrNull(item.published),
			summary: item.summary,
			metadata: { official: feed.official, feed: feed.key, engagement: "" },
		});
		if (candidate) collected.push(candidate);
	}
	return collected;
}

async function collectHnTop({ cutoff, timeoutMs, signal }) {
	const ids = await fetchJson(HN_TOP, { timeoutMs, signal });
	if (!Array.isArray(ids)) return [];
	const items = await mapLimit(ids.slice(0, 80), 12, async (id) => {
		try {
			return await fetchJson(`${HN_ITEM}/${id}.json`, { timeoutMs, signal });
		} catch {
			return null;
		}
	});
	const picked = [];
	for (const item of items) {
		if (!item || item.dead || item.deleted || item.type !== "story") continue;
		const text = `${item.title ?? ""} ${item.text ?? ""}`;
		if (!AI_RE.test(text)) continue;
		if (Number(item.score ?? 0) < 20) continue;
		if (!withinLookback(isoOrNull(item.time), cutoff)) continue;
		const candidate = makeCandidate({
			title: item.title,
			url: item.url || `https://news.ycombinator.com/item?id=${item.id}`,
			source: "Hacker News",
			source_type: "hn",
			published_at: isoOrNull(item.time),
			summary: item.text || item.title,
			metadata: {
				points: item.score,
				comments: item.descendants,
				engagement: `${item.score ?? 0} points, ${item.descendants ?? 0} comments`,
				hn_id: item.id,
			},
		});
		if (candidate) picked.push(candidate);
	}
	return picked;
}

async function collectHnSearch({ cutoff, timeoutMs, signal }) {
	const cutoffSeconds = Math.floor(cutoff / 1000);
	const url = `${HN_SEARCH}?query=AI&tags=story&hitsPerPage=50&numericFilters=created_at_i%3E${cutoffSeconds}`;
	const payload = await fetchJson(url, { timeoutMs, signal });
	const hits = Array.isArray(payload?.hits) ? payload.hits : [];
	const out = [];
	for (const hit of hits) {
		if (!hit || !hit.title) continue;
		if (!AI_RE.test(`${hit.title} ${hit.story_text ?? ""}`)) continue;
		if (Number(hit.points ?? 0) < 5) continue;
		const candidate = makeCandidate({
			title: hit.title,
			url: hit.url || `https://news.ycombinator.com/item?id=${hit.objectID}`,
			source: "Hacker News",
			source_type: "hn",
			published_at: isoOrNull(hit.created_at_i),
			summary: hit.story_text || hit.title,
			metadata: {
				points: hit.points,
				comments: hit.num_comments,
				engagement: `${hit.points ?? 0} points, ${hit.num_comments ?? 0} comments`,
				hn_id: hit.objectID,
			},
		});
		if (candidate) out.push(candidate);
	}
	return out;
}

async function collectArxiv({ cutoff, timeoutMs, signal }) {
	const xml = await fetchText(ARXIV_QUERY, { timeoutMs, signal });
	const entries = parseFeed(xml);
	const out = [];
	for (const entry of entries) {
		const published = isoOrNull(entry.published);
		if (!withinLookback(published, cutoff)) continue;
		const candidate = makeCandidate({
			title: entry.title,
			url: entry.link,
			source: "arXiv",
			source_type: "arxiv",
			published_at: published,
			summary: entry.summary,
			metadata: { official: false, engagement: "" },
		});
		if (candidate) out.push(candidate);
	}
	return out;
}

async function collectHfPapers({ cutoff, timeoutMs, signal }) {
	const payload = await fetchJson(HF_PAPERS, { timeoutMs, signal });
	if (!Array.isArray(payload)) return [];
	const out = [];
	for (const entry of payload.slice(0, 30)) {
		const paper = entry?.paper ?? entry;
		if (!paper?.id || !paper?.title) continue;
		const published = isoOrNull(entry.submittedOnDailyAt ?? paper.publishedAt);
		if (!withinLookback(published, cutoff)) continue;
		const candidate = makeCandidate({
			title: paper.title,
			url: `https://huggingface.co/papers/${paper.id}`,
			source: "Hugging Face Daily Papers",
			source_type: "paper",
			published_at: published,
			summary: paper.summary,
			metadata: {
				points: paper.upvotes,
				engagement: paper.upvotes ? `${paper.upvotes} upvotes` : "",
				authors: Array.isArray(paper.authors) ? paper.authors.slice(0, 4).map((author) => author.name).filter(Boolean) : [],
			},
		});
		if (candidate) out.push(candidate);
	}
	return out;
}

function parseGithubTrending(html) {
	const blocks = String(html ?? "").split(/<article\b[^>]*class="[^"]*Box-row[^"]*"[\s\S]*?>/i).slice(1);
	const out = [];
	for (const block of blocks) {
		const repoMatch = block.match(/<h2\b[\s\S]*?<a\b[^>]*href="\/([^"/]+\/[^"/]+)"/i);
		if (!repoMatch) continue;
		const repo = repoMatch[1].trim();
		const descMatch = block.match(/<p\b[^>]*class="[^"]*col-9[^"]*"[^>]*>([\s\S]*?)<\/p>/i);
		const desc = descMatch ? stripHtml(descMatch[1]) : "";
		const starsMatch = block.match(/([\d,.]+)\s+stars?\s+today/i);
		const starsToday = starsMatch ? Number(starsMatch[1].replace(/[,.]/g, "")) : 0;
		if (!AI_RE.test(`${repo} ${desc}`)) continue;
		const candidate = makeCandidate({
			title: `${repo}: ${truncate(desc, 120)}`,
			url: `https://github.com/${repo}`,
			source: "GitHub Trending",
			source_type: "repo",
			published_at: new Date().toISOString(),
			summary: desc,
			metadata: {
				repo,
				stars: starsToday,
				engagement: starsToday ? `${starsToday} stars today` : "",
			},
		});
		if (candidate) out.push(candidate);
	}
	return out;
}

async function collectGithub({ timeoutMs, signal }) {
	const html = await fetchText(GITHUB_TRENDING, { timeoutMs, signal });
	return parseGithubTrending(html);
}

function dedupe(candidates) {
	const seenUrls = new Set();
	const seenTitles = new Set();
	const out = [];
	for (const candidate of candidates) {
		const titleKey = normalizeTitle(candidate.title);
		if (seenUrls.has(candidate.url) || (titleKey && seenTitles.has(titleKey))) continue;
		seenUrls.add(candidate.url);
		if (titleKey) seenTitles.add(titleKey);
		out.push(candidate);
	}
	return out;
}

function displayItem(candidate) {
	return {
		id: candidate.id,
		title: candidate.title,
		url: candidate.url,
		source: candidate.source,
		source_type: candidate.source_type,
		category: categoryOf(candidate),
		published_at: candidate.published_at,
		relevance_score: candidate.relevance_score,
		summary: truncate(candidate.summary ?? "", 420),
		metadata: {
			points: candidate.metadata?.points,
			comments: candidate.metadata?.comments,
			stars: candidate.metadata?.stars,
			engagement: candidate.metadata?.engagement,
			official: candidate.metadata?.official,
			repo: candidate.metadata?.repo,
			authors: candidate.metadata?.authors,
		},
	};
}

function sourceCap(candidate) {
	if (candidate.source === "arXiv") return 15;
	if (candidate.source === "Hacker News") return 8;
	if (candidate.source === "GitHub Trending") return 6;
	if (candidate.metadata?.official === true) return 4;
	return 5;
}

/** Interleave sources so one prolific blog cannot own the model prompt. */
function diversifyBySource(sorted) {
	const groups = new Map();
	for (const candidate of sorted) {
		const group = groups.get(candidate.source) ?? [];
		group.push(candidate);
		groups.set(candidate.source, group);
	}
	const queues = [...groups.values()];
	const out = [];
	let added = true;
	while (added) {
		added = false;
		for (const queue of queues) {
			const candidate = queue.shift();
			if (candidate === undefined) continue;
			out.push(candidate);
			added = true;
		}
	}
	return out;
}

function rankAndCap(candidates, { limit, maxPerType = 30, maxOfficial = 24 }) {
	const sorted = candidates.slice().sort((a, b) => {
		if (b.relevance_score !== a.relevance_score) return b.relevance_score - a.relevance_score;
		return String(b.published_at ?? "").localeCompare(String(a.published_at ?? ""));
	});
	const out = [];
	const perSource = new Map();
	const perType = new Map();
	let officialCount = 0;
	for (const candidate of diversifyBySource(sorted)) {
		if (out.length >= limit) break;
		const sourceCount = perSource.get(candidate.source) ?? 0;
		if (sourceCount >= sourceCap(candidate)) continue;
		const typeCount = perType.get(candidate.source_type) ?? 0;
		if (typeCount >= maxPerType) continue;
		const official = candidate.metadata?.official === true;
		if (official && officialCount >= maxOfficial) continue;
		out.push(candidate);
		perSource.set(candidate.source, sourceCount + 1);
		perType.set(candidate.source_type, typeCount + 1);
		if (official) officialCount += 1;
	}
	return out;
}

/**
 * Fetch every configured source once. The returned stats drive the progress
 * text in the panel, and the ranked candidates are the only material sent to
 * the model.
 */
export async function collectCandidates({ lookbackHours = 48, timeoutMs = 16000, signal, onProgress } = {}) {
	const startedAt = Date.now();
	const cutoff = startedAt - Math.max(1, lookbackHours) * 3600000;
	const stats = [];
	const all = [];

	const tasks = [
		...FEEDS.map((feed) => ({
			name: feed.name,
			run: () => collectFeed(feed, { now: startedAt, defaultLookbackHours: lookbackHours, timeoutMs, signal }),
		})),
		...HTML_SOURCES.map((source) => ({
			name: source.name,
			run: () => collectHtmlBlog(source, { now: startedAt, defaultLookbackHours: lookbackHours, timeoutMs, signal }),
		})),
		{ name: "Hacker News", run: () => collectHnTop({ cutoff, timeoutMs, signal }) },
		{ name: "Hacker News Search", run: () => collectHnSearch({ cutoff, timeoutMs, signal }) },
		{ name: "arXiv", run: () => collectArxiv({ cutoff, timeoutMs, signal }) },
		{ name: "Hugging Face Daily Papers", run: () => collectHfPapers({ cutoff, timeoutMs, signal }) },
		{ name: "GitHub Trending", run: () => collectGithub({ timeoutMs, signal }) },
	];

	let done = 0;
	const total = tasks.length;
	onProgress?.({ stage: "sources", done, total, source: "开始抓取" });

	const results = await Promise.all(tasks.map(async (task) => {
		const begin = Date.now();
		try {
			const items = await task.run();
			const stat = { name: task.name, ok: true, count: items.length, ms: Date.now() - begin };
			stats.push(stat);
			all.push(...items);
			return items;
		} catch (error) {
			const stat = {
				name: task.name,
				ok: false,
				count: 0,
				ms: Date.now() - begin,
				error: error instanceof Error ? error.message : String(error),
			};
			stats.push(stat);
			return [];
		} finally {
			done += 1;
			onProgress?.({ stage: "sources", done, total, source: task.name });
		}
	}));

	const flattened = results.flat();
	const unique = dedupe(flattened);
	for (const candidate of unique) score(candidate, startedAt);
	const selected = rankAndCap(unique, { limit: 72, maxPerType: 30, maxOfficial: 24 });
	const allItems = unique
		.slice()
		.sort((a, b) => (b.relevance_score - a.relevance_score) || String(b.published_at ?? "").localeCompare(String(a.published_at ?? "")))
		.map(displayItem);
	stats.sort((a, b) => (a.ok === b.ok ? b.count - a.count : a.ok ? -1 : 1));

	return {
		candidates: selected,
		all: allItems,
		allCount: unique.length,
		stats,
		elapsedMs: Date.now() - startedAt,
	};
}

export { makeCandidate, rankAndCap, dedupe, displayItem, parseGithubTrending };
