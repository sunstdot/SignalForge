import { categoryOf, truncate } from "./util.js";

const ALLOWED_TAGS = ["新能力新用法", "实践方法", "失败与限制", "对比与选择", "新问题与需求"];
const EXECUTION_TYPES = new Set(["arxiv", "paper", "repo", "model", "blog"]);
const MAX_DETAILS = 4;

const SYSTEM = `你是 SignalForge 的情报主编，服务对象是一位独立开发者 / AI 产品人。你的判断必须克制、具体、可核对：只使用给定材料，不补充材料之外的事实，不把标题联想当成结论。

你会收到当天抓取的候选条目。你的任务不是摘要所有内容，而是挑出最多 5 条真正值得花时间看的信号，并写清楚「发现了什么」和「为什么值得看」。宁缺毋滥，没有足够好的条目就少选。`;

const OPPORTUNITY_SYSTEM = `你是一位做过独立产品、也带过研发团队的 AI 产品与技术顾问。你只从给定的今日信号出发，寻找能落地、能验证的机会，不写正确的废话，不虚构材料里没有的能力或数字。

商业机会面向独立开发者：一个月内能做出 MVP，有明确付费对象。
研发机会面向互联网公司研发团队：能插入现有工作流，减少重复劳动或提升业务转化。`;

function sourceTypeLabel(type) {
	return {
		arxiv: "论文",
		paper: "论文",
		repo: "开源项目",
		hn: "社区热榜",
		blog: "博客",
		newsletter: "Newsletter",
		news: "媒体",
	}[type] ?? type;
}

export function evidenceNote(item) {
	const metadata = item.metadata ?? {};
	const parts = [];
	if (item.source_type === "hn") {
		parts.push("社区热榜（转述/讨论，非独立验证）");
	} else if (item.source_type === "arxiv" || item.source_type === "paper") {
		parts.push("论文摘要（未经同行评审与原文核验）");
	} else if (item.source_type === "repo") {
		parts.push("开源仓库（README 与代码未核验）");
	} else if (metadata.official === true) {
		parts.push("官方材料");
	} else if (item.source_type === "newsletter") {
		parts.push("作者 Newsletter（观点与转述）");
	} else if (item.source_type === "news") {
		parts.push("媒体转述");
	} else {
		parts.push("作者博客（观点与转述）");
	}
	const engagement = String(metadata.engagement ?? "").trim();
	if (engagement) parts.push(`互动数据：${engagement}`);
	if (item.source_type === "hn" && !engagement) parts.push("无互动数据");
	return parts.join(" · ");
}

export function trackOf(item) {
	return EXECUTION_TYPES.has(item.source_type) ? "execution" : "inspiration";
}

export function inferTags(text) {
	const rules = [
		["新能力新用法", /发布|推出|新增|新功能|支持|上线|release|launch|new\b|现在可以|能力/i],
		["实践方法", /方法|流程|步骤|工作流|实践|怎么做|教程|指南|tutorial|workflow|pipeline|how to/i],
		["失败与限制", /失败|限制|局限|踩坑|翻车|教训|缺点|不能|bug|failure|limitation|drawback/i],
		["对比与选择", /对比|比较|选择|权衡|替代|评测|benchmark|versus|\bvs\b|取舍|哪个/i],
		["新问题与需求", /问题|需求|痛点|希望|求助|问一下|\bask\b|question|need|想要|期待/i],
	];
	return rules.filter(([, pattern]) => pattern.test(text)).slice(0, 2).map(([label]) => label);
}

function stripFence(text) {
	let value = String(text ?? "").trim();
	value = value.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "").trim();
	const start = value.search(/[[{]/);
	if (start > 0) value = value.slice(start);
	const objectEnd = value.lastIndexOf("}");
	const arrayEnd = value.lastIndexOf("]");
	const end = Math.max(objectEnd, arrayEnd);
	if (end >= 0 && end < value.length - 1) value = value.slice(0, end + 1);
	return value;
}

export function parseJsonLoose(text) {
	const cleaned = stripFence(text);
	try {
		return JSON.parse(cleaned);
	} catch {
		const repaired = cleaned
			.replace(/,\s*([}\]])/g, "$1")
			.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, " ");
		return JSON.parse(repaired);
	}
}

