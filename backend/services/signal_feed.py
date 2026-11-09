"""今日信号：轻量分轨、多源限流与可解释筛选。

Phase 2 扩展：
- 默认少量精选（≤5 条），不凑数。
- 结合参考链接学习得到的价值特征，提高相似价值候选的关注度（不替代质量/证据判断）。
- 卡片补充「依据与边界」与初始五类标签（标签用于整理，不作入选门槛）。
"""
import re
from typing import Dict, List, Optional

from .company_blog import classify_company_blog, is_company_blog
from .signal_learning import learned_boost

EXECUTION = {"paper", "arxiv", "repo", "github", "model", "anthropic_blog", "blog"}
INSPIRATION = {"x", "reddit", "hn", "hackernews", "producthunt", "rss", "news",
               "newsletter", "smolai", "wechat", "investor"}
UPSTREAM = {"x", "reddit", "hn", "producthunt"}
GENERIC_FEEDS = {"rss", "news", "newsletter", "wechat", "investor", "smolai", "hackernews", "blog"}
AI_TERMS = re.compile(
    r"\b(?:ai|llm|gpt|claude|gemini|agent|agents|inference|prompt|"
    r"rag|mcp|openai|anthropic|deepmind|huggingface|neural|machine learning|"
    r"vibe coding|copilot)\b|\b(?:language|foundation|multimodal|generative|reasoning)\s+models?\b|"
    r"人工智能|大模型|智能体|模型|提示词|推理|开源",
    re.IGNORECASE,
)

# 初始五类标签（用于整理，不是白名单，也不是入选门槛）
TAG_RULES = [
    ("新能力新用法", re.compile(
        r"发布|推出|新增|新功能|支持|现在可以|上线|release|launch|new |支持了|可以用|能力", re.IGNORECASE)),
    ("实践方法", re.compile(
        r"方法|流程|步骤|工作流|实践|怎么做|教程|指南|tutorial|workflow|pipeline|how to|step", re.IGNORECASE)),
    ("失败与限制", re.compile(
        r"失败|限制|局限|踩坑|翻车|教训|缺点|不能|bug|failure|limitation|drawback", re.IGNORECASE)),
    ("对比与选择", re.compile(
        r"对比|比较|选择|权衡|替代|评测|benchmark|versus|vs\.?|取舍|哪个", re.IGNORECASE)),
    ("新问题与需求", re.compile(
        r"问题|需求|痛点|希望|求助|问一下|ask|question|need|想要|期待", re.IGNORECASE)),
]

# 学习到的价值特征命中时，放宽的互动门槛（仍保留证据底线，不放任纯噪音）。
DEFAULT_X_INTERACTIONS = 20
DEFAULT_SOCIAL_VOLUME = 30
LEARNED_X_INTERACTIONS = 5
LEARNED_SOCIAL_VOLUME = 10


def _track(item: Dict) -> Optional[str]:
    bucket = item.get("content_bucket")
    if not bucket and is_company_blog(item):
        bucket = classify_company_blog(item)
    if bucket == "corporate":
        return None
    if bucket in {"product_launch", "technical"} and item.get("source_type") != "anthropic_blog":
        source_text = f"{item.get('title', '')} {str(item.get('summary') or item.get('original_content') or '')[:500]}"
        if not AI_TERMS.search(source_text):
            return None
    if bucket == "product_launch":
        return "inspiration"
    if bucket == "technical":
        return "execution"
    source_type = item.get("source_type")
    if source_type in GENERIC_FEEDS:
        text = f"{item.get('title', '')} {str(item.get('summary') or item.get('original_content') or '')[:300]}"
        if not AI_TERMS.search(text):
            return None
    if source_type in EXECUTION:
        return "execution"
    if source_type in INSPIRATION:
        return "inspiration"
    return None


def _priority(item: Dict, learned: Optional[Dict] = None) -> float:
    """排序规则：现有评分 + 一手来源加成 + 学习到的价值特征加成。"""
    score = float(item.get("relevance_score") or 0)
    if item.get("source_type") in UPSTREAM or item.get("content_bucket") == "product_launch":
        score += 1
    if learned and learned.get("boost"):
        score += float(learned["boost"])
    return score


