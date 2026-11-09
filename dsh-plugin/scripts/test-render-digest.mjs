import { readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");

const dataDir = path.join(process.env.DSH_HOME || path.join(os.homedir(), ".dsh"), "signalforge");
const renderDate = process.env.SF_DATE || "2026-11-04";
const digest = JSON.parse(readFileSync(path.join(dataDir, `digests/${renderDate}.json`), "utf8"));
const index = JSON.parse(readFileSync(path.join(dataDir, "index.json"), "utf8"));

const registrations = [];
globalThis.window = {
	__ModuleLoader__: {
		load({ id, factory }) {
			const loaded = factory((name) => {
				if (name === "react") return ReactProxy;
				throw new Error(`unexpected module: ${name}`);
			});
			globalThis.__loadedModule = { id, loaded };
		},
	},
};

let presetIndex = 0;
const preset = [];
const ReactProxy = new Proxy(React, {
	get(target, property, receiver) {
		if (property === "useState") {
			return function useState(initial) {
				if (presetIndex < preset.length) return [preset[presetIndex++], () => {}];
				return target.useState(initial);
			};
		}
		return Reflect.get(target, property, receiver);
	},
});

await import("../client.js");
const { loaded } = globalThis.__loadedModule;
const ctx = {
	effect(fn) { fn(); return () => {}; },
	locale: { register() {}, bind() { return (key) => key; } },
	slots: { inject(_name, fn) { return fn(); }, register(options, component) { registrations.push({ options, component }); return () => {}; } },
	get() { return undefined; },
};
loaded.apply(ctx);
const main = registrations.find((item) => item.options.name === "main");

const tab = process.env.SF_TAB || "signals";
preset.push(
	renderDate,
	renderDate,
	digest,
	index.dates,
	null,
	tab,
	false,
	null,
	null,
	0,
);
const html = renderToStaticMarkup(React.createElement(main.component, {}));
const text = html.replace(/<style>[\s\S]*?<\/style>/g, " ").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
console.log("rendered", html.length, "bytes");
console.log("tab", tab);
console.log("signal cards", (html.match(/class="sf-card /g) || []).length);
console.log("intel cards", (html.match(/class="sf-card sf-intel/g) || []).length);
console.log("text has 19 条:", text.includes("19 条"));
console.log("has tab label:", text.includes("全部情报"));
console.log("has all hint:", text.includes("本次抓取的全部候选"));
console.log("has filtered count:", /\d+ \/ \d+ 条/.test(text));
console.log("category tags", (html.match(/class="sf-cat"/g) || []).length);
console.log("chat buttons", (html.match(/class="sf-chatBtn"/g) || []).length);
console.log("paper buttons", (html.match(/class="sf-paperBtn"/g) || []).length);
console.log("category chips", (html.match(/class="sf-catTab"/g) || []).length);
console.log("has raw summary label", text.includes("原始摘要"));
console.log("text snippet:", text.slice(0, 700));
