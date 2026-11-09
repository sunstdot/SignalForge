import os from "node:os";
import path from "node:path";
import { DigestStore } from "../src/store.js";
import { collectCandidates } from "../src/sources.js";
import { todayInZone } from "../src/util.js";

const dataHome = process.env.DSH_HOME && process.env.DSH_HOME.trim()
	? process.env.DSH_HOME.trim()
	: path.join(os.homedir(), ".dsh");
const dataDir = process.env.SIGNALFORGE_DATA_DIR && process.env.SIGNALFORGE_DATA_DIR.trim()
	? path.resolve(process.env.SIGNALFORGE_DATA_DIR.trim())
	: path.join(dataHome, "signalforge");
const store = new DigestStore(dataDir);
const date = process.argv.find((arg) => /^\d{4}-\d{2}-\d{2}$/.test(arg)) || todayInZone("Asia/Shanghai");
const digest = await store.loadDigest(date);
if (!digest) {
	console.error(`No digest for ${date}`);
	process.exit(1);
}
if (Array.isArray(digest.items) && digest.items.length > 0 && !process.argv.includes("--force")) {
	console.log(`Digest ${date} already has ${digest.items.length} items; use --force to refresh.`);
	process.exit(0);
}
const collection = await collectCandidates({
	lookbackHours: 48,
	timeoutMs: 16000,
	onProgress: (progress) => {
		if (progress.source) process.stderr.write(`\r${progress.done}/${progress.total} ${progress.source}          `);
	},
});
process.stderr.write("\n");
digest.items = collection.all;
digest.stats = {
	...(digest.stats ?? {}),
	candidates: collection.all.length,
	enriched: 0,
	itemsAt: new Date().toISOString(),
};
digest.analysis = {
	...(digest.analysis ?? {}),
	enrichmentError: null,
};
await store.saveDigest(digest);
console.log(JSON.stringify({
	date,
	items: digest.items.length,
	signals: digest.signals?.length ?? 0,
	sources: collection.stats.filter((item) => item.ok).length,
}, null, 2));
