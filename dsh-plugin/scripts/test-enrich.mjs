import { enrichItems } from "../src/analyze.js";

const items = [
	{ id: "a", title: "Show HN: OnKey", source: "Hacker News", source_type: "hn", category: "资讯", summary: "A developer built an app to show where they are off-key.", published_at: null, relevance_score: 9 },
	{ id: "b", title: "Simulated Control Evals", source: "arXiv", source_type: "arxiv", category: "论文", summary: "We propose simulated control evaluations.", published_at: null, relevance_score: 8 },
];

const ctx = {
	agentDefaultModel: { currentSelection: () => ({ provider: "deepseek-account", model: "deepseek-flash" }) },
	llm: {
		prepareCall: async (config) => ({
			config,
			stream: () => (async function* () {
				yield { type: "text-delta", index: 0, text: JSON.stringify({ items: [
					{ idx: 1, finding: "开发者用 AI 编程工具做了一个实时显示跑调位置的应用。", why_read: "个人痛点可以借助 AI 编程快速做成小产品。", tags: ["新能力新用法"], details: ["作者自称唱歌很差"] },
					{ idx: 2, finding: "论文提出在贴近部署的模拟环境中做控制评估。", why_read: "安全评估可以更早覆盖真实部署特征。", tags: ["实践方法"], details: [] },
				] }) };
				yield { type: "finish", reason: { kind: "stop" } };
			})(),
		}),
	},
};

const result = await enrichItems(ctx, items, { date: "2026-11-04", batchSize: 2, concurrency: 1 });
console.log({ enriched: result.enriched, warning: result.warning, finding: result.items[0].finding, why: result.items[1].why_read });
if (result.enriched !== 2 || result.items[0].finding !== "开发者用 AI 编程工具做了一个实时显示跑调位置的应用。") process.exit(1);