async function callModel(ctx, { system, prompt, maxTokens = 6000, signal }) {
	const selection = ctx.agentDefaultModel.currentSelection();
	const config = {
		provider: selection.provider,
		model: selection.model,
		maxTokens,
		...(selection.reasoningEffort === undefined ? {} : { reasoningEffort: selection.reasoningEffort }),
	};
	const call = await ctx.llm.prepareCall(config, signal);
	let text = "";
	let finish;
	const options = {
		...call.config,
		system,
		messages: [{ role: "user", content: [{ type: "text", text: prompt }] }],
		signal,
	};
	for await (const chunk of call.stream(options)) {
		if (chunk.type === "text-delta") text += chunk.text;
		else if (chunk.type === "finish") finish = chunk.reason;
	}
	if (finish?.kind === "error") {
		const failure = finish.failure ?? {};
		throw new Error(`模型调用失败：${failure.code ?? "ERROR"} ${failure.message ?? ""}`.trim());
	}
	if (finish?.kind === "aborted") throw new Error("模型调用已取消");
	if (finish?.kind === "length") throw new Error("模型输出被截断（达到 maxTokens），请重试");
	return {
		text,
		provider: selection.provider,
		model: selection.model,
	};
}

async function callJson(ctx, options) {
	let lastError;
	for (let attempt = 0; attempt < 2; attempt += 1) {
		const prompt = attempt === 0
			? options.prompt
			: `${options.prompt}\n\n上一次输出无法解析为 JSON。请重新输出，只输出合法 JSON，不要 markdown 代码块，不要解释文字，所有字符串保持单行。`;
		try {
			const result = await callModel(ctx, { ...options, prompt });
			return { ...result, json: parseJsonLoose(result.text) };
		} catch (error) {
			lastError = error;
			if (String(error?.message ?? "").includes("已取消")) throw error;
		}
	}
	throw lastError ?? new Error("模型没有返回可用结果");
}

function candidateBlock(candidates) {
	return candidates.map((candidate, index) => {
		const published = candidate.published_at ? candidate.published_at.slice(0, 16).replace("T", " ") : "时间未知";
		const summary = truncate(candidate.summary || "（无摘要）", 240);
		return `[${index + 1}] ${candidate.title}\n来源：${candidate.source}（${sourceTypeLabel(candidate.source_type)}）· ${published}\n摘要：${summary}`;
	}).join("\n\n");
}

function buildSignalPrompt(candidates, date, maxSignals) {
	return `# 今日候选（${date}，共 ${candidates.length} 条）

${candidateBlock(candidates)}

# 任务

从上面的候选里选出最多 ${maxSignals} 条今天最值得看的 AI 信号，按价值从高到低排序。

判断标准（满足其一即可，不必全占）：
- 出现了具体的新能力、新用法，或成本/速度/精度发生了可感知的变化
- 有可复用的方法、工作流、工程经验
- 暴露了真实的失败、限制、踩坑或安全边界
- 做了有价值的对比、评测、选型
- 提出了此前没有被满足的新问题或需求

排除：纯融资/人事/营销稿；只有口号没有具体内容的发布；同一事件的多条重复报道；无法从材料中确认的关键结论。

# 输出格式

只输出一个 JSON 对象，不要 markdown 代码块，不要解释文字：

{"signals":[{"idx":1,"track":"execution","tags":["新能力新用法"],"finding":"这条材料具体发现了什么（不超过 80 字）","why_read":"为什么值得看，对独立开发者/产品人意味着什么（不超过 70 字）","details":["来自材料的关键细节（不超过 40 字）","第二条关键细节"]}]}

规则：
- idx 必须对应上面的候选编号。
- track 只能是 "execution"（技术/论文/开源/官方能力）或 "inspiration"（社区讨论/观点/新闻/需求）。
- tags 只能从这五类里选 0–2 个：${ALLOWED_TAGS.join("、")}。
- finding 和 why_read 必须是单行、具体、可核对；不要用「值得关注」「具有重要意义」这类空话。
- details 给 2–4 条，每条都必须在材料里有依据；材料不够就少给，不要补写。
- 同一事件只保留一条。`;
}

