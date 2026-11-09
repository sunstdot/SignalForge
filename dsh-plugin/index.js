/**
 * Host half of the SignalForge bundle.
 *
 * It owns the daily pipeline (source collection → LLM signal selection → LLM
 * opportunity mining), stores one digest per day under `$DSH_HOME/signalforge`,
 * and exposes a same-origin JSON API for the sidebar panel:
 *
 *   GET    /signalforge/api/bootstrap?date=YYYY-MM-DD
 *   GET    /signalforge/api/digest?date=YYYY-MM-DD
 *   POST   /signalforge/api/jobs            { date }
 *   GET    /signalforge/api/jobs/:id
 *   DELETE /signalforge/api/jobs/:id
 *
 * Analysis routes through `ctx.llm` with the current default model selection,
 * so calls use the signed-in account rather than a separate API key.
 */
import os from "node:os";
import path from "node:path";
import { registerApi } from "./src/http.js";
import { createPipeline } from "./src/pipeline.js";
import { PAPER_SKILL_CONTENT, PAPER_SKILL_DESCRIPTION, PAPER_SKILL_NAME, PAPER_SKILL_WHEN } from "./src/paper-skill.js";
import { DigestStore } from "./src/store.js";

export const name = "signalforge";

/** Services the daily pipeline needs; the web route is injected separately. */
export const inject = ["llm", "agentDefaultModel"];


function resolveDataDir(config) {
	if (typeof config?.dataDir === "string" && config.dataDir.trim()) return path.resolve(config.dataDir.trim());
	const home = process.env.DSH_HOME && process.env.DSH_HOME.trim()
		? process.env.DSH_HOME.trim()
		: path.join(os.homedir(), ".dsh");
	return path.join(home, "signalforge");
}

export function apply(ctx, config = {}) {
	const options = config && typeof config === "object" ? config : {};
	const dataDir = resolveDataDir(options);
	const store = new DigestStore(dataDir);
	const logger = ctx.logger && typeof ctx.logger.info === "function" ? ctx.logger : console;
	const pipeline = createPipeline({
		ctx,
		store,
		config: options,
		logger,
	});

	ctx.effect(() => () => pipeline.dispose(), "signalforge: pipeline lifetime");

	ctx.inject(["webServer"], (webCtx) => {
		registerApi(webCtx, {
			pipeline,
			store,
			config: { ...options, dataDir },
		});
	});

	ctx.inject(["skills"], (skillCtx) => {
		skillCtx.effect(
			() => skillCtx.skills.register({
				name: PAPER_SKILL_NAME,
				description: PAPER_SKILL_DESCRIPTION,
				whenToUse: PAPER_SKILL_WHEN,
				source: "signalforge",
				content: PAPER_SKILL_CONTENT,
			}),
			"signalforge: paper reading skill",
		);
	});

	logger.info?.(`[signalforge] ready · data=${dataDir} · tz=${pipeline.settings.timezone}`);
}
