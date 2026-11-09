"""论断聚类：把"在说同一件事"的论断归到一簇，给核验阶段定额。

为什么需要：抽取阶段每条论断的 predicate 都是模型自由写的，
实测 2527 条论断里出现 2000 多个不同的 predicate 写法
（"担任 CEO" / "担任首席执行官" / "says she is CEO"），
直接按字符串精确匹配几乎没有归并效果。

分两步：
1. 归一化：统一大小写、全半角、常见同义词、去掉修饰性副词和数量尾巴。
2. 归并：同 subject 下按归一化 predicate 分桶，桶内再看 text 是否真的在讲同一件事。

核验阶段只处理"跨来源"的桶——单来源的桶没有可核验的对象，
按 single 处理即可，不必花模型调用。
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, List

# 中英文同义谓词归一。key 是归一化后的规范形，value 是会被映射到它的模式。
# 原则：只合并语义等价的表述，不合并"相关但不同"的事（如"担任 CEO"与"是联合创始人"）。
PREDICATE_SYNONYMS = {
    "担任CEO": ("担任ceo", "担任首席执行官", "是ceo", "出任ceo", "任ceo", "ceo是", "says ceo", "is the ceo"),
    "担任总裁": ("担任总裁", "是总裁", "出任总裁", "president"),
    "担任联合创始人": ("联合创始人", "co-founder", "cofounder"),
    "总部位于": ("总部位于", "总部设在", " headquartered", "based in"),
    "成立于": ("成立于", "创立于", "创建于", "founded in", "was founded"),
    "注册为公益公司": (
        "注册为公益公司", "是公益公司", "公益公司", "public benefit corporation",
        "pbc", "benefit corporation",
    ),
    "员工规模": ("员工数", "员工规模", "人数", "headcount", "employees", "employee count"),
    "融资": ("融资", "估值", "raise", "funding", "valuation"),
    "离职": ("离职", "离开", "departed", "left the company"),
    "加入": ("加入", "入职", "joined"),
}

# 归一化时剔除的修饰词：这些词会让语义相同的 predicate 分到不同桶。
_NOISE_PATTERNS = (
    r"\bapproximately\b", r"\babout\b", r"\baround\b", r"\broughly\b",
    r"大约", r"约", r"左右", r"已经", r"目前", r"当前",
)

# 谓词里带具体数值时，归一到同一个语义桶（数值差异交由核验阶段判冲突）。
_NUMBER_RE = re.compile(r"\d[\d,\.]*\s*(?:%|人|名|亿|万|billion|million|thousand)?", re.IGNORECASE)


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", value).strip().lower()
    text = re.sub(r"[‘’“”]", '"', text)
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_subject(value: str) -> str:
    text = _normalize_text(value)
    # 同一实体的不同写法：去掉冠词和尾部限定语
    text = re.sub(r"^(the|a|an)\s+", "", text)
    text = re.sub(r"\s*\(.*?\)\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_predicate(value: str) -> str:
    text = _normalize_text(value)
    for pattern in _NOISE_PATTERNS:
        text = re.sub(pattern, "", text)
    # 数值不参与分桶键：同一属性的不同数值恰恰是要被核验出来的冲突
    text = _NUMBER_RE.sub(" ", text)
    text = re.sub(r"[\s\-_/]+", " ", text).strip()

    # 同义匹配时忽略空格：中英混写的谓词空格位置不固定
    # （"担任 CEO" / "担任CEO" / " headquartered in"），
    # 带空格直接比较会让同义模式漏配。
    compact = text.replace(" ", "")
    for canonical, patterns in PREDICATE_SYNONYMS.items():
        if any(p.replace(" ", "") in compact for p in patterns):
            return canonical
    return text


def cluster_claims(claims: Iterable[dict]) -> List[dict]:
    """把论断聚成簇。

    返回每个簇：{key, claim_ids, source_ids, subjects, predicates}
    只按 subject + 归一化 predicate 分桶，不做语义判断——
    语义层面的"是否同一事实"留给核验阶段的模型判断。
    """
    buckets: Dict[tuple, dict] = {}
    for claim in claims:
        subject = normalize_subject(claim.get("subject", ""))
        predicate = normalize_predicate(claim.get("predicate", ""))
        # 缺 subject/predicate 的论断无法归簇，各自独立成簇
        key = (subject, predicate) if subject or predicate else (f"__solo__{claim['id']}", "")
        bucket = buckets.setdefault(key, {
            "key": key,
            "claim_ids": [],
            "source_ids": set(),
            "subjects": set(),
            "predicates": set(),
        })
        bucket["claim_ids"].append(claim["id"])
        if claim.get("source_id"):
            bucket["source_ids"].add(claim["source_id"])
        if subject:
            bucket["subjects"].add(subject)
        if predicate:
            bucket["predicates"].add(predicate)

    clusters = []
    for bucket in buckets.values():
        clusters.append({
            "key": list(bucket["key"]),
            "claim_ids": sorted(bucket["claim_ids"]),
            "source_ids": sorted(bucket["source_ids"]),
            "subjects": sorted(bucket["subjects"]),
            "predicates": sorted(bucket["predicates"]),
            # 跨来源才值得送模型核验；单来源没有可对照的第二方
            "cross_source": len(bucket["source_ids"]) >= 2,
        })
    clusters.sort(key=lambda c: (not c["cross_source"], -len(c["claim_ids"])))
    return clusters


def select_for_verification(clusters: List[dict], max_clusters: int = 40) -> List[dict]:
    """挑出要送模型核验的簇。

    优先跨来源的簇（多来源说同一件事，才有"是否一致"可判），
    同源多条的簇次之，单条单源的直接跳过。
    """
    cross = [c for c in clusters if c["cross_source"]]
    multi = [c for c in clusters if not c["cross_source"] and len(c["claim_ids"]) > 1]
    ordered = sorted(cross, key=lambda c: -len(c["claim_ids"])) + \
              sorted(multi, key=lambda c: -len(c["claim_ids"]))
    return ordered[:max_clusters]