def _quick_read_context(item: Dict, cached: str) -> Optional[tuple[str, str, list[str], list[str]]]:
    """只使用有原始材料支撑的既有速读，不从标题臆测重要性。

    X 帖子本身较短：只要存在成文的速读材料，长度不作为硬门槛
    （简短的重要公告允许入选，质量由互动数据与速读内容判断）。
    """
    title = " ".join(str(item.get("title") or "").split()).casefold()
    original = " ".join(str(item.get("original_content") or "").split())
    summary = " ".join(str(item.get("summary") or "").split())
    if item.get("source_type") == "x":
        if not original and not summary and len(title) < 15:
            return None
    elif not any(len(text) >= 45 and text.casefold() != title for text in (original, summary)):
        return None
    if item.get("source_type") == "anthropic_blog" and original.casefold().startswith(
        "anthropic is an ai safety and research company"
    ) and summary == original:
        return None
    core = re.search(r"\*\*核心内容\*\*\s*[：:]\s*([^\n]+)", cached)
    insight = re.search(r"\*\*值得关注\*\*\s*[：:]\s*([^\n]+)", cached)
    if not core or not insight:
        return None
    takeaway, so_what = core.group(1).strip(), insight.group(1).strip()
    if min(len(takeaway), len(so_what)) < 15 or takeaway.casefold() == title or takeaway == so_what:
        return None
    detail = re.search(r"\*\*关键信息\*\*\s*[：:]\s*(.*?)(?=\n\s*\n|\n\*\*|\Z)", cached, re.DOTALL)
    facts = [fact.strip()[:100] for fact in re.findall(r"(?m)^\s*[-•]\s*(.+)$", detail.group(1) if detail else "")
             if len(fact.strip()) >= 5]
    return takeaway[:240], so_what[:200], facts[:2], facts[:4]


def _comments(item: Dict) -> List[str]:
    comments = (item.get("metadata") or {}).get("comments") or []
    return [str(c) for c in comments if isinstance(c, str) and c.strip()]


def _evidence_note(item: Dict) -> str:
    """依据与边界：来源角色 + 证据形态 + 缺失状态，不把残缺文本补写成事实。"""
    metadata = item.get("metadata") or {}
    source_type = item.get("source_type")
    notes = []
    if source_type == "reddit":
        notes.append("社区讨论" if _comments(item) else "社区主帖（回复上下文缺失）")
        if metadata.get("comments_fetched") is False:
            notes.append("回复抓取失败")
    elif source_type == "x":
        if metadata.get("quoted_url"):
            notes.append("作者自述 + 引用原帖（引用内容未随文核验）")
        elif metadata.get("post_type") == "quote":
            notes.append("作者引用（被引用上下文缺失）")
        else:
            notes.append("作者自述（公开主页核验）")
    elif source_type in {"hn", "hackernews"}:
        notes.append("社区热榜（转述/讨论，非独立验证）")
    elif item.get("content_bucket") == "product_launch":
        notes.append("官方能力发布")
    elif source_type in {"anthropic_blog", "blog"}:
        notes.append("官方材料")
    else:
        notes.append("一手来源" if source_type in UPSTREAM else "来源转述")

    engagement = str(metadata.get("engagement") or "").strip()
    if engagement:
        notes.append(f"互动数据：{engagement}")
    if source_type in UPSTREAM and not engagement and not _comments(item):
        notes.append("无互动/回复依据")
    return " · ".join(notes)


def _tag_item(text: str) -> List[str]:
    """基于文本的轻量五类标签；标签用于整理，不影响是否入选。"""
    if not text:
        return []
    tags = [label for label, pattern in TAG_RULES if pattern.search(text)]
    return tags


def _interaction_count(engagement: str) -> int:
    return sum(
        int(value.replace(",", "")) for value in re.findall(
            r"(\d[\d,]*)\s+(?:likes?|replies|reposts|retweets|quotes|upvotes|points|comments)\b",
            str(engagement or ""), re.IGNORECASE
        )
    )


def _passes_engagement(item: Dict, learned: Optional[Dict]) -> bool:
    """社区内容需要一定互动作为证据；学习命中的价值特征可适当放宽，但不取消。

    只有价值特征命中（matched_forms 非空）才放宽；单纯主题/品牌命中不放宽。
    """
    if item.get("source_type") not in UPSTREAM:
        return True
    metadata = item.get("metadata") or {}
    value_matched = bool(learned and learned.get("matched_forms"))
    if item.get("source_type") == "x":
        interactions = _interaction_count(metadata.get("engagement") or "")
        threshold = LEARNED_X_INTERACTIONS if value_matched else DEFAULT_X_INTERACTIONS
        return interactions >= threshold
    volume = metadata.get("volume")
    if not isinstance(volume, (int, float)):
        volume = _interaction_count(metadata.get("engagement") or "")
    threshold = LEARNED_SOCIAL_VOLUME if value_matched else DEFAULT_SOCIAL_VOLUME
    return float(volume) >= threshold


