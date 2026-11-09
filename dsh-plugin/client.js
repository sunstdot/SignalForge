window.__ModuleLoader__.load({
	id: "dsh-signalforge",
	factory(require) {
		const React = require("react");
		const h = React.createElement;
		const { useState, useEffect, useMemo, useRef } = React;

		const NS = "signalforge";
		const API = "/signalforge/api";

		/* ------------------------------------------------------------------ *
		 * Copy
		 * ------------------------------------------------------------------ */

		const ZH = {
			panel: "今日 AI 情报",
			title: "今日 AI 情报",
			subtitle: "从今天的 AI 资讯里精选信号，并用当前账号挖出可以落地的商业与研发机会。",
			fetch: "获取今日资讯",
			regenerate: "重新获取今日资讯",
			refreshing: "正在获取…",
			onlyToday: "仅当天可获取",
			backToday: "回到今天",
			prevDay: "更早的日期",
			nextDay: "更新的日期",
			tabSignals: "今日 AI 情报",
			tabOpps: "今日 AI 情报机会",
			tabAll: "全部情报",
			signalsUnit: "条信号",
			oppsUnit: "个机会",
			itemsUnit: "条",
			allHint: "本次抓取的全部候选，含未入选信号；点标题查看原文。",
			searchPlaceholder: "搜索标题、来源或摘要",
			categoryAll: "全部内容",
			notEnrichedTitle: "有候选还没有中文速读",
			notEnrichedHint: "条候选目前只有原始摘要。补全后每条都会有「发现了什么 / 为什么值得看」。",
			enrichAction: "补全中文速读",
			enriching: "正在补全…",
			rawSummary: "原始摘要",
			notEnriched: "这条还没有中文速读。",
			noItemsTitle: "这次没有保存候选明细",
			noItemsHint: "重新获取一次今日资讯，就会把全部候选一起保存下来。",
			noItemsPastHint: "这一天归档时没有保存候选明细；精选信号仍然可以回看。",
			noMatch: "没有匹配的候选",
			noMatchHint: "换个关键词，或把来源切回「全部来源」。",
			relevance: "相关度",
			loading: "加载中…",
			emptyTitle: "今天还没有情报",
			emptyHint: "点击「获取今日资讯」，抓取今天的 AI 来源，并用当前 DeepSeek 账号分析。全部候选会补中文速读，通常需要 2–3 分钟。",
			emptyPastTitle: "这一天还没有生成情报",
			emptyPastHint: "获取只对当天生效。回到今天生成后，就可以按天回看。",
			noSignals: "没有选出信号",
			noSignalsHint: "候选材料不足，或今天的信号质量不够。可以重新获取一次。",
			noSignalsPastHint: "这一天归档时没有选出信号。",
			noOpps: "还没有机会分析",
			noOppsHint: "机会从今日信号里生长出来。先生成或重新获取今日情报。",
			noOppsPastHint: "这一天归档时没有生成机会分析；上面的信号仍然可以回看。",
			findingLabel: "发现了什么：",
			whyLabel: "为什么值得看：",
			evidenceLabel: "依据与边界：",
			aiBadge: "AI 速读",
			verify: "请核对原文",
			viewOriginal: "查看原文 ↗",
			continueChat: "继续对话",
			readPaper: "精读论文",
			paperReadTitle: "论文精读",
			paperReadHint: "情报里没有的论文，可以粘贴 arXiv / DOI / PDF 链接，或标题 + 摘要。",
			paperPlaceholder: "粘贴 arXiv / DOI / PDF 链接，或标题 + 摘要…",
			paperStart: "开始精读",
			paperStarting: "准备中…",
			chatCopied: "文章信息已复制，去对话里粘贴即可继续。",
			chatUnavailable: "当前 Harness 组合没有可用的对话服务，无法打开新对话。",
			showDetails: "展开细节",
			hideDetails: "收起细节",
			detailsTitle: "关键信息",
			sourceCoverage: "来源覆盖",
			candidates: "候选",
			selected: "入选",
			model: "分析模型",
			accountNote: "AI 分析使用当前 DeepSeek 账号",
			generatedAt: "生成于",
			business: "商业机会",
			rdev: "研发机会",
			businessHint: "面向独立开发者，一个月内能做出 MVP 的方向。",
			rdevHint: "面向研发团队，能插进现有工作流的提效方案。",
			trigger: "触发点",
			insight: "趋势判断",
			form: "可以怎么做",
			users: "目标用户",
			mvp: "MVP 功能",
			businessModel: "商业模式",
			risk: "最大风险",
			scenario: "场景与痛点",
			aiSolution: "AI 怎么做",
			implementation: "集成形态",
			audience: "适用团队",
			impact: "预期收益",
			difficulty: "落地难度",
			resistance: "推进阻力",
			score: "评分",
			source: "来源",
			retry: "重试",
			error: "出错了",
			cancelled: "已取消",
			warning: "提示",
			stageSources: "抓取资讯来源",
			stageSignals: "AI 精选今日信号",
			stageOpportunities: "AI 挖掘今日机会",
			stageEnrich: "AI 补全中文速读",
			stageSaving: "保存结果",
			stageDone: "完成",
			elapsed: "已用时",
			seconds: "秒",
			history: "历史",
			noDates: "还没有历史",
			jobRunning: "正在生成今日情报",
			statsLine: "精选 {signals} 条（不凑数）· 候选 {candidates} 条 · {sources} 个来源已抓取",
			dateLabel: "日期",
			todayLabel: "今天",
		};

		const EN = {
			panel: "Daily AI Brief",
			title: "Daily AI Brief",
			subtitle: "Pick today's AI signals and turn them into buildable business and engineering opportunities with your current account.",
			fetch: "Get today's brief",
			regenerate: "Regenerate today's brief",
			refreshing: "Fetching…",
			onlyToday: "Today only",
			backToday: "Back to today",
			prevDay: "Older date",
			nextDay: "Newer date",
			tabSignals: "Signals",
			tabOpps: "Opportunities",
			tabAll: "All intel",
			signalsUnit: "signals",
			oppsUnit: "opportunities",
			itemsUnit: "items",
			allHint: "Every candidate fetched in this run, including ones that were not selected. Open the title to read the source.",
			searchPlaceholder: "Search title, source or summary",
			categoryAll: "All",
			notEnrichedTitle: "Some candidates have no Chinese quick-read yet",
			notEnrichedHint: "candidates only have their original summary. Enrich them to add “what was found / why it matters”.",
			enrichAction: "Enrich quick-reads",
			enriching: "Enriching…",
			rawSummary: "Original summary",
			notEnriched: "This item has no Chinese quick-read yet.",
			noItemsTitle: "This run did not store candidate details",
			noItemsHint: "Fetch today's brief again to save every candidate alongside the selected signals.",
			noItemsPastHint: "This archived day did not store candidate details; its selected signals are still readable.",
			noMatch: "No matching candidates",
			noMatchHint: "Try another keyword, or switch the source filter back to all sources.",
			relevance: "relevance",
			loading: "Loading…",
			emptyTitle: "No brief for today yet",
			emptyHint: "Click “Get today's brief” to fetch today's AI sources and analyze them with the current DeepSeek account. Chinese quick-reads are written for every candidate; it usually takes 2–3 minutes.",
			emptyPastTitle: "No brief for this day",
			emptyPastHint: "Fetching only works for today. Generate today first, then browse by day.",
			noSignals: "No signals selected",
			noSignalsHint: "There was not enough good material. Try fetching again.",
			noSignalsPastHint: "This archived day has no selected signals.",
			noOpps: "No opportunity analysis yet",
			noOppsHint: "Opportunities grow out of the selected signals. Generate today's brief first.",
			noOppsPastHint: "This archived day has no opportunity analysis; its signals are still readable.",
			findingLabel: "What was found: ",
			whyLabel: "Why it matters: ",
			evidenceLabel: "Evidence & limits: ",
			aiBadge: "AI read",
			verify: "verify the source",
			viewOriginal: "Open source ↗",
			continueChat: "Discuss with AI",
			readPaper: "Read paper",
			paperReadTitle: "Paper reader",
			paperReadHint: "For papers outside the digest, paste an arXiv / DOI / PDF link, or a title + abstract.",
			paperPlaceholder: "Paste an arXiv / DOI / PDF link, or a title + abstract…",
			paperStart: "Start reading",
			paperStarting: "Preparing…",
			chatCopied: "Article details copied — paste them into a conversation to continue.",
			chatUnavailable: "This Harness composition has no conversation service to open a new chat.",
			showDetails: "Show details",
			hideDetails: "Hide details",
			detailsTitle: "Key facts",
			sourceCoverage: "Source coverage",
			candidates: "candidates",
			selected: "selected",
			model: "Model",
			accountNote: "Analysis uses the current DeepSeek account",
			generatedAt: "Generated",
			business: "Business opportunities",
			rdev: "Engineering opportunities",
			businessHint: "Directions an independent developer can ship an MVP for within a month.",
			rdevHint: "Ways a product team can insert AI into its existing workflow.",
			trigger: "Trigger",
			insight: "Insight",
			form: "What to build",
			users: "Target users",
			mvp: "MVP features",
			businessModel: "Business model",
			risk: "Biggest risk",
			scenario: "Scenario & pain",
			aiSolution: "How AI helps",
			implementation: "Integration",
			audience: "Teams",
			impact: "Expected impact",
			difficulty: "Difficulty",
			resistance: "Resistance",
			score: "Score",
			source: "Source",
			retry: "Retry",
			error: "Something went wrong",
			cancelled: "Cancelled",
			warning: "Notice",
			stageSources: "Fetching sources",
			stageSignals: "Selecting signals",
			stageOpportunities: "Mining opportunities",
			stageEnrich: "Writing Chinese quick-reads",
			stageSaving: "Saving",
			stageDone: "Done",
			elapsed: "Elapsed",
			seconds: "s",
			history: "History",
			noDates: "No history yet",
			jobRunning: "Generating today's brief",
			statsLine: "{signals} signals (no filler) · {candidates} candidates · {sources} sources fetched",
			dateLabel: "Date",
			todayLabel: "Today",
		};

		/* ------------------------------------------------------------------ *
		 * Helpers
		 * ------------------------------------------------------------------ */

		function useT(props) {
			const bound = props && typeof props.t === "function" ? props.t : null;
			return useMemo(() => {
				return function t(key) {
					if (bound) {
						const value = bound(key);
						if (typeof value === "string") return value;
					}
					return ZH[key] || key;
				};
			}, [bound]);
		}

		function formatDateCn(date) {
			if (!date) return "";
			const time = Date.parse(`${date}T12:00:00Z`);
			if (!Number.isFinite(time)) return date;
			const names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
			return `${date} · ${names[new Date(time).getUTCDay()]}`;
		}

		const CATEGORY_ORDER = ["论文", "仓库", "模型", "资讯", "AI公司博客", "微信公众号资讯", "Smol 资讯", "投资者资讯"];
		const CATEGORY_COLORS = {
			"论文": "#6366f1",
			"仓库": "#0ea5e9",
			"模型": "#10b981",
			"资讯": "#f59e0b",
			"AI公司博客": "#06b6d4",
			"微信公众号资讯": "#22c55e",
			"Smol 资讯": "#f97316",
			"投资者资讯": "#ef4444",
		};

		function itemCategory(item) {
			if (item && typeof item.category === "string" && item.category) return item.category;
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

		function categoryColor(category) {
			return CATEGORY_COLORS[category] || "var(--dsw-alias-label-tertiary)";
		}

		function isPaper(item) {
			return itemCategory(item) === "论文" || item?.source_type === "arxiv" || item?.source_type === "paper";
		}

		function evidenceFor(item) {
			const metadata = item?.metadata ?? {};
			const type = item?.source_type;
			const category = itemCategory(item);
			const parts = [];
			if (type === "hn" || type === "reddit" || type === "x") parts.push("社区热榜（转述/讨论，非独立验证）");
			else if (type === "arxiv" || type === "paper") parts.push("论文摘要（未经同行评审与原文核验）");
			else if (type === "repo" || type === "github") parts.push("开源仓库（README 与代码未核验）");
			else if (category === "AI公司博客") parts.push("官方材料");
			else if (type === "newsletter") parts.push("作者 Newsletter（观点与转述）");
			else if (type === "news") parts.push("媒体转述");
			else parts.push("作者博客（观点与转述）");
			const engagement = String(metadata.engagement ?? "").trim();
			if (engagement) parts.push(`互动数据：${engagement}`);
			return parts.join(" · ");
		}

		function formatTime(value) {
			if (!value) return "";
			const time = Date.parse(value);
			if (!Number.isFinite(time)) return "";
			const date = new Date(time);
			const pad = (number) => String(number).padStart(2, "0");
			return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
		}

		function pluralize(t, count, unitKey) {
			return `${count} ${t(unitKey)}`;
		}

		async function request(path, options = {}) {
			const response = await fetch(`${API}${path}`, {
				cache: "no-store",
				...options,
				headers: {
					...(options.body ? { "content-type": "application/json" } : {}),
					...(options.headers || {}),
				},
			});
			let data = null;
			try {
				data = await response.json();
			} catch {
				data = null;
			}
			return { status: response.status, ok: response.ok, data };
		}

		function errorText(result) {
			if (result?.data && typeof result.data.error === "string") return result.data.error;
			return result?.status ? `HTTP ${result.status}` : "网络请求失败";
		}

		/* ------------------------------------------------------------------ *
		 * Icons
		 * ------------------------------------------------------------------ */

		function iconProps(size) {
			return {
				width: size,
				height: size,
				viewBox: "0 0 16 16",
				fill: "none",
				stroke: "currentColor",
				strokeWidth: 1.4,
				strokeLinecap: "round",
				strokeLinejoin: "round",
				"aria-hidden": true,
				focusable: false,
			};
		}

		function SignalForgeIcon({ size, active }) {
			const s = typeof size === "number" ? size : 16;
			return h(
				"svg",
				{
					width: s,
					height: s,
					viewBox: "0 0 16 16",
					fill: "none",
					stroke: "currentColor",
					strokeWidth: active ? 1.55 : 1.3,
					strokeLinecap: "round",
					strokeLinejoin: "round",
					"aria-hidden": true,
					focusable: false,
				},
				h("path", { d: "M2.2 13.2a8.6 8.6 0 0 1 11.6 0", opacity: 0.45 }),
				h("path", { d: "M4.6 11.4a5.6 5.6 0 0 1 6.8 0", opacity: 0.75 }),
				h("path", { d: "M7 9.4a2.4 2.4 0 0 1 2 0" }),
				h("path", { d: "M8 9.4 12.4 3.6" }),
				h("circle", { cx: 8, cy: 9.4, r: 1.15, fill: "currentColor", stroke: "none" }),
				h("circle", { cx: 12.6, cy: 3.4, r: 1.1, fill: "currentColor", stroke: "none" }),
			);
		}

		function IconRefresh({ size }) {
			const s = size || 15;
			return h(
				"svg",
				iconProps(s),
				h("path", { d: "M13.2 6.2A5.4 5.4 0 0 0 3.3 5" }),
				h("path", { d: "M3 2.9v2.6h2.6" }),
				h("path", { d: "M2.8 9.8A5.4 5.4 0 0 0 12.7 11" }),
				h("path", { d: "M13 13.1v-2.6h-2.6" }),
			);
		}

		function IconSearch({ size }) {
			const s = size || 14;
			return h(
				"svg",
				iconProps(s),
				h("circle", { cx: 7, cy: 7, r: 4.2 }),
				h("path", { d: "M10.2 10.2 13.6 13.6" }),
			);
		}

		function IconPaper({ size }) {
			const s = size || 14;
			return h(
				"svg",
				iconProps(s),
				h("path", { d: "M4 2.5h5l3 3v8H4z" }),
				h("path", { d: "M9 2.5v3h3" }),
				h("path", { d: "M6 8.5h4" }),
				h("path", { d: "M6 10.8h3" }),
			);
		}

		function IconMessage({ size }) {
			const s = size || 14;
			return h(
				"svg",
				iconProps(s),
				h("path", { d: "M13.5 8.4c0 2.7-2.5 4.9-5.5 4.9-.7 0-1.4-.1-2-.3l-3 1.1 1.1-2.7c-.7-.8-1.1-1.9-1.1-3 0-2.7 2.5-4.9 5.5-4.9s5 2.2 5 4.9Z" }),
				h("path", { d: "M5.8 8.2h4.4" }),
				h("path", { d: "M5.8 10.2h2.8" }),
			);
		}

		function IconChevron({ direction }) {
			const path = direction === "left" ? "M10 3.5 5.5 8l4.5 4.5" : "M6 3.5 10.5 8 6 12.5";
			return h("svg", iconProps(14), h("path", { d: path }));
		}

		function IconRadar({ size }) {
			const s = size || 64;
			return h(
				"svg",
				{
					width: s,
					height: s,
					viewBox: "0 0 64 64",
					fill: "none",
					"aria-hidden": true,
				},
				h("circle", { cx: 32, cy: 34, r: 23, stroke: "currentColor", strokeWidth: 1.2, opacity: 0.22 }),
				h("circle", { cx: 32, cy: 34, r: 15, stroke: "currentColor", strokeWidth: 1.2, opacity: 0.38 }),
				h("circle", { cx: 32, cy: 34, r: 7, stroke: "currentColor", strokeWidth: 1.2, opacity: 0.6 }),
				h("path", { d: "M32 34 49 15", stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round", opacity: 0.8 }),
				h("circle", { cx: 32, cy: 34, r: 2.4, fill: "currentColor" }),
				h("circle", { cx: 49, cy: 15, r: 2.4, fill: "currentColor" }),
			);
		}

		/* ------------------------------------------------------------------ *
		 * Styles
		 * ------------------------------------------------------------------ */

		const CSS = [
			".sf-page{position:relative;display:flex;flex-direction:column;height:100%;min-height:0;overflow:hidden;background:var(--dsw-alias-bg-base);color:var(--dsw-alias-label-primary);font-family:var(--dsh-font-family-text,system-ui,-apple-system,\"PingFang SC\",\"Microsoft YaHei\",sans-serif)}",
			".sf-scroll{flex:1 1 auto;min-height:0;overflow:auto;scrollbar-gutter:stable}",
			".sf-inner{width:min(880px,100%);margin:0 auto;padding:34px 30px 88px;box-sizing:border-box}",
			".sf-head{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;flex-wrap:wrap}",
			".sf-eyebrow{font-size:11px;line-height:16px;letter-spacing:.12em;color:var(--dsw-alias-label-tertiary);font-weight:600}",
			".sf-titleRow{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-top:6px}",
			".sf-title{margin:0;font-size:28px;line-height:36px;font-weight:640;letter-spacing:-.012em}",
			".sf-dateChip{font-size:12.5px;line-height:20px;color:var(--dsw-alias-label-secondary);border:.5px solid var(--dsw-alias-border-l2);border-radius:999px;padding:2px 10px;font-variant-numeric:tabular-nums}",
			".sf-sub{margin:9px 0 0;max-width:640px;font-size:14px;line-height:23px;color:var(--dsw-alias-label-secondary)}",
			".sf-primary{display:inline-flex;align-items:center;gap:7px;height:36px;padding:0 15px;border-radius:9px;border:0;background:var(--dsw-alias-button-primary-fill);color:var(--dsw-alias-label-primary-foreground);font:inherit;font-size:13.5px;cursor:pointer;transition:background .15s ease,opacity .15s ease;white-space:nowrap}",
			".sf-primary:hover{background:var(--dsw-alias-button-primary-hover)}",
			".sf-primary:disabled{opacity:.45;cursor:not-allowed}",
			".sf-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:32px;padding:0 11px;border-radius:8px;border:.5px solid var(--dsw-alias-border-l2);background:transparent;color:var(--dsw-alias-label-secondary);font:inherit;font-size:13px;cursor:pointer}",
			".sf-btn:hover{background:color-mix(in srgb,var(--dsw-alias-label-primary) 7%,transparent);color:var(--dsw-alias-label-primary)}",
			".sf-btn:disabled{opacity:.4;cursor:not-allowed}",
			".sf-primary:focus-visible,.sf-btn:focus-visible,.sf-tab:focus-visible,.sf-catTab:focus-visible,.sf-linkBtn:focus-visible,.sf-expand:focus-visible,.sf-dateSelect:focus-visible{outline:2px solid var(--dsw-alias-brand-primary);outline-offset:2px}",
			".sf-toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-top:26px;padding-bottom:16px;border-bottom:.5px solid var(--dsw-alias-border-l1)}",
			".sf-dateNav{display:flex;align-items:center;gap:4px}",
			".sf-navBtn{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border:0;border-radius:7px;background:transparent;color:var(--dsw-alias-label-tertiary);cursor:pointer}",
			".sf-navBtn:hover{background:color-mix(in srgb,var(--dsw-alias-label-primary) 8%,transparent);color:var(--dsw-alias-label-primary)}",
			".sf-navBtn:disabled{opacity:.3;cursor:not-allowed}",
			".sf-dateSelect{height:32px;border:.5px solid var(--dsw-alias-border-l2);border-radius:8px;background:transparent;color:var(--dsw-alias-label-secondary);font:inherit;font-size:13px;padding:0 8px;color-scheme:light dark}",
			".sf-linkBtn{border:0;background:transparent;color:var(--dsw-alias-brand-text);font:inherit;font-size:13px;cursor:pointer;padding:4px 7px;border-radius:5px}",
			".sf-linkBtn:hover{text-decoration:underline}",
			".sf-tabs{display:flex;align-items:center;gap:2px;flex-wrap:wrap}",
			".sf-tab{position:relative;display:inline-flex;align-items:center;gap:7px;height:32px;padding:0 12px;border:0;border-radius:8px;background:transparent;color:var(--dsw-alias-label-tertiary);font:inherit;font-size:13.5px;cursor:pointer}",
			".sf-tab:hover{color:var(--dsw-alias-label-primary);background:color-mix(in srgb,var(--dsw-alias-label-primary) 6%,transparent)}",
			".sf-tab[data-active=true]{color:var(--dsw-alias-label-primary);background:color-mix(in srgb,var(--dsw-alias-label-primary) 8%,transparent);font-weight:550}",
			".sf-tabNum{font-size:11.5px;line-height:16px;color:var(--dsw-alias-label-tertiary);font-variant-numeric:tabular-nums}",
			".sf-meta{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:20px 0 16px;font-size:12.5px;line-height:19px;color:var(--dsw-alias-label-tertiary)}",
			".sf-metaRight{display:flex;align-items:center;gap:8px;flex-wrap:wrap}",
			".sf-model{display:inline-flex;align-items:center;gap:5px;padding:1px 8px;border-radius:999px;border:.5px solid var(--dsw-alias-border-l2);font-size:11.5px;line-height:18px;color:var(--dsw-alias-label-secondary)}",
			".sf-dot{width:5px;height:5px;border-radius:50%;background:var(--dsw-alias-state-success-primary);display:inline-block}",
			".sf-banner{display:flex;align-items:flex-start;gap:10px;padding:12px 14px;border-radius:10px;border:.5px solid var(--dsw-alias-border-l2);background:color-mix(in srgb,var(--dsw-alias-brand-primary) 6%,transparent);margin:0 0 16px;font-size:13px;line-height:20px;color:var(--dsw-alias-label-secondary)}",
			".sf-banner[data-kind=error]{background:color-mix(in srgb,var(--dsw-alias-state-error-primary) 9%,transparent);border-color:color-mix(in srgb,var(--dsw-alias-state-error-primary) 34%,var(--dsw-alias-border-l2))}",
			".sf-banner[data-kind=warn]{background:color-mix(in srgb,var(--dsw-alias-state-warn-primary) 10%,transparent);border-color:color-mix(in srgb,var(--dsw-alias-state-warn-primary) 30%,var(--dsw-alias-border-l2))}",
			".sf-bannerText{flex:1 1 auto;min-width:0}",
			".sf-bannerTitle{display:block;font-weight:600;color:var(--dsw-alias-label-primary);margin-bottom:2px}",
			".sf-progress{height:3px;border-radius:2px;background:color-mix(in srgb,var(--dsw-alias-label-primary) 12%,transparent);overflow:hidden;margin-top:8px}",
			".sf-progress i{display:block;height:100%;background:var(--dsw-alias-brand-primary);border-radius:2px;transition:width .3s ease}",
			".sf-spinner{width:13px;height:13px;border-radius:50%;border:2px solid color-mix(in srgb,var(--dsw-alias-brand-primary) 25%,transparent);border-top-color:var(--dsw-alias-brand-primary);animation:sf-spin .8s linear infinite;flex:none;margin-top:2px}",
			".sf-list{display:flex;flex-direction:column;gap:20px}",
			".sf-card{padding:22px 24px 18px;border-radius:12px;border:1px solid var(--dsw-alias-border-l2);background:var(--dsw-alias-bg-layer-1);box-shadow:0 1px 2px rgba(0,0,0,.035),0 8px 22px -20px rgba(0,0,0,.22)}",
			".sf-cardHead{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}",
			".sf-cardTitle{flex:1 1 auto;min-width:0;font-size:18px;line-height:27px;font-weight:600;color:var(--dsw-alias-label-primary);text-decoration:none;letter-spacing:-.008em}",
			".sf-cardTitle:hover{text-decoration:underline;text-underline-offset:2px}",
			".sf-source{flex:none;font-size:12px;line-height:18px;color:var(--dsw-alias-label-tertiary);white-space:nowrap;margin-top:2px}",
			".sf-tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}",
			".sf-tag{font-size:12px;line-height:19px;padding:1px 9px;border-radius:5px;background:color-mix(in srgb,var(--dsw-alias-label-primary) 5%,transparent);color:var(--dsw-alias-label-secondary)}",
			".sf-line{margin:12px 0 0;font-size:15px;line-height:25px;color:var(--dsw-alias-label-secondary)}",
			".sf-line strong{color:var(--dsw-alias-label-primary);font-weight:600;margin-right:1px}",
			".sf-evidence{margin:10px 0 0;font-size:13px;line-height:21px;color:var(--dsw-alias-label-secondary)}",
			".sf-cardFoot{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:15px;padding-top:11px;border-top:.5px solid var(--dsw-alias-border-l1);font-size:12.5px;line-height:19px;color:var(--dsw-alias-label-secondary)}",
			".sf-footMeta{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
			".sf-cardActions{display:flex;align-items:center;gap:10px;flex:none;flex-wrap:wrap;justify-content:flex-end}",
			".sf-paperBtn{display:inline-flex;align-items:center;gap:5px;height:28px;padding:0 9px;border:.5px solid color-mix(in srgb,var(--dsw-alias-brand-primary) 22%,var(--dsw-alias-border-l2));border-radius:7px;background:color-mix(in srgb,var(--dsw-alias-brand-primary) 6%,transparent);color:var(--dsw-alias-brand-text);font:inherit;font-size:12px;cursor:pointer;white-space:nowrap;transition:background .15s ease}",
			".sf-paperBtn:hover{background:color-mix(in srgb,var(--dsw-alias-brand-primary) 11%,transparent)}",
			".sf-paperBtn:focus-visible{outline:2px solid var(--dsw-alias-brand-primary);outline-offset:2px}",
			".sf-paperBox{margin:16px 0 0;border:.5px solid var(--dsw-alias-border-l2);border-radius:10px;background:var(--dsw-alias-bg-layer-1);padding:0 14px}",
			".sf-paperSummary{display:flex;align-items:center;gap:8px;padding:11px 0;cursor:pointer;list-style:none;font-size:12.5px;color:var(--dsw-alias-label-secondary)}",
			".sf-paperSummary::-webkit-details-marker{display:none}",
			".sf-paperSummary::after{content:\"›\";margin-left:auto;color:var(--dsw-alias-label-tertiary);font-size:16px;line-height:1;transition:transform .15s ease}",
			".sf-paperBox[open] .sf-paperSummary::after{transform:rotate(90deg)}",
			".sf-paperSummaryMain{display:inline-flex;align-items:center;gap:6px;color:var(--dsw-alias-label-primary);font-weight:550;flex:none}",
			".sf-paperSummaryHint{color:var(--dsw-alias-label-tertiary);font-size:11.5px;line-height:18px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
			".sf-paperBox[open]{padding-bottom:14px}",
			".sf-paperBody{display:flex;align-items:flex-end;gap:10px;padding-top:11px;border-top:.5px solid var(--dsw-alias-border-l1)}",
			".sf-paperInput{flex:1;min-width:0;min-height:56px;resize:vertical;border:.5px solid var(--dsw-alias-border-l2);border-radius:8px;background:transparent;color:var(--dsw-alias-label-primary);font:inherit;font-size:13px;line-height:20px;padding:8px 10px;outline:none;box-sizing:border-box}",
			".sf-paperInput:focus{border-color:var(--dsw-alias-brand-primary)}",
			".sf-paperStart{height:34px;flex:none}",
			".sf-chatBtn{display:inline-flex;align-items:center;gap:5px;height:28px;padding:0 9px;border:.5px solid var(--dsw-alias-border-l2);border-radius:7px;background:transparent;color:var(--dsw-alias-brand-text);font:inherit;font-size:12px;cursor:pointer;white-space:nowrap;transition:background .15s ease,border-color .15s ease}",
			".sf-chatBtn:hover{background:color-mix(in srgb,var(--dsw-alias-brand-primary) 7%,transparent);border-color:color-mix(in srgb,var(--dsw-alias-brand-primary) 30%,var(--dsw-alias-border-l2))}",
			".sf-chatBtn:focus-visible{outline:2px solid var(--dsw-alias-brand-primary);outline-offset:2px}",
			".sf-origin{display:inline-flex;align-items:center;gap:4px;flex:none;color:var(--dsw-alias-brand-text);text-decoration:none;font-size:12px}",
			".sf-origin:hover{text-decoration:underline}",
			".sf-expand{margin-top:7px}",
			".sf-expand button{border:0;background:transparent;color:var(--dsw-alias-label-tertiary);font:inherit;font-size:12px;cursor:pointer;padding:2px 0}",
			".sf-expand button:hover{color:var(--dsw-alias-label-primary)}",
			".sf-details{margin-top:4px;font-size:13px;line-height:21px;color:var(--dsw-alias-label-secondary)}",
			".sf-details strong{display:block;font-size:11px;line-height:17px;color:var(--dsw-alias-label-tertiary);font-weight:500;margin:6px 0 3px}",
			".sf-details ul{margin:0;padding-left:17px}",
			".sf-details li{margin:2px 0}",
			".sf-oppGrid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;align-items:start}",
			".sf-sectionHead{display:flex;align-items:baseline;justify-content:space-between;gap:10px;margin:3px 0 8px}",
			".sf-sectionHead h2{margin:0;font-size:16px;line-height:23px;font-weight:600}",
			".sf-sectionHead span{font-size:12px;color:var(--dsw-alias-label-tertiary)}",
			".sf-sectionHint{margin:0 0 12px;font-size:12.5px;line-height:20px;color:var(--dsw-alias-label-tertiary)}",
			".sf-oppList{display:flex;flex-direction:column;gap:14px}",
			".sf-opp{padding:16px 17px;border-radius:11px;border:1px solid var(--dsw-alias-border-l2);background:var(--dsw-alias-bg-layer-1);box-shadow:0 1px 2px rgba(0,0,0,.03)}",
			".sf-oppTop{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:5px}",
			".sf-rank{font-size:11.5px;line-height:18px;color:var(--dsw-alias-label-tertiary);font-variant-numeric:tabular-nums}",
			".sf-score{font-size:11.5px;line-height:18px;color:var(--dsw-alias-brand-text);border:.5px solid color-mix(in srgb,var(--dsw-alias-brand-primary) 32%,transparent);border-radius:999px;padding:0 7px;font-variant-numeric:tabular-nums}",
			".sf-oppTitle{margin:0;font-size:16px;line-height:24px;font-weight:600;letter-spacing:-.005em}",
			".sf-oppSource{display:block;margin-top:5px;font-size:12px;line-height:18px;color:var(--dsw-alias-brand-text);text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
			".sf-oppSource:hover{text-decoration:underline}",
			".sf-field{margin-top:9px}",
			".sf-fieldLabel{display:block;font-size:11px;line-height:17px;letter-spacing:.03em;color:var(--dsw-alias-label-tertiary)}",
			".sf-fieldValue{margin:2px 0 0;font-size:14px;line-height:22px;color:var(--dsw-alias-label-secondary)}",
			".sf-fieldValue ul{margin:2px 0 0;padding-left:16px}",
			".sf-chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}",
			".sf-chip{font-size:10.5px;line-height:17px;padding:0 7px;border-radius:4px;border:.5px solid var(--dsw-alias-border-l2);color:var(--dsw-alias-label-secondary)}",
			".sf-allBar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:18px 0 0}",
			".sf-searchBox{display:flex;align-items:center;gap:7px;height:36px;padding:0 12px;border:.5px solid var(--dsw-alias-border-l2);border-radius:9px;color:var(--dsw-alias-label-tertiary);flex:1 1 280px;max-width:420px;box-sizing:border-box}",
			".sf-searchBox:focus-within{border-color:var(--dsw-alias-brand-primary)}",
			".sf-searchBox input{flex:1;min-width:0;border:0;background:transparent;color:var(--dsw-alias-label-primary);font:inherit;font-size:13px;outline:none}",
			".sf-searchBox input::placeholder{color:var(--dsw-alias-label-tertiary)}",
			".sf-allCount{margin-left:auto;font-size:12.5px;color:var(--dsw-alias-label-tertiary);font-variant-numeric:tabular-nums;white-space:nowrap}",
			".sf-allHint{margin:8px 0 8px;font-size:12.5px;line-height:20px;color:var(--dsw-alias-label-tertiary)}",
			".sf-catTabs{display:flex;align-items:center;gap:3px;flex-wrap:wrap;margin:12px 0 0}",
			".sf-catTab{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 11px;border:0;border-radius:8px;background:transparent;color:var(--dsw-alias-label-tertiary);font:inherit;font-size:13px;cursor:pointer;white-space:nowrap}",
			".sf-catTab:hover{color:var(--dsw-alias-label-primary);background:color-mix(in srgb,var(--dsw-alias-label-primary) 6%,transparent)}",
			".sf-catTab[data-active=true]{color:var(--dsw-alias-label-primary);background:color-mix(in srgb,var(--dsw-alias-brand-primary) 8%,transparent);font-weight:550}",
			".sf-catCount{font-size:11px;line-height:16px;color:var(--dsw-alias-label-tertiary);font-variant-numeric:tabular-nums}",
			".sf-cat{display:inline-flex;align-items:center;gap:6px;flex:none;font-size:12px;line-height:20px;padding:2px 10px;border-radius:999px;border:.5px solid var(--dsw-alias-border-l2);color:var(--dsw-alias-label-secondary);background:color-mix(in srgb,var(--dsw-alias-label-primary) 4%,transparent);white-space:nowrap;margin-top:1px}",
			".sf-catDot{width:5px;height:5px;border-radius:50%;flex:none}",
			".sf-itemMetaLine{margin-top:6px;font-size:13px;line-height:20px;color:var(--dsw-alias-label-tertiary)}",
			".sf-lineMuted{color:var(--dsw-alias-label-tertiary)}",
			".sf-banner>.sf-btn{flex:none;align-self:flex-start}",
			".sf-empty{display:flex;flex-direction:column;align-items:center;text-align:center;padding:70px 20px 40px;color:var(--dsw-alias-label-tertiary)}",
			".sf-emptyIcon{color:var(--dsw-alias-brand-primary);opacity:.65;margin-bottom:14px}",
			".sf-emptyTitle{font-size:17px;line-height:25px;color:var(--dsw-alias-label-primary);font-weight:600}",
			".sf-emptyHint{max-width:480px;margin:8px 0 18px;font-size:13.5px;line-height:22px;color:var(--dsw-alias-label-tertiary)}",
			".sf-emptyActions{display:flex;gap:8px;align-items:center}",
			".sf-skeleton{height:140px;border-radius:10px;border:.5px solid var(--dsw-alias-border-l1);background:linear-gradient(90deg,transparent,color-mix(in srgb,var(--dsw-alias-label-primary) 4%,transparent),transparent);background-size:200% 100%;animation:sf-shimmer 1.4s infinite}",
			".sf-coverage{margin:18px 0 0;font-size:11.5px;line-height:18px;color:var(--dsw-alias-label-tertiary)}",
			".sf-coverage summary{cursor:pointer;color:var(--dsw-alias-label-tertiary);width:fit-content}",
			".sf-coverage summary:hover{color:var(--dsw-alias-label-secondary)}",
			".sf-sourceList{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}",
			".sf-sourceItem{display:inline-flex;align-items:center;gap:4px;padding:1px 7px;border-radius:999px;border:.5px solid var(--dsw-alias-border-l1);font-size:10.5px;line-height:17px}",
			".sf-sourceItem[data-ok=false]{color:var(--dsw-alias-state-error-primary);border-color:color-mix(in srgb,var(--dsw-alias-state-error-primary) 28%,transparent)}",
			".sf-footer{margin-top:26px;padding-top:14px;border-top:.5px solid var(--dsw-alias-border-l1);font-size:12px;line-height:19px;color:var(--dsw-alias-label-tertiary);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}",
			".sf-fadeIn{animation:sf-fade .18s ease}",
			"@keyframes sf-spin{to{transform:rotate(360deg)}}",
			"@keyframes sf-shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}",
			"@keyframes sf-fade{from{opacity:0;transform:translateY(2px)}to{opacity:1;transform:none}}",
			"@media (max-width:820px){.sf-inner{padding:24px 16px 60px}.sf-title{font-size:22px;line-height:30px}.sf-head{gap:14px}.sf-oppGrid{grid-template-columns:minmax(0,1fr)}.sf-toolbar{align-items:flex-start;flex-direction:column}.sf-tabs{width:100%;overflow:auto}.sf-dateSelect{font-size:16px}.sf-card{padding:18px 16px 15px;border-radius:11px}.sf-cardTitle{font-size:16.5px;line-height:24px}.sf-line{font-size:14px;line-height:23px}.sf-evidence{font-size:12.5px;line-height:20px}.sf-cat{font-size:11px;line-height:19px}.sf-list{gap:14px}.sf-paperBody{flex-direction:column;align-items:stretch}.sf-paperStart{width:100%}.sf-paperSummaryHint{display:none}}",
			"@media (prefers-reduced-motion:reduce){.sf-spinner,.sf-skeleton{animation:none}.sf-fadeIn{animation:none}}",
		].join("");

		/* ------------------------------------------------------------------ *
		 * Components
		 * ------------------------------------------------------------------ */

		function Field({ label, value }) {
			if (!value) return null;
			return h(
				"div",
				{ className: "sf-field" },
				h("span", { className: "sf-fieldLabel" }, label),
				h("p", { className: "sf-fieldValue" }, value),
			);
		}

		function SignalCard({ item, index, t, onChat, onPaper }) {
			const [expanded, setExpanded] = useState(false);
			const details = Array.isArray(item.details) ? item.details : [];
			const tags = Array.isArray(item.tags) ? item.tags : [];
			return h(
				"article",
				{ className: "sf-card sf-fadeIn" },
				h(
					"div",
					{ className: "sf-cardHead" },
					h(
						"a",
						{
							className: "sf-cardTitle",
							href: item.url,
							target: "_blank",
							rel: "noopener noreferrer",
						},
						item.title,
					),
					h("span", { className: "sf-source" }, item.source),
				),
				tags.length > 0 && h(
					"div",
					{ className: "sf-tags" },
					tags.map((tag) => h("span", { className: "sf-tag", key: tag }, tag)),
				),
				item.finding && h("p", { className: "sf-line" }, h("strong", null, t("findingLabel")), item.finding),
				item.why_read && h("p", { className: "sf-line" }, h("strong", null, t("whyLabel")), item.why_read),
				item.evidence_note && h("p", { className: "sf-evidence" }, `${t("evidenceLabel")}${item.evidence_note}`),
				h(
					"div",
					{ className: "sf-cardFoot" },
					h(
						"span",
						{ className: "sf-footMeta" },
						[
							`${t("aiBadge")} · ${t("verify")}`,
							item.published_at ? formatTime(item.published_at) : "",
						].filter(Boolean).join(" · "),
					),
					h(
						"div",
						{ className: "sf-cardActions" },
						isPaper(item) && h(
							"button",
							{
								type: "button",
								className: "sf-paperBtn",
								onClick: () => onPaper?.(item),
							},
							h(IconPaper, { size: 13 }),
							t("readPaper"),
						),
						h(
							"button",
							{
								type: "button",
								className: "sf-chatBtn",
								onClick: () => onChat?.(item),
							},
							h(IconMessage, { size: 13 }),
							t("continueChat"),
						),
						h(
							"a",
							{
								className: "sf-origin",
								href: item.url,
								target: "_blank",
								rel: "noopener noreferrer",
							},
							t("viewOriginal"),
						),
					),
				),
				details.length > 0 && h(
					"div",
					{ className: "sf-expand" },
					h(
						"button",
						{
							type: "button",
							"aria-expanded": expanded,
							onClick: () => setExpanded((value) => !value),
						},
						expanded ? t("hideDetails") : t("showDetails"),
					),
					expanded && h(
						"div",
						{ className: "sf-details" },
						h("strong", null, t("detailsTitle")),
						h("ul", null, details.map((detail, detailIndex) => h("li", { key: `${index}-${detailIndex}` }, detail))),
					),
				),
			);
		}

		function IntelCard({ item, t, onChat, onPaper }) {
			const [expanded, setExpanded] = useState(false);
			const category = itemCategory(item);
			const tags = Array.isArray(item.tags) ? item.tags : [];
			const details = Array.isArray(item.details) ? item.details : [];
			const finding = String(item.finding ?? "").trim();
			const whyRead = String(item.why_read ?? "").trim();
			const summary = String(item.summary ?? "").trim();
			const hasQuickRead = Boolean(finding && whyRead);
			const evidence = evidenceFor(item);
			const meta = [
				item.source,
				item.relevance_score ? `${t("relevance")} ${item.relevance_score}` : "",
			].filter(Boolean).join(" · ");
			return h(
				"article",
				{ className: "sf-card sf-intel sf-fadeIn" },
				h(
					"div",
					{ className: "sf-cardHead" },
					h(
						"a",
						{
							className: "sf-cardTitle",
							href: item.url,
							target: "_blank",
							rel: "noopener noreferrer",
						},
						item.title,
					),
					h(
						"span",
						{ className: "sf-cat" },
						h("i", { className: "sf-catDot", style: { background: categoryColor(category) } }),
						category,
					),
				),
				meta && h("div", { className: "sf-itemMetaLine" }, meta),
				tags.length > 0 && h(
					"div",
					{ className: "sf-tags" },
					tags.map((tag) => h("span", { className: "sf-tag", key: tag }, tag)),
				),
				hasQuickRead
					? h(
						React.Fragment,
						null,
						h("p", { className: "sf-line" }, h("strong", null, t("findingLabel")), finding),
						h("p", { className: "sf-line" }, h("strong", null, t("whyLabel")), whyRead),
					)
					: h(
						React.Fragment,
						null,
						summary
							? h("p", { className: "sf-line" }, h("strong", null, `${t("rawSummary")}：`), summary)
							: h("p", { className: "sf-line sf-lineMuted" }, t("notEnriched")),
					),
				evidence && h("p", { className: "sf-evidence" }, `${t("evidenceLabel")}${evidence}`),
				h(
					"div",
					{ className: "sf-cardFoot" },
					h(
						"span",
						{ className: "sf-footMeta" },
						[
							`${hasQuickRead ? t("aiBadge") : t("rawSummary")} · ${t("verify")}`,
							item.published_at ? formatTime(item.published_at) : "",
						].filter(Boolean).join(" · "),
					),
					h(
						"div",
						{ className: "sf-cardActions" },
						isPaper(item) && h(
							"button",
							{
								type: "button",
								className: "sf-paperBtn",
								onClick: () => onPaper?.(item),
							},
							h(IconPaper, { size: 13 }),
							t("readPaper"),
						),
						h(
							"button",
							{
								type: "button",
								className: "sf-chatBtn",
								onClick: () => onChat?.(item),
							},
							h(IconMessage, { size: 13 }),
							t("continueChat"),
						),
						h(
							"a",
							{
								className: "sf-origin",
								href: item.url,
								target: "_blank",
								rel: "noopener noreferrer",
							},
							t("viewOriginal"),
						),
					),
				),
				details.length > 0 && h(
					"div",
					{ className: "sf-expand" },
					h(
						"button",
						{
							type: "button",
							"aria-expanded": expanded,
							onClick: () => setExpanded((value) => !value),
						},
						expanded ? t("hideDetails") : t("showDetails"),
					),
					expanded && h(
						"div",
						{ className: "sf-details" },
						h("strong", null, t("detailsTitle")),
						h("ul", null, details.map((detail, index) => h("li", { key: `${item.id}-${index}` }, detail))),
					),
				),
			);
		}

		function BusinessCard({ item, index, t }) {
			const mvp = Array.isArray(item.mvp_features) ? item.mvp_features : [];
			return h(
				"article",
				{ className: "sf-opp sf-fadeIn" },
				h(
					"div",
					{ className: "sf-oppTop" },
					h("span", { className: "sf-rank" }, `#${index + 1}`),
					h("span", { className: "sf-score" }, `${item.total_score}/20`),
				),
				h("h3", { className: "sf-oppTitle" }, item.title),
				item.source_title && h(
					"a",
					{
						className: "sf-oppSource",
						href: item.source_url,
						target: "_blank",
						rel: "noopener noreferrer",
						title: item.source_title,
					},
					`${t("source")}：${item.source_title}`,
				),
				h(Field, { label: t("trigger"), value: item.trigger }),
				h(Field, { label: t("insight"), value: item.core_insight }),
				h(Field, { label: t("form"), value: item.product_form }),
				h(Field, { label: t("users"), value: item.target_users }),
				mvp.length > 0 && h(
					"div",
					{ className: "sf-field" },
					h("span", { className: "sf-fieldLabel" }, t("mvp")),
					h("div", { className: "sf-chips" }, mvp.map((feature) => h("span", { className: "sf-chip", key: feature }, feature))),
				),
				h(Field, { label: t("businessModel"), value: item.business_model }),
				h(Field, { label: t("risk"), value: item.risks }),
			);
		}

		function RdevCard({ item, index, t }) {
			const audience = Array.isArray(item.audience) ? item.audience : [];
			return h(
				"article",
				{ className: "sf-opp sf-fadeIn" },
				h(
					"div",
					{ className: "sf-oppTop" },
					h("span", { className: "sf-rank" }, `#${index + 1} · ${item.type ?? t("rdev")}`),
					h("span", { className: "sf-score" }, `${item.total_score}/10`),
				),
				h("h3", { className: "sf-oppTitle" }, item.title),
				item.source_title && h(
					"a",
					{
						className: "sf-oppSource",
						href: item.source_url,
						target: "_blank",
						rel: "noopener noreferrer",
						title: item.source_title,
					},
					`${t("source")}：${item.source_title}`,
				),
				h(Field, { label: t("scenario"), value: item.scenario }),
				h(Field, { label: t("aiSolution"), value: item.ai_solution }),
				h(Field, { label: t("implementation"), value: item.implementation }),
				audience.length > 0 && h(
					"div",
					{ className: "sf-field" },
					h("span", { className: "sf-fieldLabel" }, t("audience")),
					h("div", { className: "sf-chips" }, audience.map((team) => h("span", { className: "sf-chip", key: team }, team))),
				),
				h(Field, { label: t("impact"), value: item.impact }),
				h(
					"div",
					{ className: "sf-field" },
					h("span", { className: "sf-fieldLabel" }, `${t("difficulty")} / ${t("resistance")}`),
					h("p", { className: "sf-fieldValue" }, [item.difficulty, item.resistance].filter(Boolean).join(" · ")),
				),
			);
		}

		function EmptyState({ t, past, onStart, disabled }) {
			return h(
				"div",
				{ className: "sf-empty" },
				h("div", { className: "sf-emptyIcon" }, h(IconRadar, { size: 62 })),
				h("div", { className: "sf-emptyTitle" }, past ? t("emptyPastTitle") : t("emptyTitle")),
				h("p", { className: "sf-emptyHint" }, past ? t("emptyPastHint") : t("emptyHint")),
				!past && h(
					"div",
					{ className: "sf-emptyActions" },
					h(
						"button",
						{ type: "button", className: "sf-primary", onClick: onStart, disabled },
						h(IconRefresh, { size: 14 }),
						disabled ? t("refreshing") : t("fetch"),
					),
				),
			);
		}

		function stageLabel(t, stage) {
			if (stage === "sources") return t("stageSources");
			if (stage === "signals") return t("stageSignals");
			if (stage === "opportunities") return t("stageOpportunities");
			if (stage === "enrich") return t("stageEnrich");
			if (stage === "saving") return t("stageSaving");
			if (stage === "done") return t("stageDone");
			return stage || "";
		}

		function JobBanner({ job, t }) {
			if (!job || job.status !== "running") return null;
			const progress = job.progress ?? {};
			const total = Number(progress.sourceTotal) || 0;
			const done = Number(progress.sourceDone) || 0;
			let percent = 8;
			const enrichTotal = Number(progress.enrichTotal) || 0;
			const enriched = Number(progress.enriched) || 0;
			if (job.stage === "sources" && total > 0) percent = Math.max(8, Math.round((done / total) * 35));
			else if (job.stage === "signals") percent = 50;
			else if (job.stage === "opportunities") percent = 70;
			else if (job.stage === "enrich" && enrichTotal > 0) percent = Math.max(10, Math.round((enriched / enrichTotal) * 90));
			else if (job.stage === "enrich") percent = 10;
			else if (job.stage === "saving") percent = 95;
			const elapsed = job.startedAt ? Math.max(0, Math.round((Date.now() - Date.parse(job.startedAt)) / 1000)) : 0;
			return h(
				"div",
				{ className: "sf-banner" },
				h("span", { className: "sf-spinner", "aria-hidden": true }),
				h(
					"div",
					{ className: "sf-bannerText" },
					h("span", { className: "sf-bannerTitle" }, `${stageLabel(t, job.stage)} · ${job.message || t("jobRunning")}`),
					h(
						"span",
						null,
						[
							total > 0 && job.stage === "sources" ? `${done}/${total}` : "",
							elapsed > 0 ? `${t("elapsed")} ${elapsed} ${t("seconds")}` : "",
							progress.candidates ? `${t("candidates")} ${progress.candidates}` : "",
							progress.signals ? `${t("signalsUnit")} ${progress.signals}` : "",
							job.stage === "enrich" && enrichTotal > 0 ? `${enriched}/${enrichTotal}` : "",
						].filter(Boolean).join(" · "),
					),
					h("div", { className: "sf-progress" }, h("i", { style: { width: `${percent}%` } })),
				),
			);
		}

		function SignalForgePage(props) {
			const t = useT(props);
			const [today, setToday] = useState("");
			const [date, setDate] = useState("");
			const [digest, setDigest] = useState(null);
			const [dates, setDates] = useState([]);
			const [job, setJob] = useState(null);
			const [tab, setTab] = useState("signals");
			const [loading, setLoading] = useState(true);
			const [error, setError] = useState(null);
			const [notice, setNotice] = useState(null);
			const [, setTick] = useState(0);
			const [query, setQuery] = useState("");
			const [categoryFilter, setCategoryFilter] = useState("all");
			const [paperInput, setPaperInput] = useState("");
			const [paperBusy, setPaperBusy] = useState(false);
			const pollRef = useRef(null);
			const dateRef = useRef("");
			const aliveRef = useRef(true);

			useEffect(() => {
				dateRef.current = date;
			}, [date]);

			function stopPolling() {
				if (pollRef.current !== null) {
					window.clearInterval(pollRef.current);
					pollRef.current = null;
				}
			}

			async function pollJob(id) {
				stopPolling();
				const tick = async () => {
					if (!aliveRef.current) return;
					try {
						const result = await request(`/jobs/${encodeURIComponent(id)}`);
						if (result.status === 404) {
							stopPolling();
							setJob(null);
							return;
						}
						if (!result.ok || !result.data) throw new Error(errorText(result));
						const next = result.data;
						setJob(next);
						if (next.status === "done") {
							stopPolling();
							if (next.digest && dateRef.current === next.digest.date) {
								setDigest(next.digest);
							}
							if (next.digest) {
								setDates((previous) => {
									const entry = {
										date: next.digest.date,
										generatedAt: next.digest.generatedAt,
										signals: next.digest.signals?.length ?? 0,
										business: next.digest.opportunities?.business?.length ?? 0,
										rdev: next.digest.opportunities?.rdev?.length ?? 0,
										model: next.digest.analysis?.model ?? null,
										warning: next.digest.analysis?.warning ?? null,
									};
									return [entry, ...previous.filter((item) => item.date !== entry.date)]
										.sort((a, b) => b.date.localeCompare(a.date));
								});
							}
							setError(null);
						} else if (next.status === "error" || next.status === "cancelled") {
							stopPolling();
							if (next.error) setError(next.error);
						}
					} catch (pollError) {
						stopPolling();
						setError(pollError instanceof Error ? pollError.message : String(pollError));
					}
				};
				await tick();
				if (aliveRef.current) {
					pollRef.current = window.setInterval(tick, 1200);
				}
			}

			async function loadDigest(target) {
				setLoading(true);
				setError(null);
				try {
					const result = await request(`/digest?date=${encodeURIComponent(target)}`);
					if (result.status === 404) {
						setDigest(null);
					} else if (!result.ok) {
						throw new Error(errorText(result));
					} else {
						setDigest(result.data);
					}
				} catch (loadError) {
					setDigest(null);
					setError(loadError instanceof Error ? loadError.message : String(loadError));
				} finally {
					setLoading(false);
				}
			}

			useEffect(() => {
				aliveRef.current = true;
				(async () => {
					try {
						const result = await request("/bootstrap");
						if (!result.ok) throw new Error(errorText(result));
						const data = result.data;
						setToday(data.today);
						setDate(data.date || data.today);
						setDates(Array.isArray(data.dates) ? data.dates : []);
						setDigest(data.digest ?? null);
						if (data.job && data.job.status === "running") {
							setJob(data.job);
							await pollJob(data.job.id);
						}
					} catch (bootError) {
						setError(bootError instanceof Error ? bootError.message : String(bootError));
					} finally {
						setLoading(false);
					}
				})();
				return () => {
					aliveRef.current = false;
					stopPolling();
				};
			}, []);

			useEffect(() => {
				if (job?.status !== "running") return undefined;
				const timer = window.setInterval(() => setTick((value) => value + 1), 1000);
				return () => window.clearInterval(timer);
			}, [job?.status]);

			function chooseDate(next) {
				if (!next || next === date) return;
				setDate(next);
				setTab("signals");
				setQuery("");
				setCategoryFilter("all");
				setNotice(null);
				loadDigest(next);
			}

			async function startFetch() {
				if (!today || date !== today) return;
				if (job?.status === "running") return;
				setError(null);
				try {
					const result = await request("/jobs", {
						method: "POST",
						body: JSON.stringify({ date: today }),
					});
					if (!result.ok || !result.data?.job) throw new Error(errorText(result));
					setJob(result.data.job);
					await pollJob(result.data.job.id);
				} catch (fetchError) {
					setError(fetchError instanceof Error ? fetchError.message : String(fetchError));
				}
			}

			async function runChatAction(action, { clearPaper = false } = {}) {
				setError(null);
				setNotice(null);
				if (typeof action !== "function") {
					setError(t("chatUnavailable"));
					return false;
				}
				try {
					const result = await action();
					if (result && result.ok) {
						if (clearPaper) setPaperInput("");
						return true;
					}
					if (result && result.copied) {
						setNotice(t("chatCopied"));
						return false;
					}
					setError(result && result.error ? `${t("chatUnavailable")} ${result.error}` : t("chatUnavailable"));
					return false;
				} catch (chatError) {
					setError(chatError instanceof Error ? chatError.message : String(chatError));
					return false;
				}
			}

			function handleChat(item) {
				return runChatAction(() => props.openArticleChat?.(item));
			}

			function handleReadPaper(item) {
				return runChatAction(() => props.openPaperChat?.(item));
			}

			async function startManualPaper() {
				const raw = paperInput.trim();
				if (!raw || paperBusy) return;
				setPaperBusy(true);
				try {
					await runChatAction(() => props.openManualPaper?.(raw), { clearPaper: true });
				} finally {
					setPaperBusy(false);
				}
			}

			async function startEnrich() {
				if (!date) return;
				if (job?.status === "running") return;
				setError(null);
				try {
					const result = await request("/jobs", {
						method: "POST",
						body: JSON.stringify({ date, mode: "enrich" }),
					});
					if (!result.ok || !result.data?.job) throw new Error(errorText(result));
					setJob(result.data.job);
					await pollJob(result.data.job.id);
				} catch (enrichError) {
					setError(enrichError instanceof Error ? enrichError.message : String(enrichError));
				}
			}

			const running = job?.status === "running";
			const enriching = running && job?.mode === "enrich";
			const isToday = Boolean(today) && date === today;
			const signals = Array.isArray(digest?.signals) ? digest.signals : [];
			const business = Array.isArray(digest?.opportunities?.business) ? digest.opportunities.business : [];
			const rdev = Array.isArray(digest?.opportunities?.rdev) ? digest.opportunities.rdev : [];
			const opportunityCount = business.length + rdev.length;
			const stats = digest?.stats ?? {};
			const model = digest?.analysis?.model ?? null;
			const warning = digest?.analysis?.warning ?? null;
			const oppsError = digest?.analysis?.opportunitiesError ?? null;
			const sources = Array.isArray(stats.sources) ? stats.sources : [];
			const okSources = sources.filter((item) => item.ok).length;
			const allItems = Array.isArray(digest?.items) ? digest.items : [];
			const itemCount = allItems.length || Number(stats.candidates ?? 0);
			const categoryCounts = new Map();
			for (const item of allItems) {
				const category = itemCategory(item);
				categoryCounts.set(category, (categoryCounts.get(category) ?? 0) + 1);
			}
			const categories = CATEGORY_ORDER.filter((category) => categoryCounts.has(category));
			const unenrichedCount = allItems.filter((item) => !item.finding || !item.why_read).length;
			const normalizedQuery = query.trim().toLowerCase();
			const filteredItems = allItems.filter((item) => {
				if (categoryFilter !== "all" && itemCategory(item) !== categoryFilter) return false;
				if (!normalizedQuery) return true;
				return `${item.title ?? ""} ${item.source ?? ""} ${item.summary ?? ""} ${item.finding ?? ""}`.toLowerCase().includes(normalizedQuery);
			});
			const showEmpty = !running && !digest && !loading;
			const emptyPast = Boolean(today) && date !== today;
			const dateMeta = new Map(dates.map((item) => [item.date, item]));
			const availableDates = [...new Set([today, ...dates.map((item) => item.date), date].filter(Boolean))]
				.sort((a, b) => b.localeCompare(a));
			const dateIndex = availableDates.indexOf(date);
			const olderDate = dateIndex >= 0 ? availableDates[dateIndex + 1] ?? "" : "";
			const newerDate = dateIndex > 0 ? availableDates[dateIndex - 1] : "";
			const dateOptionLabel = (value) => {
				const meta = dateMeta.get(value);
				const count = meta
					? ` · ${meta.signals ?? 0} 条`
					: "";
				return value === today
					? `${t("todayLabel")} · ${value}${meta ? count : " · 待生成"}`
					: `${value}${count}`;
			};

			const statsLine = t("statsLine")
				.replace("{signals}", String(signals.length))
				.replace("{candidates}", String(stats.candidates ?? 0))
				.replace("{sources}", String(okSources || stats.okSources || 0));

			return h(
				"div",
				{ className: "sf-page" },
				h("style", null, CSS),
				h(
					"div",
					{ className: "sf-scroll" },
					h(
						"div",
						{ className: "sf-inner" },
						h(
							"header",
							{ className: "sf-head" },
							h(
								"div",
								null,
								h("div", { className: "sf-eyebrow" }, "SIGNALFORGE · DAILY AI INTELLIGENCE"),
								h(
									"div",
									{ className: "sf-titleRow" },
									h("h1", { className: "sf-title" }, t("title")),
									date && h("span", { className: "sf-dateChip" }, formatDateCn(date)),
								),
								h("p", { className: "sf-sub" }, t("subtitle")),
							),
							h(
								"div",
								{ className: "sf-headActions" },
								h(
									"button",
									{
										type: "button",
										className: "sf-primary",
										onClick: startFetch,
										disabled: !isToday || running,
										title: isToday ? t("fetch") : t("onlyToday"),
									},
									h(IconRefresh, { size: 14 }),
									running ? t("refreshing") : digest ? t("regenerate") : t("fetch"),
								),
							),
						),
						h(
							"div",
							{ className: "sf-toolbar" },
							h(
								"div",
								{ className: "sf-dateNav" },
								h(
									"button",
									{
										type: "button",
										className: "sf-navBtn",
										onClick: () => chooseDate(olderDate),
										disabled: !olderDate,
										title: t("prevDay"),
										"aria-label": t("prevDay"),
									},
									h(IconChevron, { direction: "left" }),
								),
								h(
									"select",
									{
										className: "sf-dateSelect",
										value: date || today,
										"aria-label": t("dateLabel"),
										onChange: (event) => chooseDate(event.target.value),
									},
									availableDates.map((value) => h("option", { key: value, value }, dateOptionLabel(value))),
								),
								h(
									"button",
									{
										type: "button",
										className: "sf-navBtn",
										onClick: () => chooseDate(newerDate),
										disabled: !newerDate,
										title: t("nextDay"),
										"aria-label": t("nextDay"),
									},
									h(IconChevron, { direction: "right" }),
								),
								date && date !== today && h(
									"button",
									{ type: "button", className: "sf-linkBtn", onClick: () => chooseDate(today) },
									t("backToday"),
								),
							),
							h(
								"div",
								{ className: "sf-tabs", role: "tablist" },
								h(
									"button",
									{
										type: "button",
										role: "tab",
										className: "sf-tab",
										"data-active": tab === "signals",
										"aria-selected": tab === "signals",
										onClick: () => setTab("signals"),
									},
									t("tabSignals"),
									h("span", { className: "sf-tabNum" }, signals.length),
								),
								h(
									"button",
									{
										type: "button",
										role: "tab",
										className: "sf-tab",
										"data-active": tab === "opportunities",
										"aria-selected": tab === "opportunities",
										onClick: () => setTab("opportunities"),
									},
									t("tabOpps"),
									h("span", { className: "sf-tabNum" }, opportunityCount),
								),
								h(
									"button",
									{
										type: "button",
										role: "tab",
										className: "sf-tab",
										"data-active": tab === "all",
										"aria-selected": tab === "all",
										onClick: () => setTab("all"),
									},
									t("tabAll"),
									h("span", { className: "sf-tabNum" }, itemCount),
								),
							),
						),
						!loading && h(
							"details",
							{ className: "sf-paperBox" },
							h(
								"summary",
								{ className: "sf-paperSummary" },
								h("span", { className: "sf-paperSummaryMain" }, h(IconPaper, { size: 15 }), t("paperReadTitle")),
								h("span", { className: "sf-paperSummaryHint" }, t("paperReadHint")),
							),
							h(
								"div",
								{ className: "sf-paperBody" },
								h("textarea", {
									className: "sf-paperInput",
									rows: 2,
									value: paperInput,
									placeholder: t("paperPlaceholder"),
									"aria-label": t("paperPlaceholder"),
									onChange: (event) => setPaperInput(event.target.value),
									onKeyDown: (event) => {
										if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
											event.preventDefault();
											startManualPaper();
										}
									},
								}),
								h(
									"button",
									{
										type: "button",
										className: "sf-primary sf-paperStart",
										onClick: startManualPaper,
										disabled: !paperInput.trim() || paperBusy,
									},
									paperBusy ? t("paperStarting") : t("paperStart"),
								),
							),
						),
						loading && h(
							"div",
							{ className: "sf-list", style: { marginTop: 18 } },
							h("div", { className: "sf-skeleton" }),
							h("div", { className: "sf-skeleton" }),
						),
						!loading && h(JobBanner, { job, t }),
						notice && h(
							"div",
							{ className: "sf-banner", "data-kind": "info", role: "status" },
							h("div", { className: "sf-bannerText" }, notice),
						),
						error && h(
							"div",
							{ className: "sf-banner", "data-kind": "error", role: "alert" },
							h(
								"div",
								{ className: "sf-bannerText" },
								h("span", { className: "sf-bannerTitle" }, t("error")),
								error,
							),
							h("button", { type: "button", className: "sf-btn", onClick: startFetch, disabled: !isToday || running }, t("retry")),
						),
						warning && h(
							"div",
							{ className: "sf-banner", "data-kind": "warn" },
							h(
								"div",
								{ className: "sf-bannerText" },
								h("span", { className: "sf-bannerTitle" }, t("warning")),
								warning,
							),
						),
						!loading && digest && h(
							"div",
							{ className: "sf-meta" },
							h("span", null, statsLine),
							h(
								"span",
								{ className: "sf-metaRight" },
								model && h("span", { className: "sf-model" }, h("i", { className: "sf-dot" }), `${t("model")} · ${model}`),
								h("span", null, t("accountNote")),
							),
						),
						!loading && showEmpty && h(EmptyState, {
							t,
							past: emptyPast,
							onStart: startFetch,
							disabled: !isToday || running,
						}),
						!loading && digest && tab === "signals" && h(
							"section",
							{ "aria-label": t("tabSignals") },
							signals.length === 0
								? h(
									"div",
									{ className: "sf-empty" },
									h("div", { className: "sf-emptyIcon" }, h(IconRadar, { size: 54 })),
									h("div", { className: "sf-emptyTitle" }, t("noSignals")),
									h("p", { className: "sf-emptyHint" }, isToday ? t("noSignalsHint") : t("noSignalsPastHint")),
								)
								: h(
									"div",
									{ className: "sf-list" },
									signals.map((item, index) => h(SignalCard, {
										key: item.id || `${item.title}-${index}`,
										item,
										index,
										t,
										onChat: handleChat,
										onPaper: handleReadPaper,
									})),
								),
						),
						!loading && digest && tab === "opportunities" && h(
							"section",
							{ "aria-label": t("tabOpps") },
							oppsError && h(
								"div",
								{ className: "sf-banner", "data-kind": "warn" },
								h(
									"div",
									{ className: "sf-bannerText" },
									h("span", { className: "sf-bannerTitle" }, t("warning")),
									oppsError,
								),
							),
							opportunityCount === 0
								? h(
									"div",
									{ className: "sf-empty" },
									h("div", { className: "sf-emptyIcon" }, h(IconRadar, { size: 54 })),
									h("div", { className: "sf-emptyTitle" }, t("noOpps")),
									h("p", { className: "sf-emptyHint" }, isToday ? t("noOppsHint") : t("noOppsPastHint")),
								)
								: h(
									"div",
									{ className: "sf-oppGrid" },
									h(
										"section",
										null,
										h(
											"div",
											{ className: "sf-sectionHead" },
											h("h2", null, t("business")),
											h("span", null, pluralize(t, business.length, "oppsUnit")),
										),
										h("p", { className: "sf-sectionHint" }, t("businessHint")),
										h(
											"div",
											{ className: "sf-oppList" },
											business.map((item, index) => h(BusinessCard, {
												key: `${item.title}-${index}`,
												item,
												index,
												t,
											})),
										),
									),
									h(
										"section",
										null,
										h(
											"div",
											{ className: "sf-sectionHead" },
											h("h2", null, t("rdev")),
											h("span", null, pluralize(t, rdev.length, "oppsUnit")),
										),
										h("p", { className: "sf-sectionHint" }, t("rdevHint")),
										h(
											"div",
											{ className: "sf-oppList" },
											rdev.map((item, index) => h(RdevCard, {
												key: `${item.title}-${index}`,
												item,
												index,
												t,
											})),
										),
									),
								),
						),
						!loading && digest && tab === "all" && h(
							"section",
							{ "aria-label": t("tabAll") },
							allItems.length === 0
								? h(
									"div",
									{ className: "sf-empty" },
									h("div", { className: "sf-emptyIcon" }, h(IconRadar, { size: 54 })),
									h("div", { className: "sf-emptyTitle" }, t("noItemsTitle")),
									h("p", { className: "sf-emptyHint" }, isToday ? t("noItemsHint") : t("noItemsPastHint")),
									isToday && h(
										"div",
										{ className: "sf-emptyActions" },
										h(
											"button",
											{ type: "button", className: "sf-primary", onClick: startFetch, disabled: running },
											h(IconRefresh, { size: 14 }),
											running ? t("refreshing") : t("fetch"),
										),
									),
								)
								: h(
									React.Fragment,
									null,
									h(
										"div",
										{ className: "sf-allBar" },
										h(
											"label",
											{ className: "sf-searchBox" },
											h(IconSearch, { size: 14 }),
											h("input", {
												type: "search",
												value: query,
												placeholder: t("searchPlaceholder"),
												"aria-label": t("searchPlaceholder"),
												onChange: (event) => setQuery(event.target.value),
											}),
										),
										h("span", { className: "sf-allCount" }, `${filteredItems.length} / ${allItems.length} ${t("itemsUnit")}`),
									),
									h(
										"div",
										{ className: "sf-catTabs", role: "tablist" },
										h(
											"button",
											{
												type: "button",
												role: "tab",
												className: "sf-catTab",
												"data-active": categoryFilter === "all",
												"aria-selected": categoryFilter === "all",
												onClick: () => setCategoryFilter("all"),
											},
											t("categoryAll"),
											h("span", { className: "sf-catCount" }, allItems.length),
										),
										categories.map((category) => h(
											"button",
											{
												key: category,
												type: "button",
												role: "tab",
												className: "sf-catTab",
												"data-active": categoryFilter === category,
												"aria-selected": categoryFilter === category,
												onClick: () => setCategoryFilter(category),
											},
											category,
											h("span", { className: "sf-catCount" }, categoryCounts.get(category) ?? 0),
										)),
									),
									h("p", { className: "sf-allHint" }, t("allHint")),
									unenrichedCount > 0 && h(
										"div",
										{ className: "sf-banner", "data-kind": "warn" },
										h(
											"div",
											{ className: "sf-bannerText" },
											h("span", { className: "sf-bannerTitle" }, t("notEnrichedTitle")),
											`${unenrichedCount} ${t("notEnrichedHint")}`,
										),
										h(
											"button",
											{ type: "button", className: "sf-btn", onClick: startEnrich, disabled: running },
											enriching ? t("enriching") : t("enrichAction"),
										),
									),
									filteredItems.length === 0
										? h(
											"div",
											{ className: "sf-empty" },
											h("div", { className: "sf-emptyTitle" }, t("noMatch")),
											h("p", { className: "sf-emptyHint" }, t("noMatchHint")),
										)
										: h(
											"div",
											{ className: "sf-list" },
											filteredItems.map((item, index) => h(IntelCard, {
												key: item.id || `${item.title}-${index}`,
												item,
												t,
												onChat: handleChat,
												onPaper: handleReadPaper,
											})),
										),
								),
						),
						!loading && digest && sources.length > 0 && h(
							"details",
							{ className: "sf-coverage" },
							h(
								"summary",
								null,
								`${t("sourceCoverage")} · ${okSources}/${sources.length}`,
							),
							h(
								"div",
								{ className: "sf-sourceList" },
								sources.map((source) => h(
									"span",
									{
										className: "sf-sourceItem",
										key: source.name,
										"data-ok": source.ok,
										title: source.error || "",
									},
									`${source.name} · ${source.count}`,
								)),
							),
						),
						!loading && digest && h(
							"footer",
							{ className: "sf-footer" },
							h("span", null, `${t("accountNote")}${model ? ` · ${model}` : ""}`),
							h("span", null, `${t("generatedAt")} ${formatTime(digest.generatedAt)}`),
						),
					),
				),
			);
		}

		/* ------------------------------------------------------------------ *
		 * Registration
		 * ------------------------------------------------------------------ */

		const inject = ["slots", "locale"];

		function buildArticlePrompt(item) {
			const category = itemCategory(item);
			const details = Array.isArray(item.details) ? item.details : [];
			const evidence = item.evidence_note || evidenceFor(item);
			return [
				"我想继续讨论这条 AI 情报。",
				"",
				`标题：${item.title}`,
				item.url ? `链接：${item.url}` : "",
				`来源：${item.source}${category ? `（${category}）` : ""}`,
				item.published_at ? `时间：${formatTime(item.published_at)}` : "",
				"",
				item.finding ? `发现了什么：${item.finding}` : "",
				item.why_read ? `为什么值得看：${item.why_read}` : "",
				evidence ? `依据与边界：${evidence}` : "",
				item.summary ? `原始摘要：${item.summary}` : "",
				details.length > 0 ? `关键信息：\n${details.map((detail) => `- ${detail}`).join("\n")}` : "",
				"",
				"请基于以上材料继续和我讨论：这条情报对我（独立开发者/产品人）意味着什么？有哪些可以验证的机会、风险或下一步？如果材料不足，请明确说需要我补充什么。",
			].filter(Boolean).join("\n");
		}

		const PAPER_OUTPUT_ASK = [
			"先抓取全文；如果抓不到，明确说明只能基于已有材料做有限判断。不要假装看过图片，图只能读 caption 和正文描述。",
			"请按论文精读协议输出：论文类型与一句话贡献、阅读顺序、核心主张与边界、假设与结果、关键方程、实验审查、心智图谱、停止条件、是否采用的判断、输出练习。",
			"中文回答，术语保留英文，引用章节/图表编号；证据不足或未获取的内容直接说明。",
		].join("\n");

		function buildPaperPrompt(item) {
			const category = itemCategory(item);
			const details = Array.isArray(item.details) ? item.details : [];
			return [
				"请使用 paper-reading 技能，按论文精读协议读这篇论文。",
				"",
				`标题：${item.title}`,
				item.url ? `链接：${item.url}` : "",
				`来源：${item.source}${category ? `（${category}）` : ""}`,
				item.published_at ? `时间：${formatTime(item.published_at)}` : "",
				"",
				item.summary ? `摘要：${item.summary}` : "",
				item.finding ? `情报里的速读：${item.finding}` : "",
				item.why_read ? `情报里的判断：${item.why_read}` : "",
				details.length > 0 ? `关键信息：\n${details.map((detail) => `- ${detail}`).join("\n")}` : "",
				"",
				PAPER_OUTPUT_ASK,
			].filter(Boolean).join("\n");
		}

		function normalizePaperReference(raw) {
			const text = String(raw ?? "").trim();
			if (!text) return { kind: "empty", text: "" };
			if (/^https?:\/\//i.test(text)) return { kind: "url", text };
			const arxiv = text.match(/^(?:arxiv:\s*)?(\d{4}\.\d{4,5})(v\d+)?$/i);
			if (arxiv) return { kind: "url", text: `https://arxiv.org/abs/${arxiv[1]}${arxiv[2] ?? ""}` };
			const doi = text.match(/^10\.\d{4,9}\/\S+$/);
			if (doi) return { kind: "doi", text: `https://doi.org/${text}` };
			return { kind: "text", text };
		}

		function buildManualPaperPrompt(raw) {
			const reference = normalizePaperReference(raw);
			const target = reference.kind === "url"
				? `论文链接：${reference.text}`
				: reference.kind === "doi"
					? `论文 DOI：${reference.text}`
					: `用户提供的论文信息：\n${reference.text}`;
			return [
				"请使用 paper-reading 技能，按论文精读协议读这篇论文。",
				"",
				target,
				"",
				PAPER_OUTPUT_ASK,
			].filter(Boolean).join("\n");
		}

		function apply(ctx) {
			ctx.effect(() => ctx.locale.register(NS, { zh: ZH, en: EN }));
			const t = typeof ctx.locale.bind === "function" ? ctx.locale.bind(NS) : (key) => ZH[key] || key;

			const startChatWithPrompt = async (prompt) => {
				let copied = false;
				try {
					if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
						await navigator.clipboard.writeText(prompt);
						copied = true;
					}
				} catch {
					// Clipboard is best-effort; the new-conversation draft is the primary path.
				}
				try {
					const workspace = typeof ctx.get === "function" ? ctx.get("uiWorkspace") : undefined;
					const workspaceSnapshot = workspace?.workspaces?.list?.getSnapshot?.();
					const workspaceCount = workspaceSnapshot?.items?.length ?? 0;
					if (workspace && typeof workspace.startSession === "function" && workspaceCount > 0) {
						workspace.startSession(undefined, {
							prompt,
							clearPreviousDraft: true,
							whenDraftExists: "replace",
						});
						return { ok: true, copied };
					}
				} catch (error) {
					return { ok: false, copied, error: error instanceof Error ? error.message : String(error) };
				}
				return { ok: false, copied, error: "uiWorkspace unavailable" };
			};

			const openArticleChat = (item) => startChatWithPrompt(buildArticlePrompt(item));
			const openPaperChat = (item) => startChatWithPrompt(buildPaperPrompt(item));
			const openManualPaper = (raw) => startChatWithPrompt(buildManualPaperPrompt(raw));

			ctx.slots.inject("sidebar.panellist", () =>
				ctx.slots.register(
					{
						name: "sidebar.panellist",
						id: "signalforge",
						order: 24,
						label: () => t("panel"),
						locale: NS,
					},
					SignalForgeIcon,
				),
			);

			ctx.slots.inject("main", () =>
				ctx.slots.register(
					{
						name: "main",
						key: "signalforge",
						locale: NS,
						inject: () => ({ openArticleChat, openPaperChat, openManualPaper }),
					},
					SignalForgePage,
				),
			);

			ctx.slots.inject("conversation.view", () =>
				ctx.slots.register(
					{
						name: "conversation.view",
						id: "signalforge",
						order: 24,
						label: () => t("panel"),
						locale: NS,
						inject: () => ({ openArticleChat, openPaperChat, openManualPaper }),
					},
					SignalForgePage,
				),
			);

			console.info("[signalforge] client loaded: sidebar panel + conversation view");
		}

		return { inject, apply };
	},
});