function normalizeSignal(entry, candidate, index) {
	if (!entry || typeof entry !== "object") return null;
	const finding = truncate(entry.finding, 160);
	const whyRead = truncate(entry.why_read, 140);
	if (!finding || !whyRead) return null;
	const track = entry.track === "inspiration" || entry.track === "execution" ? entry.track : trackOf(candidate);
	const tags = Array.isArray(entry.tags)
		? entry.tags.filter((tag) => ALLOWED_TAGS.includes(tag)).slice(0, 2)
		: [];
	const details = Array.isArray(entry.details)
		? entry.details.map((detail) => truncate(detail, 80)).filter(Boolean).slice(0, MAX_DETAILS)
		: [];
	return {
		id: candidate.id,
		title: candidate.title,
		url: candidate.url,
		source: candidate.source,
		source_type: candidate.source_type,
		published_at: candidate.published_at,
		relevance_score: candidate.relevance_score,
		track,
		tags,
		finding,
		why_read: whyRead,
		evidence_note: evidenceNote(candidate),
		details,
		takeaway: finding,
		evidence: String(candidate.metadata?.engagement ?? ""),
		rank: index + 1,
	};
}

function fallbackSignals(candidates, maxSignals) {
	return candidates.slice(0, maxSignals).map((candidate, index) => {
		const text = `${candidate.title} ${candidate.summary}`;
		return {
			id: candidate.id,
			title: candidate.title,
			url: candidate.url,
			source: candidate.source,
			source_type: candidate.source_type,
			published_at: candidate.published_at,
			relevance_score: candidate.relevance_score,
			track: trackOf(candidate),
			tags: inferTags(text),
			finding: truncate(candidate.summary || candidate.title, 160),
			why_read: `来自${candidate.source}的新信号，建议结合原文判断。`,
			evidence_note: evidenceNote(candidate),
			details: [],
			takeaway: truncate(candidate.summary || candidate.title, 160),
			evidence: String(candidate.metadata?.engagement ?? ""),
			rank: index + 1,
			fallback: true,
		};
	});
}

export async function analyzeSignals(ctx, candidates, date, { maxSignals = 5, signal } = {}) {
	if (candidates.length === 0) return { signals: [], model: null, warning: "没有抓到候选内容，请稍后重试或检查网络。" };
	const prompt = buildSignalPrompt(candidates, date, maxSignals);
	try {
		const result = await callJson(ctx, { system: SYSTEM, prompt, maxTokens: 5000, signal });
		const payload = Array.isArray(result.json) ? { signals: result.json } : result.json;
		const entries = Array.isArray(payload?.signals) ? payload.signals : [];
		const picked = [];
		const used = new Set();
		for (const entry of entries) {
			if (picked.length >= maxSignals) break;
			const idx = Number(entry?.idx);
			if (!Number.isInteger(idx) || idx < 1 || idx > candidates.length || used.has(idx)) continue;
			const normalized = normalizeSignal(entry, candidates[idx - 1], picked.length);
			if (!normalized) continue;
			used.add(idx);
			picked.push(normalized);
		}
		if (picked.length === 0) throw new Error("模型没有选出可用信号");
		return { signals: picked, model: result.model, provider: result.provider, warning: null };
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		return {
			signals: fallbackSignals(candidates, maxSignals),
			model: null,
			warning: `AI 精选失败，已回退为候选摘要：${message}`,
		};
	}
}

function signalBlock(signals) {
	return signals.map((item, index) => {
		return `[${index + 1}] ${item.title}\n来源：${item.source}\n发现了什么：${item.finding}\n为什么值得看：${item.why_read}`;
	}).join("\n\n");
}

