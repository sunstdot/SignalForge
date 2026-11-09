import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { importLegacy } from "../src/legacy.js";
import { DigestStore } from "../src/store.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const positional = process.argv.slice(2).filter((arg) => !arg.startsWith("--"));
const repoRoot = positional[0] ? path.resolve(positional[0]) : path.resolve(here, "../..");
const dataHome = process.env.DSH_HOME && process.env.DSH_HOME.trim()
	? process.env.DSH_HOME.trim()
	: path.join(os.homedir(), ".dsh");
const dataDir = process.env.SIGNALFORGE_DATA_DIR && process.env.SIGNALFORGE_DATA_DIR.trim()
	? path.resolve(process.env.SIGNALFORGE_DATA_DIR.trim())
	: path.join(dataHome, "signalforge");
const force = process.argv.includes("--force");
const includeToday = process.argv.includes("--include-today");

const store = new DigestStore(dataDir);
const result = await importLegacy({ repoRoot, store, force, includeToday });
console.log(JSON.stringify({
	repoRoot,
	dataDir,
	force,
	includeToday,
	...result,
}, null, 2));
