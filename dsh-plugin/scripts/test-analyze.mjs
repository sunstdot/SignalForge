import { analyzeSignals, analyzeOpportunities } from "../src/analyze.js";

const candidates = [
	{ id: "a", title: "Show HN: OnKey", url: "https://example.com/a", source: "Hacker News", source_type: "hn", published_at: new Date().toISOString(), summary: "A developer built an app with Claude Code to show where they are off-key.", relevance_score: 9, metadata: { points: 44, comments: 24, engagement: "44 points, 24 comments" } },
	{ id: "b", title: "Simulated Control Evals", url: "https://example.com/b", source: "arXiv", source_type: "arxiv", published_at: new Date().toISOString(), summary: "We propose simulated control evaluations that run in deployment-like environments.", relevance_score: 8, metadata: {} },
];

function stubCtx(text) {
	return {
		agentDefaultModel: { currentSelection: () => ({ provider: "deepseek-account", model: "deepseek-flash" }) },
		llm: {
			prepareCall: async (config) => ({
				config,
				stream: () => (async function* () {
					yield { type: "reasoning-delta", index: 0, text: "thinking" };
					yield { type: "text-delta", index: 0, text };
					yield { type: "finish", reason: { kind: "stop" } };
				})(),
			}),
		},
	};
}

const signalText = JSON.stringify({
	signals: [
		{ idx: 1, track: "inspiration", tags: ["新能力新用法"], finding: "开发者用 Claude Code 做出实时跑调检测应用。", why_read: "AI 编程把个人痛点做成产品的门槛降到接近零。", details: ["44 points, 24 comments", "作者自称唱歌很差"] },
		{ idx: 2, track: "execution", tags: ["实践方法"], finding: "论文提出模拟控制评估，在贴近部署的环境中检验护栏。", why_read: "安全评估可以更早进入部署环境。", details: ["在模拟环境中运行"] },
	],
});
const signals = await analyzeSignals(stubCtx(signalText), candidates, "2026-11-04", { maxSignals: 5 });
console.log("signals", signals.signals.length, signals.signals.map((item) => [item.title, item.finding.slice(0, 12), item.evidence_note]));

const oppText = JSON.stringify({
	business: [{ source_idx: 1, title: "跑调纠正陪练", trigger: "实时音高检测", core_insight: "把实时检测包装成陪练", product_form: "面向业余歌手的练习工具", target_users: "想学唱歌的年轻人", mvp_features: ["实时跑调提示", "练习记录"], business_model: "订阅 19 元/月", risks: "获客", scores: { pain_point: 4, market_size: 3, tech_timing: 5, buildability: 5 } }],
	rdev: [{ source_idx: 2, type: "研发提效", title: "部署态护栏回放", trigger: "模拟控制评估", scenario: "现在安全评估只在测试床跑", ai_solution: "把评估搬进预发环境", implementation: "CI 插件", audience: ["后端", "测试"], impact: "提前发现风险", difficulty: "中", resistance: "环境权限", scores: { efficiency: 7, feasibility: 6, business_impact: 6, overall: 7 } }],
});
const opps = await analyzeOpportunities(stubCtx(oppText), signals.signals, "2026-11-04");
console.log("opps", opps.business.length, opps.business[0].title, opps.business[0].total_score, opps.rdev.length, opps.rdev[0].total_score);