function buildOpportunityPrompt(signals, date) {
	return `# 今日已选信号（${date}）

${signalBlock(signals)}

# 任务

基于上面的信号，输出两组机会：

A. 商业机会（2–3 个）：面向独立开发者，一个月内能做出 MVP，有明确的目标用户和付费理由。
B. 研发机会（2–3 个）：面向互联网公司研发团队，能插入现有工具链/工作流，减少重复劳动或提升业务转化。

要求：
- 每个机会都必须能回答「信号里的哪个具体能力，让这件事现在可行」，禁止只从标题联想。
- 找不到清晰因果链就不要硬凑；宁可少给。
- 不要写「提升效率」「赋能业务」这类空话，要具体到场景、动作和集成形态。
- 所有字符串保持单行，不要换行。

# 输出格式

只输出一个 JSON 对象，不要 markdown 代码块，不要解释文字：

{"business":[{"source_idx":1,"title":"产品方向名称（30字以内）","trigger":"信号中的具体触发点（30字以内）","core_insight":"这个能力如何支撑产品、之前为何不可行（60字以内）","product_form":"帮助[目标用户]解决[具体问题]的[产品类型]","target_users":"用户画像：职业/场景/痛点/付费意愿（40字以内）","mvp_features":["核心功能1","核心功能2","核心功能3"],"business_model":"盈利方式及定价（30字以内）","risks":"最大风险（40字以内）","scores":{"pain_point":4,"market_size":3,"tech_timing":5,"buildability":4}}],"rdev":[{"source_idx":2,"type":"研发提效","title":"方案名称（20字以内）","trigger":"信号中的具体触发点（30字以内）","scenario":"在[具体场景]中，目前做法是[现有做法]，痛点是[问题]（80字以内）","ai_solution":"新技术如何重构这个场景，边界在哪里（80字以内）","implementation":"具体集成形态，如 VS Code 插件 / GitLab Webhook / 飞书机器人（60字以内）","audience":["大前端"],"impact":"量化预期收益（50字以内）","difficulty":"低","resistance":"推进的主要阻力（40字以内）","scores":{"efficiency":8,"feasibility":7,"business_impact":6,"overall":8}}]}

规则：
- source_idx 对应上面的信号编号。
- 商业机会 scores 每项 1–5；研发机会 scores 每项 1–10。
- 商业机会 type 不需要；研发机会 type 只能是「研发提效」或「业务赋能」。
- 研发机会 difficulty 只能是「低」「中」「高」；audience 从「大前端、客户端、后端、测试、产品运营、技术TL」中选。
- 每组最多 3 个，没有就返回空数组。`;
}

function intInRange(value, min, max, fallback) {
	const number = Number(value);
	if (!Number.isFinite(number)) return fallback;
	return Math.max(min, Math.min(max, Math.round(number)));
}

function normalizeBusiness(entry, signals, index) {
	if (!entry || typeof entry !== "object") return null;
	const sourceIdx = Number(entry.source_idx);
	const source = signals[Number.isInteger(sourceIdx) && sourceIdx >= 1 && sourceIdx <= signals.length ? sourceIdx - 1 : index % signals.length];
	const title = truncate(entry.title, 60);
	const insight = truncate(entry.core_insight, 160);
	if (!title || !insight) return null;
	const scores = entry.scores ?? {};
	const normalizedScores = {
		pain_point: intInRange(scores.pain_point, 1, 5, 3),
		market_size: intInRange(scores.market_size, 1, 5, 3),
		tech_timing: intInRange(scores.tech_timing, 1, 5, 3),
		buildability: intInRange(scores.buildability, 1, 5, 3),
	};
	return {
		title,
		trigger: truncate(entry.trigger, 80),
		core_insight: insight,
		product_form: truncate(entry.product_form, 120),
		target_users: truncate(entry.target_users, 100),
		mvp_features: Array.isArray(entry.mvp_features) ? entry.mvp_features.map((feature) => truncate(feature, 60)).filter(Boolean).slice(0, 4) : [],
		business_model: truncate(entry.business_model, 80),
		risks: truncate(entry.risks, 100),
		scores: normalizedScores,
		total_score: Object.values(normalizedScores).reduce((sum, value) => sum + value, 0),
		source_title: source?.title ?? "",
		source_url: source?.url ?? "",
		source_name: source?.source ?? "",
	};
}

