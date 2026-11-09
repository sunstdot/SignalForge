import { execFileSync } from "node:child_process";
import { readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const files = [];
function walk(dir) {
	for (const name of readdirSync(dir)) {
		const file = path.join(dir, name);
		const stat = statSync(file);
		if (stat.isDirectory()) {
			if (name === "node_modules" || name.startsWith(".")) continue;
			walk(file);
		} else if (name.endsWith(".js") || name.endsWith(".mjs")) {
			files.push(file);
		}
	}
}
walk(root);
for (const file of files.sort()) {
	execFileSync(process.execPath, ["--check", file], { stdio: "inherit" });
}
console.log(`checked ${files.length} JavaScript files`);
