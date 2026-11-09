"""调研系统的数据结构与状态机。

一个 run 的全部产物都落在 data/research/runs/<run_id>/ 下，纯 JSON + Markdown，
不引入数据库。这样每个 run 都可以整体拷走、diff、人工修补。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

# 流水线阶段。state.json 记录游标，中断后可从当前阶段续跑。
STAGES = ("plan", "search", "fetch", "extract", "verify", "synthesize", "validate", "done")

# 抓取状态。抓不到是常态（付费墙/反爬/域名不可达），必须显式记录，
# 不能静默当成"没有这条信息"。
FETCH_STATUSES = ("ok", "paywalled", "blocked", "unreachable", "error", "skipped")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Run:
    id: str
    topic: str
    questions: List[str]
    as_of: str
    status: str = "created"
    stage: str = "plan"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    error: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class SubQuestion:
    id: str
    section: str
    question: str
    queries: List[str] = field(default_factory=list)


@dataclass
class Plan:
    thesis: str = ""
    sections: List[dict] = field(default_factory=list)
    sub_questions: List[SubQuestion] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "thesis": self.thesis,
            "sections": self.sections,
            "sub_questions": [asdict(q) for q in self.sub_questions],
            "entities": self.entities,
        }


@dataclass
class Source:
    id: str
    url: str
    title: str = ""
    tier: str = "secondary"
    fetched_at: str = ""
    fetch_status: str = "skipped"
    fetch_detail: str = ""
    published: Optional[str] = None
    text: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Claim:
    """原子论断。

    quote 必须是 source.text 的逐字片段——这是"可回查"的唯一保证。
    校验阶段会做字面命中检查，对不上的 claim 一律判为不可用。
    """
    id: str
    text: str
    quote: str
    source_id: str
    subject: str = ""
    predicate: str = ""
    as_of: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Verdict:
    """一个事实簇的核验结论。

    verdict 取值：
      confirmed —— 1 个 official，或 >=2 个互相独立的 media/firsthand 支持
      single    —— 只有一个来源支持
      conflict  —— 有来源给出不相容的说法
    """
    claim_ids: List[str]
    verdict: str
    supporters: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    note: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class SectionDraft:
    section_id: str
    heading: str
    markdown: str = ""
    claim_ids: List[str] = field(default_factory=list)
    rejected: List[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Report:
    title: str = ""
    markdown: str = ""
    metrics: Dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)