function normalizeRdev(entry, signals, index) {
	if (!entry || typeof entry !== "object") return null;
	const sourceIdx = Number(entry.source_idx);
	const source = signals[Number.isInteger(sourceIdx) && sourceIdx >= 1 && sourceIdx <= signals.length ? sourceIdx - 1 : index % signals.length];
	const title = truncate(entry.title, 40);
	const scenario = truncate(entry.scenario, 180);
	if (!title || !scenario) return null;
	const scores = entry.scores ?? {};
	const normalizedScores = {
		efficiency: intInRange(scores.efficiency, 1, 10, 6),
		feasibility: intInRange(scores.feasibility, 1, 10, 6),
		business_impact: intInRange(scores.business_impact, 1, 10, 6),
		overall: intInRange(scores.overall, 1, 10, 6),
	};
	const difficulty = ["低", "中", "高"].includes(entry.difficulty) ? entry.difficulty : "中";
	const audiences = ["大前端", "客户端", "后端", "测试", "产品运营", "技术TL"];
	return {
		type: entry.type === "业务赋能" ? "业务赋能" : "研发提效",
		title,
		trigger: truncate(entry.trigger, 80),
		scenario,
		ai_solution: truncate(entry.ai_solution, 180),
		implementation: truncate(entry.implementation, 120),
		audience: Array.isArray(entry.audience) ? entry.audience.filter((item) => audiences.includes(item)).slice(0, 4) : [],
		impact: truncate(entry.impact, 100),
		difficulty,
		resistance: truncate(entry.resistance, 100),
		scores: normalizedScores,
		total_score: normalizedScores.overall,
		source_title: source?.title ?? "",
		source_url: source?.url ?? "",
		source_name: source?.source ?? "",
	};
}

export async function analyzeOpportunities(ctx, signals, date, { signal } = {}) {
	if (signals.length === 0) return { business: [], rdev: [], model: null };
	const prompt = buildOpportunityPrompt(signals, date);
	const result = await callJson(ctx, { system: OPPORTUNITY_SYSTEM, prompt, maxTokens: 7000, signal });
	const payload = result.json;
	const business = (Array.isArray(payload?.business) ? payload.business : [])
		.map((entry, index) => normalizeBusiness(entry, signals, index))
		.filter(Boolean)
		.slice(0, 3);
	const rdev = (Array.isArray(payload?.rdev) ? payload.rdev : [])
		.map((entry, index) => normalizeRdev(entry, signals, index))
		.filter(Boolean)
		.slice(0, 3);
	return { business, rdev, model: result.model, provider: result.provider };
}

export { ALLOWED_TAGS, SYSTEM, OPPORTUNITY_SYSTEM };

/* ------------------------------------------------------------------ *
 * Chinese quick-reads for every candidate
 * ------------------------------------------------------------------ */

const ENRICH_SYSTEM = `你是 SignalForge 的中文情报编辑。你的读者是一位独立开发者 / AI 产品人。你要把当天抓到的每一条候选都写成简短、具体、可核对的中文速读，而不是翻译标题。

只使用给定材料，不补充材料之外的事实，不编造数字、结论或因果关系。英文材料要提炼成中文，不要在 finding 里原样复制英文标题。`;

