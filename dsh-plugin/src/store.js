import { mkdir, readFile, readdir, rename, writeFile } from "node:fs/promises";
import path from "node:path";

async function readJson(file) {
	try {
		return JSON.parse(await readFile(file, "utf8"));
	} catch (error) {
		if (error?.code === "ENOENT") return null;
		if (error instanceof SyntaxError) return null;
		throw error;
	}
}

async function writeJsonAtomic(file, value) {
	const temporary = `${file}.${process.pid}.${Date.now()}.tmp`;
	await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, "utf8");
	await rename(temporary, file);
}

export class DigestStore {
	constructor(dataDir) {
		this.dataDir = dataDir;
		this.digestsDir = path.join(dataDir, "digests");
		this.indexFile = path.join(dataDir, "index.json");
		this.ready = mkdir(this.digestsDir, { recursive: true });
	}

	async loadDigest(date) {
		await this.ready;
		return await readJson(path.join(this.digestsDir, `${date}.json`));
	}

	async saveDigest(digest) {
		await this.ready;
		await writeJsonAtomic(path.join(this.digestsDir, `${digest.date}.json`), digest);
		await this.updateIndex(digest);
		return digest;
	}

	async readIndex() {
		await this.ready;
		const index = await readJson(this.indexFile);
		if (index && Array.isArray(index.dates)) return index;
		return { version: 1, updatedAt: null, dates: [] };
	}

	async listDates() {
		const index = await this.readIndex();
		if (index.dates.length > 0) return index.dates;
		await this.ready;
		let names = [];
		try {
			names = await readdir(this.digestsDir);
		} catch {
			return [];
		}
		const dates = [];
		for (const name of names) {
			const match = name.match(/^(\d{4}-\d{2}-\d{2})\.json$/);
			if (!match) continue;
			const digest = await this.loadDigest(match[1]);
			if (digest) dates.push(summaryOf(digest));
		}
		return dates.sort((a, b) => b.date.localeCompare(a.date));
	}

	async updateIndex(digest) {
		const index = await this.readIndex();
		const entry = summaryOf(digest);
		const dates = index.dates.filter((item) => item.date !== digest.date);
		dates.push(entry);
		dates.sort((a, b) => b.date.localeCompare(a.date));
		await writeJsonAtomic(this.indexFile, {
			version: 1,
			updatedAt: new Date().toISOString(),
			dates: dates.slice(0, 180),
		});
	}
}

export function summaryOf(digest) {
	return {
		date: digest.date,
		generatedAt: digest.generatedAt,
		items: Array.isArray(digest.items) ? digest.items.length : 0,
		signals: Array.isArray(digest.signals) ? digest.signals.length : 0,
		business: Array.isArray(digest.opportunities?.business) ? digest.opportunities.business.length : 0,
		rdev: Array.isArray(digest.opportunities?.rdev) ? digest.opportunities.rdev.length : 0,
		model: digest.analysis?.model ?? null,
		warning: digest.analysis?.warning ?? null,
	};
}
