import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");

const registrations = [];
globalThis.window = {
	__ModuleLoader__: {
		load({ id, factory }) {
			const loaded = factory((name) => {
				if (name === "react") return React;
				throw new Error(`unexpected module: ${name}`);
			});
			globalThis.__loadedModule = { id, loaded };
		},
	},
};

await import("../client.js");
const { id, loaded } = globalThis.__loadedModule;
console.log("module", id, Boolean(loaded.apply), loaded.inject);

const copy = {
	zh: { meta: {} },
};
const ctx = {
	effect(fn) {
		const dispose = fn();
		return typeof dispose === "function" ? dispose : () => {};
	},
	locale: {
		register() {},
		bind() {
			return (key) => key;
		},
	},
	slots: {
		inject(_name, fn) {
			return fn();
		},
		register(options, component) {
			registrations.push({ options, component });
			return () => {};
		},
	},
	get() {
		return undefined;
	},
};
loaded.apply(ctx);
console.log("registrations", registrations.map((item) => item.options.name));

const main = registrations.find((item) => item.options.name === "main");
const html = renderToStaticMarkup(React.createElement(main.component, {}));
console.log("rendered", html.length, "bytes");
console.log(html.slice(0, 220));