function buildEnrichPrompt(batch, date) {
	const block = batch.map((item, index) => {
		const summary = truncate(item.summary || "（无摘要）", 260);
		return `[${index + 1}] ${item.title}\n来源：${item.source}（${item.category || sourceTypeLabel(item.source_type)}）\n摘要：${summary}`;
	}).join("\n\n");
	return `# 今日候选批次（${date}，共 ${batch.length} 条）

${block}

# 任务

为上面每一条候选写中文速读。必须逐条输出，不能漏条目。

# 输出格式

只输出一个 JSON 对象，不要 markdown 代码块，不要解释文字：

{"items":[{"idx":1,"finding":"发现了什么（30–70字，具体事实）","why_read":"为什么值得看（20–50字，对独立开发者/产品人的实际含义）","tags":["新能力新用法"],"details":["关键细节（不超过 40 字）","第二条关键细节"]}]}

规则：
- idx 对应上面的候选编号。
- finding 必须是简体中文，写清这条材料具体说了什么；不要用「值得关注」「具有重要意义」这类空话，也不要把英文标题原样抄过来。
- why_read 必须是简体中文，写清对独立开发者 / 产品人的含义；不要重复 finding。
- tags 只能从这五类里选 0–2 个：${ALLOWED_TAGS.join("、")}。
- details 给 0–2 条，每条都必须在材料里有依据；材料不够就返回空数组。
- 所有字符串保持单行，不要换行。
- 纯商业融资、人事、营销稿如果材料里没有可用信息，finding 写清楚「这是一条融资/人事/营销信息」，why_read 写「对产品判断帮助有限，可跳过」。`;
}

function hasChinese(text) {
	return /[\u4e00-\u9fff]/.test(String(text ?? ""));
}

export async function enrichItems(ctx, items, { signal, date = "今日", batchSize = 18, concurrency = 2, onProgress } = {}) {
	const list = Array.isArray(items) ? items : [];
	if (list.length === 0) return { items: list, warning: null, enriched: 0, total: 0 };

	const batches = [];
	for (let offset = 0; offset < list.length; offset += batchSize) {
		batches.push({ offset, items: list.slice(offset, offset + batchSize) });
	}

	const collected = new Map();
	const failures = [];
	let done = 0;
	let next = 0;

	async function worker() {
		while (true) {
			const index = next;
			next += 1;
			if (index >= batches.length) return;
			const batch = batches[index];
			try {
				const result = await callJson(ctx, {
					system: ENRICH_SYSTEM,
					prompt: buildEnrichPrompt(batch.items, date),
					maxTokens: 6000,
					signal,
				});
				const payload = Array.isArray(result.json) ? result.json : result.json?.items;
				const entries = Array.isArray(payload) ? payload : [];
				for (const entry of entries) {
					if (!entry || typeof entry !== "object") continue;
					const raw = Number(entry.idx);
					if (!Number.isInteger(raw) || raw < 1) continue;
					let global = batch.offset + raw - 1;
					if (raw > batch.items.length && raw <= list.length) global = raw - 1;
					if (global < 0 || global >= list.length) continue;
					const finding = truncate(entry.finding, 120);
					const whyRead = truncate(entry.why_read, 100);
					if (!finding || !whyRead || !hasChinese(finding) || !hasChinese(whyRead)) continue;
					const tags = Array.isArray(entry.tags)
						? entry.tags.filter((tag) => ALLOWED_TAGS.includes(tag)).slice(0, 2)
						: [];
					const details = Array.isArray(entry.details)
						? entry.details.map((detail) => truncate(detail, 70)).filter((detail) => detail && hasChinese(detail)).slice(0, 2)
						: [];
					collected.set(global, { finding, why_read: whyRead, tags, details, enriched: true });
				}
			} catch (error) {
				failures.push(error instanceof Error ? error.message : String(error));
			} finally {
				done += 1;
				onProgress?.({ done, total: batches.length, enriched: collected.size });
			}
		}
	}

	await Promise.all(Array.from({ length: Math.min(concurrency, batches.length) }, worker));
	const merged = list.map((item, index) => {
		const category = item.category || categoryOf(item);
		const quick = collected.get(index);
		return quick ? { ...item, category, ...quick } : { ...item, category };
	});
	const warning = failures.length > 0
		? `${failures.length} 个速读批次失败，相关候选保留原始摘要：${failures[0]}`
		: null;
	return { items: merged, warning, enriched: collected.size, total: list.length };
}

export { ENRICH_SYSTEM };
