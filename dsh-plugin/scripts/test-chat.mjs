import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const React = require("react");

const registrations = [];
globalThis.window = {
	__ModuleLoader__: {
		load({ id, factory }) {
			globalThis.__loaded = { id, loaded: factory((name) => {
				if (name === "react") return React;
				throw new Error(`unexpected module: ${name}`);
			}) };
		},
	},
};

const writes = [];
try {
	Object.defineProperty(globalThis.navigator, "clipboard", {
		value: { writeText: async (text) => { writes.push(text); } },
		configurable: true,
	});
} catch {
	// Clipboard is optional; the startSession assertion below is the primary check.
}

await import("../client.js");
const { loaded } = globalThis.__loaded;
let started = null;
const workspace = {
	workspaces: { list: { getSnapshot: () => ({ items: [{}] }) } },
	startSession: (workspaceId, options) => { started = { workspaceId, options }; },
};
const ctx = {
	effect(fn) { fn(); return () => {}; },
	locale: { register() {}, bind() { return (key) => key; } },
	slots: {
		inject(_name, fn) { return fn(); },
		register(options, component) { registrations.push({ options, component }); return () => {}; },
	},
	get(name) { return name === "uiWorkspace" ? workspace : undefined; },
};
loaded.apply(ctx);
const main = registrations.find((item) => item.options.name === "main");
const action = main.options.inject().openArticleChat;
const item = {
	id: "a", title: "Show HN: OnKey", url: "https://example.com/onkey", source: "Hacker News",
	source_type: "hn", category: "资讯", published_at: new Date().toISOString(),
	finding: "开发者做了一个实时显示跑调位置的应用。",
	why_read: "AI 编程让个人痛点更容易变成小产品。",
	evidence_note: "社区热榜（转述/讨论，非独立验证）",
	summary: "A developer built an app.", details: ["44 points", "作者自称唱歌很差"],
};
const result = await action(item);
console.log({ result, workspaceId: started?.workspaceId, hasTitle: started?.options.prompt.includes("Show HN: OnKey"), hasUrl: started?.options.prompt.includes("https://example.com/onkey"), hasFinding: started?.options.prompt.includes("开发者做了一个实时显示跑调位置的应用。"), clipboard: writes.length });
if (!result.ok || !started?.options.prompt.includes("https://example.com/onkey") || !started?.options.prompt.includes("开发者做了一个实时显示跑调位置的应用。")) process.exit(1);

const paperAction = main.options.inject().openPaperChat;
started = null;
const paper = { ...item, title: "Simulated Control Evals", url: "https://arxiv.org/abs/2610.12345", source: "arXiv", source_type: "arxiv", category: "论文", summary: "We propose simulated control evaluations.", finding: "", why_read: "", details: [] };
const paperResult = await paperAction(paper);
console.log({ paperOk: paperResult.ok, hasSkill: started?.options.prompt.includes("paper-reading"), hasPaperUrl: started?.options.prompt.includes("https://arxiv.org/abs/2610.12345"), hasProtocol: started?.options.prompt.includes("论文精读协议") });
if (!paperResult.ok || !started?.options.prompt.includes("paper-reading") || !started?.options.prompt.includes("https://arxiv.org/abs/2610.12345")) process.exit(1);

const manualAction = main.options.inject().openManualPaper;
started = null;
const manualResult = await manualAction("https://arxiv.org/abs/2610.99999");
console.log({ manualOk: manualResult.ok, hasManualUrl: started?.options.prompt.includes("https://arxiv.org/abs/2610.99999") });
if (!manualResult.ok || !started?.options.prompt.includes("https://arxiv.org/abs/2610.99999")) process.exit(1);

started = null;
const doiResult = await manualAction("10.1234/example.doi");
console.log({ doiOk: doiResult.ok, hasDoi: started?.options.prompt.includes("https://doi.org/10.1234/example.doi") });
if (!doiResult.ok || !started?.options.prompt.includes("https://doi.org/10.1234/example.doi")) process.exit(1);

console.log("chat + paper actions ok");
