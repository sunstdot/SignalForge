"""调研流水线编排。

一次 run 的顺序固定为 plan → search → fetch → extract → verify → synthesize → validate。
每一步把产物落盘并推进 state.json 的游标，所以中断后可以从当前阶段续跑，
不需要重跑已经花过钱的部分。

设计取舍：
- 单进程顺序执行。调研是长任务（20-40 分钟），并发会放大限流和额度风险，
  而且用户看不懂一个跑到一半被限流的报告。
- 抓取并发（网络 IO），LLM 调用串行（避免被打限流）。
- 任何阶段失败都把 run 标成 failed 并保留已有产物，不删数据。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

from . import fetcher, models, search_backend, stages, store, validator

logger = logging.getLogger(__name__)

FETCH_CONCURRENCY = 5
EXTRACT_CONCURRENCY = 4
MAX_CLAIMS_PER_SOURCE = 12

# 抽取阶段最多处理多少个来源。不设上限会让一次调研变成几小时的长任务，
# 而且多出来的往往是转述同一篇报道的低价值来源。
MAX_EXTRACT_SOURCES = 60
# 正文短于这个长度基本是反爬提示页/跳转页，抽不出东西，直接跳过。
MIN_EXTRACT_CHARS = 200
# 每层的来源配额：官方与一手材料优先，媒体其次，secondary 只留少量作补充。
TIER_QUOTA = {"official": 24, "firsthand": 20, "media": 10, "secondary": 6}


class ResearchPipeline:
    def __init__(self, run: models.Run, *, backend: Optional[search_backend.SearchBackend] = None):
        self.run = run
        self.backend = backend or search_backend.resolve_backend()

    # ── plan ──
    async def run_plan(self) -> models.Plan:
        plan = await stages.plan_research(self.run.topic, self.run.questions, self.run.as_of)
        store.save_plan(self.run.id, plan)
        store.set_stage(self.run, "plan", "planned")
        return plan

    # ── search ──
    async def run_search(self, plan: dict) -> List[models.Source]:
        existing = {s.get("url") for s in store.list_sources(self.run.id)}
        collected: Dict[str, models.Source] = {}

        for sub_question in plan.get("sub_questions", []):
            for query in sub_question.get("queries", [])[:4]:
                try:
                    results = await self.backend.search(query, top_k=8)
                except Exception as exc:  # 单个检索式失败不该拖垮整个 run
                    logger.warning("search failed query=%r err=%s", query, exc)
                    continue
                for item in results:
                    if item.url in existing or item.url in collected:
                        continue
                    source_id = f"src{len(collected) + 1}"
                    collected[item.url] = models.Source(
                        id=source_id,
                        url=item.url,
                        title=item.title,
                        tier=item.source_tier,
                        published=item.published,
                        text=(item.raw_content or "").strip(),
                        fetch_status="ok" if item.raw_content else "skipped",
                        fetch_detail="搜索服务已返回正文" if item.raw_content else "",
                    )

        for source in collected.values():
            store.save_source(self.run.id, source)
        store.set_stage(self.run, "search", "searched")
        return list(collected.values())

    # ── fetch ──
    async def run_fetch(self) -> List[dict]:
        sources = store.list_sources(self.run.id)
        pending = [s for s in sources if s.get("fetch_status") == "skipped" and s.get("url")]
        semaphore = asyncio.Semaphore(FETCH_CONCURRENCY)

        async def one(source: dict) -> None:
            async with semaphore:
                result = await fetcher.fetch_document(source["url"])
                source["text"] = result["text"]
                source["fetch_status"] = result["status"]
                source["fetch_detail"] = result["detail"]
                source["fetched_at"] = models._now()
                store.save_source(
                    self.run.id,
                    models.Source(**{k: v for k, v in source.items() if k in models.Source.__dataclass_fields__}),
                )

        await asyncio.gather(*(one(s) for s in pending), return_exceptions=True)
        store.set_stage(self.run, "fetch", "fetched")
        return store.list_sources(self.run.id)

    # ── extract ──
    def _select_for_extraction(self) -> List[dict]:
        """挑出值得送入模型的来源。

        不设上限的话，一次检索会拿到两三百个来源，串行抽取要跑几个小时，
        模型额度也会被大量转述稿吃掉。这里按来源分层给配额，同层内按正文长度排序
        ——长正文更可能是完整报道/访谈，短的多半是摘要页。
        """
        candidates = [
            s for s in store.list_sources(self.run.id)
            if len((s.get("text") or "").strip()) >= MIN_EXTRACT_CHARS
        ]

        selected: List[dict] = []
        for tier, quota in TIER_QUOTA.items():
            pool = [s for s in candidates if s.get("tier") == tier]
            pool.sort(key=lambda s: len((s.get("text") or "").strip()), reverse=True)
            selected.extend(pool[:quota])

        if len(selected) < MAX_EXTRACT_SOURCES:
            chosen = {s["id"] for s in selected}
            rest = [s for s in candidates if s["id"] not in chosen]
            rest.sort(key=lambda s: len((s.get("text") or "").strip()), reverse=True)
            selected.extend(rest[: MAX_EXTRACT_SOURCES - len(selected)])

        return selected

    async def run_extract(self, plan: dict) -> List[models.Claim]:
        sources = self._select_for_extraction()
        entities = plan.get("entities", [])
        semaphore = asyncio.Semaphore(EXTRACT_CONCURRENCY)
        # 每个来源的起始编号先占位分配，保证并发下 claim id 不撞车
        counters = iter(range(0, len(sources) * MAX_CLAIMS_PER_SOURCE, MAX_CLAIMS_PER_SOURCE))
        collected: List[models.Claim] = []
        done = 0

        async def one(source: dict, start_index: int) -> List[models.Claim]:
            async with semaphore:
                try:
                    claims = await stages.extract_claims(source, entities, start_index=start_index)
                except Exception as exc:
                    logger.warning("extract failed source=%s err=%s", source.get("id"), exc)
                    return []
                # 引文对不上的直接丢弃，不进入后续核验
                kept = [c for c in claims if stages.quote_is_verbatim(c.quote, source.get("text", ""))]
                return kept[:MAX_CLAIMS_PER_SOURCE]

        # 每完成一批就落盘一次：整阶段跑完才写的话，用户看不到进度，
        # 中途中断也会把已经花掉的抽取全部丢掉。
        tasks = [asyncio.create_task(one(s, next(counters))) for s in sources]
        for task in asyncio.as_completed(tasks):
            batch = await task
            done += 1
            if isinstance(batch, list) and batch:
                collected.extend(batch)
                store.save_claims(self.run.id, collected)
            if done % 10 == 0:
                logger.info("extract progress %s/%s", done, len(sources))

        store.set_stage(self.run, "extract", "extracting")
        return collected

    # ── verify ──
    async def run_verify(self) -> List[models.Verdict]:
        claims = store.get_claims(self.run.id)
        sources = store.source_lookup(self.run.id)
        verdicts = await stages.verify_claims(claims, sources)
        store.save_verification(self.run.id, verdicts)
        store.set_stage(self.run, "verify", "verified")
        return verdicts

    # ── synthesize + validate ──
    async def run_synthesize(self, plan: dict) -> List[dict]:
        claims = store.claim_lookup(self.run.id)
        sources = store.source_lookup(self.run.id)
        verdicts = store.get_verification(self.run.id)

        drafts: List[dict] = []
        for section in plan.get("sections", []):
            try:
                draft = await stages.synthesize_section(section, verdicts, claims)
            except Exception as exc:
                logger.warning("synthesize failed section=%s err=%s", section.get("id"), exc)
                draft = models.SectionDraft(
                    section_id=section.get("id", ""),
                    heading=section.get("heading", ""),
                    markdown="",
                    rejected=[{"type": "generation_failed", "detail": str(exc)}],
                )
            drafts.append(draft.as_dict())

        store.set_stage(self.run, "synthesize", "synthesized")
        return drafts

    async def run_synthesize_with_validate(self, plan: dict, max_rounds: int = 2) -> List[dict]:
        """写完立刻校验，不通过就带着问题原因重写，最多 max_rounds 轮。

        单靠 prompt 要求"标注来源"不足以让模型照做，必须机器校验并回灌失败原因。
        仍然不过就保留最后一版并记录问题，让读者知道这一节的可信度打了折。
        """
        claims = store.claim_lookup(self.run.id)
        sources = store.source_lookup(self.run.id)
        verdicts = store.get_verification(self.run.id)
        drafts: List[dict] = []

        for section in plan.get("sections", []):
            problems: List[dict] = []
            draft: Optional[models.SectionDraft] = None
            passed = False

            for round_index in range(max_rounds + 1):
                try:
                    draft = await stages.synthesize_section(
                        section, verdicts, claims, problems or None,
                    )
                except Exception as exc:
                    logger.warning("synthesize failed section=%s err=%s", section.get("id"), exc)
                    draft = models.SectionDraft(
                        section_id=section.get("id", ""),
                        heading=section.get("heading", ""),
                        markdown="",
                        rejected=[{"type": "generation_failed", "detail": str(exc)}],
                    )
                    break

                draft_dict = draft.as_dict()
                passed, problems = validator.check_section(draft_dict, claims, sources, verdicts)
                if passed:
                    break
                logger.info(
                    "section %s round %s failed validation: %s problems",
                    section.get("id"), round_index + 1, len(problems),
                )

            final = draft.as_dict() if draft else {"section_id": section.get("id", ""), "heading": section.get("heading", ""), "markdown": ""}
            final["passed"] = passed
            final["rejected"] = [] if passed else problems
            drafts.append(final)

        store.set_stage(self.run, "synthesize", "synthesized")
        return drafts

    def run_validate(self, plan: dict, drafts: List[dict]) -> List[dict]:
        claims = store.claim_lookup(self.run.id)
        sources = store.source_lookup(self.run.id)
        verdicts = store.get_verification(self.run.id)

        for draft in drafts:
            ok, problems = validator.check_section(draft, claims, sources, verdicts)
            draft["rejected"] = problems
            draft["passed"] = ok
        store.set_stage(self.run, "validate", "validated")
        return drafts

    # ── 从某个阶段续跑 ──
    async def run_from(self, stage: str = "verify") -> dict:
        """从指定阶段续跑，复用已有产物。

        stage="verify" 用于调整核验逻辑后补跑：来源、论断、plan 都在盘上，
        只重跑核验 → 成稿 → 校验。
        """
        plan_dict = store.get_plan(self.run.id)
        if not plan_dict:
            raise RuntimeError("缺少 plan.json，无法从该阶段续跑，请重跑整个调研")

        self.run.status = "running"
        self.run.error = ""
        store.save_run(self.run)

        if stage == "verify":
            await self.run_verify()
        elif stage == "synthesize":
            pass  # 核验结果已在盘上，直接进成稿
        else:
            raise ValueError(f"不支持从阶段 {stage} 续跑")

        drafts = await self.run_synthesize_with_validate(plan_dict)
        return self._finalize(plan_dict, drafts)

    def _finalize(self, plan_dict: dict, drafts: List[dict]) -> dict:
        markdown = validator.build_report(
            title=self.run.topic,
            thesis=plan_dict.get("thesis", ""),
            drafts=drafts,
            claims=store.claim_lookup(self.run.id),
            verdicts=store.get_verification(self.run.id),
            sources=store.source_lookup(self.run.id),
        )
        metrics = store.coverage_metrics(self.run.id)
        metrics["sections_passed"] = sum(1 for d in drafts if d.get("passed"))
        metrics["sections_total"] = len(drafts)
        metrics["validator_problems"] = sum(len(d.get("rejected") or []) for d in drafts)
        # 明细一并落盘：只给计数的话，读者知道"有问题"却不知道问题在哪。
        metrics["validator_details"] = [
            {
                "section_id": d.get("section_id"),
                "heading": d.get("heading"),
                "passed": d.get("passed"),
                "problems": (d.get("rejected") or [])[:10],
            }
            for d in drafts
            if (d.get("rejected") or [])
        ]

        store.save_report(self.run.id, models.Report(
            title=self.run.topic, markdown=markdown, metrics=metrics,
        ))
        store.set_stage(self.run, "done", "done")
        return store.get_report(self.run.id) or {}

    # ── 全流程 ──
    async def run_all(self) -> dict:
        self.run.status = "running"
        self.run.error = ""
        store.save_run(self.run)
        try:
            plan = await self.run_plan()
            plan_dict = plan.as_dict()

            await self.run_search(plan_dict)
            await self.run_fetch()
            await self.run_extract(plan_dict)
            await self.run_verify()
            drafts = await self.run_synthesize_with_validate(plan_dict)
            return self._finalize(plan_dict, drafts)
        except Exception as exc:
            logger.exception("research run failed id=%s", self.run.id)
            self.run.status = "failed"
            self.run.error = f"{type(exc).__name__}: {exc}"
            store.save_run(self.run)
            raise


def run_sync(run_id: str) -> None:
    """供 FastAPI BackgroundTasks 调用的同步入口。"""
    run = store.get_run(run_id)
    if not run:
        return
    asyncio.run(ResearchPipeline(run).run_all())


def run_from_stage_sync(run_id: str, stage: str = "verify") -> None:
    """从指定阶段续跑，复用已有产物。

    调整核验/成稿逻辑后补跑时用：来源和论断都已落盘，没必要把抓取和抽取
    的额度再花一遍。
    """
    run = store.get_run(run_id)
    if not run:
        return
    asyncio.run(ResearchPipeline(run).run_from(stage))


async def _resume() -> None:  # pragma: no cover - 占位，保持模块结构清晰
    return None
