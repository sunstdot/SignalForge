import { analyzeOpportunities, analyzeSignals, enrichItems } from "./analyze.js";
import { collectCandidates } from "./sources.js";
import { addDays, isDate, todayInZone } from "./util.js";

const DEFAULTS = {
	timezone: "Asia/Shanghai",
	maxSignals: 5,
	lookbackHours: 48,
	sourceTimeoutMs: 16000,
};

function publicJob(job, { includeDigest = false } = {}) {
	if (!job) return null;
	return {
		id: job.id,
		date: job.date,
		mode: job.mode,
		status: job.status,
		stage: job.stage,
		message: job.message,
		startedAt: job.startedAt,
		finishedAt: job.finishedAt,
		error: job.error,
		progress: { ...job.progress },
		...(includeDigest && job.digest ? { digest: job.digest } : {}),
	};
}

export function createPipeline({ ctx, store, config = {}, logger } = {}) {
	const settings = {
		...DEFAULTS,
		...Object.fromEntries(Object.entries(config).filter(([, value]) => value !== undefined)),
	};
	const timezone = String(settings.timezone || DEFAULTS.timezone);
	const maxSignals = Math.max(1, Math.min(8, Number(settings.maxSignals) || DEFAULTS.maxSignals));
	const lookbackHours = Math.max(6, Math.min(168, Number(settings.lookbackHours) || DEFAULTS.lookbackHours));
	const sourceTimeoutMs = Math.max(4000, Math.min(30000, Number(settings.sourceTimeoutMs) || DEFAULTS.sourceTimeoutMs));

	let active = null;
	let disposed = false;

	function today() {
		return todayInZone(timezone);
	}

	function setStage(job, stage, message) {
		job.stage = stage;
		job.message = message;
		logger?.info?.(`[signalforge] ${job.date} ${stage}: ${message}`);
	}

	async function run(job) {
		const date = job.date;
		setStage(job, "sources", "抓取今日 AI 资讯来源…");
		const collection = await collectCandidates({
			lookbackHours,
			timeoutMs: sourceTimeoutMs,
			signal: job.controller.signal,
			onProgress: (progress) => {
				job.progress.sourceDone = progress.done;
				job.progress.sourceTotal = progress.total;
				job.message = progress.source === "开始抓取"
					? `准备抓取 ${progress.total} 个来源…`
					: `抓取 ${progress.source}（${progress.done}/${progress.total}）`;
			},
		});
		job.progress.candidates = collection.allCount;
		job.progress.selected = collection.candidates.length;

		const okSources = collection.stats.filter((item) => item.ok).length;
		setStage(
			job,
			"signals",
			`已从 ${okSources} 个来源抓到 ${collection.allCount} 条候选，AI 正在精选今日信号…`,
		);

		const signalResult = await analyzeSignals(ctx, collection.candidates, date, {
			maxSignals,
			signal: job.controller.signal,
		});
		job.progress.signals = signalResult.signals.length;

		let opportunityResult = { business: [], rdev: [] };
		let opportunitiesError = null;
		if (signalResult.signals.length > 0) {
			setStage(job, "opportunities", "AI 正在从今日信号里挖掘商业与研发机会…");
			try {
				opportunityResult = await analyzeOpportunities(ctx, signalResult.signals, date, {
					signal: job.controller.signal,
				});
			} catch (error) {
				opportunitiesError = error instanceof Error ? error.message : String(error);
			}
		}
		job.progress.opportunities = (opportunityResult.business?.length ?? 0) + (opportunityResult.rdev?.length ?? 0);

		let items = Array.isArray(collection.all) ? collection.all : [];
		let enrichmentWarning = null;
		let enrichedCount = 0;
		if (items.length > 0) {
			job.progress.enrichTotal = items.length;
			setStage(job, "enrich", `AI 正在为全部 ${items.length} 条候选写中文速读…`);
			try {
				const enriched = await enrichItems(ctx, items, {
					date,
					signal: job.controller.signal,
					onProgress: (progress) => {
						job.progress.enriched = progress.enriched;
						job.message = `AI 正在写中文速读（${progress.done}/${progress.total} 批，已完成 ${progress.enriched} 条）`;
					},
				});
				items = enriched.items;
				enrichedCount = enriched.enriched;
				enrichmentWarning = enriched.warning;
			} catch (error) {
				enrichmentWarning = error instanceof Error ? error.message : String(error);
			}
		}

		const generatedAt = new Date().toISOString();
		const warning = signalResult.warning
			?? (opportunitiesError ? `机会分析失败：${opportunitiesError}` : null)
			?? enrichmentWarning;
		const digest = {
			version: 1,
			date,
			timezone,
			generatedAt,
			analysis: {
				provider: signalResult.provider ?? opportunityResult.provider ?? null,
				model: signalResult.model ?? opportunityResult.model ?? null,
				maxSignals,
				warning,
				opportunitiesError,
				enrichmentError: enrichmentWarning,
			},
			stats: {
				candidates: items.length,
				selected: collection.candidates.length,
				enriched: enrichedCount,
				okSources,
				sourceTotal: collection.stats.length,
				elapsedMs: collection.elapsedMs,
				totalMs: Date.now() - Date.parse(job.startedAt),
				sources: collection.stats,
			},
			items,
			signals: signalResult.signals,
			opportunities: {
				generatedAt: opportunitiesError ? null : generatedAt,
				business: opportunityResult.business ?? [],
				rdev: opportunityResult.rdev ?? [],
			},
		};

		setStage(job, "saving", "保存今日情报…");
		await store.saveDigest(digest);
		job.digest = digest;
		job.status = "done";
		job.stage = "done";
		job.message = `完成：${digest.signals.length} 条信号，${digest.opportunities.business.length + digest.opportunities.rdev.length} 个机会`;
		job.finishedAt = new Date().toISOString();
		logger?.info?.(`[signalforge] ${date} done`);
	}

	function fail(job, error) {
		const aborted = job.controller.signal.aborted;
		job.status = aborted ? "cancelled" : "error";
		job.stage = aborted ? "cancelled" : "error";
		job.message = aborted ? "已取消" : (job.mode === "enrich" ? "补全速读失败" : "获取失败");
		job.error = aborted ? null : error instanceof Error ? error.message : String(error);
		job.finishedAt = new Date().toISOString();
		if (!aborted) logger?.warn?.(`[signalforge] ${job.date} failed: ${job.error}`);
	}

	async function runEnrich(job, digest) {
		const allItems = Array.isArray(digest.items) ? digest.items : [];
		const pending = allItems.filter((item) => !item.finding || !item.why_read);
		job.progress.enrichTotal = pending.length;
		if (pending.length === 0) {
			job.status = "done";
			job.stage = "done";
			job.message = "全部候选都已有中文速读";
			job.finishedAt = new Date().toISOString();
			return;
		}
		setStage(job, "enrich", `AI 正在为 ${pending.length} 条缺少速读的候选补中文…`);
		const result = await enrichItems(ctx, pending, {
			date: job.date,
			signal: job.controller.signal,
			onProgress: (progress) => {
				job.progress.enriched = progress.enriched;
				job.message = `AI 正在补中文速读（${progress.done}/${progress.total} 批，已完成 ${progress.enriched} 条）`;
			},
		});
		const updated = new Map(result.items.map((item) => [item.id, item]));
		digest.items = allItems.map((item) => updated.get(item.id) ?? item);
		const enrichedTotal = digest.items.filter((item) => item.finding && item.why_read).length;
		const previousAnalysis = digest.analysis ?? {};
		const warningWasEnrichment = typeof previousAnalysis.warning === "string" && previousAnalysis.warning.includes("速读批次");
		digest.analysis = {
			...previousAnalysis,
			warning: warningWasEnrichment ? result.warning : previousAnalysis.warning ?? null,
			enrichmentError: result.warning,
			enrichedAt: new Date().toISOString(),
		};
		digest.stats = {
			...(digest.stats ?? {}),
			candidates: digest.items.length,
			enriched: enrichedTotal,
		};
		setStage(job, "saving", "保存中文速读…");
		await store.saveDigest(digest);
		job.digest = digest;
		job.status = "done";
		job.stage = "done";
		job.message = `补全完成：${result.enriched}/${result.total} 条（总计 ${enrichedTotal}/${digest.items.length}）`;
		job.finishedAt = new Date().toISOString();
		logger?.info?.(`[signalforge] ${job.date} enrichment done`);
	}

	async function startEnrich(date) {
		if (disposed) throw new Error("插件已卸载");
		if (!isDate(date)) throw new Error("日期格式必须是 YYYY-MM-DD");
		if (active && active.status === "running") {
			return { job: publicJob(active), reused: true };
		}
		const digest = await store.loadDigest(date);
		if (!digest) throw new Error("这一天还没有情报，先获取一次再补速读");
		const items = Array.isArray(digest.items) ? digest.items : [];
		if (items.length === 0) throw new Error("这一天还没有候选明细，先重新获取一次");
		if (active && active.status === "running") {
			return { job: publicJob(active), reused: true };
		}
		const job = {
			id: `job-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
			date,
			mode: "enrich",
			status: "running",
			stage: "enrich",
			message: `准备补全 ${items.length} 条候选的中文速读…`,
			startedAt: new Date().toISOString(),
			finishedAt: null,
			error: null,
			progress: {
				sourceDone: 0,
				sourceTotal: 0,
				candidates: items.length,
				selected: 0,
				signals: 0,
				opportunities: 0,
				enrichTotal: items.length,
				enriched: 0,
			},
			digest: null,
			controller: new AbortController(),
		};
		active = job;
		job.promise = runEnrich(job, digest).catch((error) => fail(job, error));
		return { job: publicJob(job), reused: false };
	}

	function start(date) {
		if (disposed) throw new Error("插件已卸载");
		if (!isDate(date)) throw new Error("日期格式必须是 YYYY-MM-DD");
		if (date !== today()) throw new Error("只能获取今天的情报；历史日期可以查看已生成的结果");
		if (active && active.status === "running") {
			return { job: publicJob(active), reused: true };
		}
		const job = {
			id: `job-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
			date,
			mode: "full",
			status: "running",
			stage: "sources",
			message: "准备抓取…",
			startedAt: new Date().toISOString(),
			finishedAt: null,
			error: null,
			progress: {
				sourceDone: 0,
				sourceTotal: 0,
				candidates: 0,
				selected: 0,
				signals: 0,
				opportunities: 0,
				enrichTotal: 0,
				enriched: 0,
			},
			digest: null,
			controller: new AbortController(),
		};
		active = job;
		job.promise = run(job).catch((error) => fail(job, error));
		return { job: publicJob(job), reused: false };
	}

	function get(id) {
		if (!active || active.id !== id) return null;
		return publicJob(active, { includeDigest: true });
	}

	function current() {
		if (!active || active.status !== "running") return null;
		return publicJob(active);
	}

	function cancel(id) {
		if (!active || active.id !== id || active.status !== "running") return false;
		active.controller.abort();
		return true;
	}

	function dispose() {
		disposed = true;
		if (active && active.status === "running") active.controller.abort();
	}

	return {
		start,
		startEnrich,
		get,
		current,
		cancel,
		dispose,
		today,
		addDays,
		settings: { timezone, maxSignals, lookbackHours, sourceTimeoutMs },
	};
}
