import { collectCandidates } from "../src/sources.js";

const result = await collectCandidates({
	lookbackHours: 48,
	timeoutMs: 16000,
	onProgress: (progress) => {
		if (progress.source) process.stderr.write(`\r${progress.done}/${progress.total} ${progress.source}          `);
	},
});
process.stderr.write("\n");
console.log(JSON.stringify({
	allCount: result.allCount,
	selected: result.candidates.length,
	elapsedMs: result.elapsedMs,
	stats: result.stats,
	sample: result.candidates.slice(0, 8).map((item) => ({
		title: item.title,
		source: item.source,
		type: item.source_type,
		score: item.relevance_score,
		published: item.published_at,
	})),
}, null, 2));