def _card(item: Dict, track: str, context: tuple[str, str, list[str], list[str]],
          learned: Optional[Dict] = None) -> Dict:
    takeaway, so_what, facts, details = context
    metadata = item.get("metadata") or {}
    evidence = str(metadata.get("engagement") or "").strip()
    tags = _tag_item(f"{item.get('title', '')} {takeaway} {so_what} {' '.join(facts)}")
    comments = _comments(item)
    if evidence:
        why = f"社区讨论 · {evidence}"
    elif item.get("content_bucket") == "product_launch":
        why = "官方能力发布"
    elif item.get("source_type") in UPSTREAM:
        why = "一手社区信号"
    else:
        why = "技术内容" if track == "execution" else "值得关注"

    card = {
        "id": item["id"], "title": item.get("title", ""), "url": item.get("url", ""),
        "source": item.get("source", ""), "source_type": item.get("source_type", ""),
        "published_at": item.get("published_at") or item.get("published_date") or item.get("date"),
        "relevance_score": item.get("relevance_score", 0),
        "track": track,
        # 新的展示字段（发现/为什么看/依据边界/标签）
        "finding": takeaway,
        "why_read": so_what,
        "evidence_note": _evidence_note(item),
        "tags": tags,
        "details": details,
        # 兼容旧字段
        "takeaway": takeaway, "facts": facts, "so_what": so_what,
        "evidence": evidence, "why": why,
    }
    if comments:
        card["comments"] = comments[:5]
    if metadata.get("quoted_url"):
        card["quoted_url"] = metadata["quoted_url"]
    if learned and learned.get("boost"):
        card["learned_from"] = learned.get("refs", [])
        card["learned_matched_forms"] = learned.get("matched_forms", {})
        card["learned_reason"] = "因你提供的参考信息而提高关注度（价值特征相似）"
    return card


def build_signal_feed(items: List[Dict], quick_reads: Dict | None = None, limit: int = 5,
                      preferences: Optional[Dict] = None) -> Dict:
    """最多返回 limit 条精选，分轨保底且每个作者/源最多两条；原始内容不变。

    preferences 为参考链接学习推导出的偏好快照；命中价值特征可提高关注度并
    适度放宽互动门槛，但内容质量与上下文判断仍保留。
    """
    feed: Dict = {"inspiration": [], "execution": [], "total": 0}
    if limit <= 0:
        return feed
    tracks = {"inspiration": [], "execution": []}
    contexts = {}
    learned_map: Dict[str, Dict] = {}
    for item in items:
        if item.get("dup_of") or not item.get("id"):
            continue
        track = _track(item)
        if not track:
            continue
        context = _quick_read_context(item, (quick_reads or {}).get(item["id"]) or "")
        if not context:
            continue
        learned = learned_boost(item, preferences) if preferences else None
        if item.get("source_type") in UPSTREAM and not _passes_engagement(item, learned):
            continue
        contexts[item["id"]] = context
        learned_map[item["id"]] = learned
        tracks[track].append(item)

    for group in tracks.values():
        group.sort(key=lambda item: (-_priority(item, learned_map.get(item["id"])), item.get("id", "")))

    selected: Dict[str, List[Dict]] = {"inspiration": [], "execution": []}
    counts: Dict[str, int] = {}
    seen = set()

    def take(track: str, candidates: List[Dict], max_items: int):
        for item in candidates:
            if len(selected[track]) >= max_items or len(seen) >= limit:
                break
            author = (item.get("metadata") or {}).get("author")
            source = f"{item.get('source_type')}:{author or item.get('source', '')}"
            if item["id"] in seen or counts.get(source, 0) >= 2:
                continue
            selected[track].append(item)
            seen.add(item["id"])
            counts[source] = counts.get(source, 0) + 1

    minimum = min(2, max(1, limit // 3))
    for track in ("inspiration", "execution"):
        take(track, tracks[track], minimum)
    remaining = sorted(
        ((track, item) for track, group in tracks.items() for item in group),
        key=lambda pair: (-_priority(pair[1], learned_map.get(pair[1]["id"])), pair[1].get("id", "")),
    )
    for track, item in remaining:
        if len(seen) >= limit:
            break
        take(track, [item], limit)

    for track, group in selected.items():
        feed[track] = [_card(item, track, contexts[item["id"]], learned_map.get(item["id"])) for item in group]
    feed["total"] = len(seen)
    return feed
