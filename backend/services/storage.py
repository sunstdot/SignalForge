"""文件式存储服务 - 替代 SQLite 数据库，数据存储在 /data 目录"""
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 数据目录：项目根目录下的 /data
DATA_DIR = Path(__file__).parent.parent.parent / "data"
CONTENT_DIR = DATA_DIR / "content"
BRIEFINGS_DIR = DATA_DIR / "briefings"
EXPERIMENTS_DIR = DATA_DIR / "experiments"


def _ensure_dirs():
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)


_ensure_dirs()


# ───────────────────────── 内容条目 ─────────────────────────

def _load_content_file(date: str) -> List[Dict]:
    path = CONTENT_DIR / f"{date}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save_content_file(date: str, items: List[Dict]):
    path = CONTENT_DIR / f"{date}.json"
    path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )


def store_content_items(items: List[Dict]) -> int:
    """批量存储内容条目，按日期写入文件，去重"""
    # 先分组
    by_date: Dict[str, List[Dict]] = {}
    for item in items:
        created = item.get("created_at", datetime.now())
        if isinstance(created, datetime):
            date = created.strftime("%Y-%m-%d")
        elif isinstance(created, str):
            date = created[:10]
        else:
            date = datetime.now().strftime("%Y-%m-%d")

        # 序列化 datetime
        item = dict(item)
        if isinstance(item.get("created_at"), datetime):
            item["created_at"] = item["created_at"].isoformat()

        by_date.setdefault(date, []).append(item)

    stored = 0
    for date, new_items in by_date.items():
        existing = _load_content_file(date)
        existing_ids = {i["id"] for i in existing}
        added = [i for i in new_items if i["id"] not in existing_ids]
        if added:
            _save_content_file(date, existing + added)
            stored += len(added)

    return stored


def get_content_items(
    date: Optional[str] = None,
    source_type: Optional[str] = None,
    min_score: float = 0,
    limit: int = 200,
) -> List[Dict]:
    """获取内容条目列表"""
    if date:
        items = _load_content_file(date)
    else:
        items = []
        for path in sorted(CONTENT_DIR.glob("*.json"), reverse=True):
            items.extend(json.loads(path.read_text(encoding="utf-8")))

    if source_type:
        items = [i for i in items if i.get("source_type") == source_type]
    items = [i for i in items if i.get("relevance_score", 0) >= min_score]
    items.sort(key=lambda x: (-x.get("relevance_score", 0), x.get("created_at", "")), reverse=False)
    return items[:limit]


def get_content_item_by_id(item_id: str) -> Optional[Dict]:
    for path in sorted(CONTENT_DIR.glob("*.json"), reverse=True):
        for item in json.loads(path.read_text(encoding="utf-8")):
            if item["id"] == item_id:
                return item
    return None


NON_DAILY_ORIGINS = {"last30days", "venture-product-radar"}


def _has_daily_content(date: str) -> bool:
    """该日期是否有真正的 daily 采集内容。

    辅助导入数据不应作为"今日 AI 情报"档期出现。只要当天存在任意一条普通日更来源的
    内容，就算一次真实采集。
    """
    items = _load_content_file(date)
    return any(
        (item.get("metadata") or {}).get("origin") not in NON_DAILY_ORIGINS
        for item in items
    )


def get_all_dates() -> List[str]:
    """返回真正采集过 daily 内容的日期列表（倒序）。"""
    dates = sorted([p.stem for p in CONTENT_DIR.glob("*.json")], reverse=True)
    return [d for d in dates if _has_daily_content(d)]


def get_content_stats() -> Dict:
    today = datetime.now().strftime("%Y-%m-%d")
    all_items = get_content_items(limit=10000)
    today_items = _load_content_file(today)
    by_source: Dict[str, int] = {}
    for item in all_items:
        st = item.get("source_type", "unknown")
        by_source[st] = by_source.get(st, 0) + 1
    return {
        "total": len(all_items),
        "today": len(today_items),
        "unprocessed": 0,
        "by_source": by_source,
    }


# ───────────────────────── 简报 ─────────────────────────

def get_briefing_file(date: str) -> Optional[Dict]:
    path = BRIEFINGS_DIR / f"{date}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_briefing_file(briefing: Dict):
    path = BRIEFINGS_DIR / f"{briefing['date']}.json"
    path.write_text(
        json.dumps(briefing, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )


def get_latest_briefing_date() -> Optional[str]:
    dates = get_all_dates()
    return dates[0] if dates else None


# ───────────────────────── 机会雷达缓存 ─────────────────────────

OPPORTUNITIES_DIR = DATA_DIR / "opportunities"
OPPORTUNITIES_DIR.mkdir(parents=True, exist_ok=True)


def load_opportunities(date: str) -> Optional[Dict]:
    path = OPPORTUNITIES_DIR / f"{date}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_opportunities(date: str, data: Dict):
    path = OPPORTUNITIES_DIR / f"{date}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ───────────────────────── 速读缓存 ─────────────────────────

QUICK_READS_DIR = DATA_DIR / "quick_reads"
QUICK_READS_DIR.mkdir(parents=True, exist_ok=True)


def load_quick_reads(date: str) -> Dict:
    """加载某日期所有速读缓存 {item_id: summary}"""
    path = QUICK_READS_DIR / f"{date}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_quick_read(date: str, item_id: str, summary: str):
    """保存单条速读缓存"""
    data = load_quick_reads(date)
    data[item_id] = summary
    path = QUICK_READS_DIR / f"{date}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ───────────────────────── 分类摘要缓存 ─────────────────────────

DIGESTS_DIR = DATA_DIR / "digests"
DIGESTS_DIR.mkdir(parents=True, exist_ok=True)


def load_category_digest(date: str) -> Optional[Dict]:
    path = DIGESTS_DIR / f"{date}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_category_digest(date: str, digest: Dict):
    path = DIGESTS_DIR / f"{date}.json"
    path.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")


# ───────────────────────── 研发效能洞察缓存 ─────────────────────────

RDEV_DIR = DATA_DIR / "rdev_opportunities"
RDEV_DIR.mkdir(parents=True, exist_ok=True)


def load_rdev_opportunities(date: str) -> Optional[Dict]:
    path = RDEV_DIR / f"{date}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_rdev_opportunities(date: str, data: Dict):
    path = RDEV_DIR / f"{date}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _cache_has_items(path: Path, key: str) -> bool:
    if not path.exists():
        return False
    values = json.loads(path.read_text(encoding="utf-8")).get(key)
    return isinstance(values, list) and len(values) > 0


def get_opportunity_dates() -> List[str]:
    """返回至少有一类机会缓存数据的日期列表（倒序）。"""
    dates = {path.stem for path in OPPORTUNITIES_DIR.glob("*.json")}
    dates.update(path.stem for path in RDEV_DIR.glob("*.json"))
    return [
        date for date in sorted(dates, reverse=True)
        if _cache_has_items(OPPORTUNITIES_DIR / f"{date}.json", "opportunities")
        or _cache_has_items(RDEV_DIR / f"{date}.json", "solutions")
    ]


# ───────────────────────── 实验想法 ─────────────────────────

def _load_ideas() -> List[Dict]:
    path = EXPERIMENTS_DIR / "ideas.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save_ideas(ideas: List[Dict]):
    path = EXPERIMENTS_DIR / "ideas.json"
    path.write_text(json.dumps(ideas, ensure_ascii=False, indent=2), encoding="utf-8")


def get_ideas(status: Optional[str] = None) -> List[Dict]:
    ideas = _load_ideas()
    if status:
        ideas = [i for i in ideas if i.get("status") == status]
    return sorted(ideas, key=lambda x: x.get("created_at", ""), reverse=True)


def get_idea_by_id(idea_id: str) -> Optional[Dict]:
    for idea in _load_ideas():
        if idea["id"] == idea_id:
            return idea
    return None


def create_idea(data: Dict) -> Dict:
    ideas = _load_ideas()
    idea = {
        "id": str(uuid.uuid4()),
        "content_id": data.get("content_id", ""),
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "difficulty": data.get("difficulty", "medium"),
        "estimated_days": data.get("estimated_days", 7),
        "tags": data.get("tags", []),
        "status": data.get("status", "pending"),
        "priority": data.get("priority", 0),
        "briefing_date": data.get("briefing_date", ""),
        "source_type": data.get("source_type", ""),
        "source_title": data.get("source_title", ""),
        "source_url": data.get("source_url", ""),
        # 产品思路相关字段
        "inspiration": data.get("inspiration", ""),
        "product_concept": data.get("product_concept", {}),
        "source_context": data.get("source_context", ""),
        "created_at": datetime.now().isoformat(),
    }
    ideas.append(idea)
    _save_ideas(ideas)
    return idea



def update_idea_status_by_id(idea_id: str, status: str) -> Optional[Dict]:
    ideas = _load_ideas()
    for idea in ideas:
        if idea["id"] == idea_id:
            idea["status"] = status
            _save_ideas(ideas)
            return idea
    return None


def delete_idea_by_id(idea_id: str) -> bool:
    ideas = _load_ideas()
    new_ideas = [i for i in ideas if i["id"] != idea_id]
    if len(new_ideas) == len(ideas):
        return False
    _save_ideas(new_ideas)
    return True


def get_ideas_stats() -> Dict:
    ideas = _load_ideas()
    stats: Dict[str, int] = {}
    for idea in ideas:
        s = idea.get("status", "pending")
        stats[s] = stats.get(s, 0) + 1
    return {
        "total": len(ideas),
        "pending": stats.get("pending", 0),
        "selected": stats.get("selected", 0),
        "in-progress": stats.get("in-progress", 0),
        "completed": stats.get("completed", 0),
        "archived": stats.get("archived", 0),
    }


# ───────────────────────── 实验 ─────────────────────────

def _load_experiments() -> List[Dict]:
    path = EXPERIMENTS_DIR / "experiments.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save_experiments(experiments: List[Dict]):
    path = EXPERIMENTS_DIR / "experiments.json"
    path.write_text(json.dumps(experiments, ensure_ascii=False, indent=2), encoding="utf-8")


def get_experiments(status: Optional[str] = None) -> List[Dict]:
    exps = _load_experiments()
    if status:
        exps = [e for e in exps if e.get("status") == status]
    return sorted(exps, key=lambda x: x.get("created_at", ""), reverse=True)


def get_experiment_by_id(exp_id: str) -> Optional[Dict]:
    for exp in _load_experiments():
        if exp["id"] == exp_id:
            return exp
    return None


def create_experiment(data: Dict) -> Dict:
    exps = _load_experiments()
    exp = {
        "id": str(uuid.uuid4()),
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "status": data.get("status", "planning"),
        "idea_id": data.get("idea_id"),
        "target_days": data.get("target_days"),
        "tech_stack": data.get("tech_stack", []),
        "started_at": data.get("started_at"),
        "created_at": datetime.now().isoformat(),
    }
    exps.append(exp)
    _save_experiments(exps)
    return exp


def update_experiment_by_id(exp_id: str, data: Dict) -> Optional[Dict]:
    exps = _load_experiments()
    for exp in exps:
        if exp["id"] == exp_id:
            for key in ("title", "description", "status", "target_days", "product_concept"):
                if key in data:
                    exp[key] = data[key]
            _save_experiments(exps)
            return exp
    return None


def delete_experiment_by_id(exp_id: str) -> bool:
    exps = _load_experiments()
    new_exps = [e for e in exps if e["id"] != exp_id]
    if len(new_exps) == len(exps):
        return False
    _save_experiments(new_exps)
    return True


# ───────────────────────── 实验日志 ─────────────────────────

def _load_logs() -> List[Dict]:
    path = EXPERIMENTS_DIR / "logs.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save_logs(logs: List[Dict]):
    path = EXPERIMENTS_DIR / "logs.json"
    path.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")


def get_logs_for_experiment(exp_id: str) -> List[Dict]:
    logs = [l for l in _load_logs() if l.get("experiment_id") == exp_id]
    return sorted(logs, key=lambda x: x.get("created_at", ""), reverse=True)


def add_log(exp_id: str, content: str) -> Dict:
    logs = _load_logs()
    log = {
        "id": str(uuid.uuid4()),
        "experiment_id": exp_id,
        "content": content,
        "created_at": datetime.now().isoformat(),
    }
    logs.append(log)
    _save_logs(logs)
    return log


# ───────────────────────── 手动情报 ─────────────────────────

MANUAL_INTEL_DIR = DATA_DIR / "manual_intel"
MANUAL_INTEL_DIR.mkdir(parents=True, exist_ok=True)


def _load_manual_intel() -> List[Dict]:
    f = MANUAL_INTEL_DIR / "items.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return []


def _save_manual_intel(items: List[Dict]):
    f = MANUAL_INTEL_DIR / "items.json"
    f.write_text(
        json.dumps(items, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def get_manual_intel_items(source_platform: Optional[str] = None) -> List[Dict]:
    items = _load_manual_intel()
    if source_platform:
        items = [i for i in items if i.get("source_platform") == source_platform]
    return sorted(items, key=lambda x: x.get("added_at", ""), reverse=True)


def get_manual_intel_item_by_id(item_id: str) -> Optional[Dict]:
    for item in _load_manual_intel():
        if item["id"] == item_id:
            return item
    return None


def create_manual_intel_item(data: Dict) -> Dict:
    items = _load_manual_intel()
    item = {
        "id": str(uuid.uuid4()),
        "url": data.get("url", ""),
        "title": data.get("title", ""),
        "source_platform": data.get("source_platform", "other"),
        "user_note": data.get("user_note", ""),
        "added_at": datetime.now().isoformat(),
        "content_snippet": data.get("content_snippet", ""),
        "quick_read": "",
        "business_opps": [],
        "rdev_opps": [],
    }
    items.append(item)
    _save_manual_intel(items)
    return item


_UPDATABLE_FIELDS = {"quick_read", "business_opps", "rdev_opps", "title", "user_note", "content_snippet", "source_platform"}

def update_manual_intel_item(item_id: str, updates: Dict) -> Optional[Dict]:
    items = _load_manual_intel()
    for item in items:
        if item["id"] == item_id:
            for key, value in updates.items():
                if key in _UPDATABLE_FIELDS:
                    item[key] = value
            _save_manual_intel(items)
            return item
    return None


def delete_manual_intel_item(item_id: str) -> bool:
    items = _load_manual_intel()
    new_items = [i for i in items if i["id"] != item_id]
    if len(new_items) == len(items):
        return False
    _save_manual_intel(new_items)
    return True


# ───────────────────────── Wiki ─────────────────────────

WIKI_DIR = DATA_DIR / "wiki"
WIKI_DIR.mkdir(parents=True, exist_ok=True)


def _load_wiki_concepts() -> List[Dict]:
    f = WIKI_DIR / "concepts.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def _save_wiki_concepts(concepts: List[Dict]):
    (WIKI_DIR / "concepts.json").write_text(
        json.dumps(concepts, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def _load_wiki_article_nodes() -> List[Dict]:
    f = WIKI_DIR / "article_nodes.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def _save_wiki_article_nodes(nodes: List[Dict]):
    (WIKI_DIR / "article_nodes.json").write_text(
        json.dumps(nodes, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def get_wiki_concepts() -> List[Dict]:
    return _load_wiki_concepts()


def get_wiki_article_nodes() -> List[Dict]:
    return _load_wiki_article_nodes()


def get_wiki_article_node(item_id: str) -> Optional[Dict]:
    for node in _load_wiki_article_nodes():
        if node["item_id"] == item_id:
            return node
    return None


def upsert_wiki_concept(name: str, slug: str, description: str, article_id: str) -> Dict:
    concepts = _load_wiki_concepts()
    now = datetime.now().isoformat()
    for c in concepts:
        if c["slug"] == slug:
            if article_id not in c["article_ids"]:
                c["article_ids"].append(article_id)
            c["description"] = description
            c["updated_at"] = now
            _save_wiki_concepts(concepts)
            return c
    new_concept = {
        "name": name,
        "slug": slug,
        "description": description,
        "article_ids": [article_id],
        "created_at": now,
        "updated_at": now,
    }
    concepts.append(new_concept)
    _save_wiki_concepts(concepts)
    return new_concept


def delete_wiki_concept(slug: str) -> bool:
    concepts = _load_wiki_concepts()
    new_concepts = [c for c in concepts if c["slug"] != slug]
    if len(new_concepts) == len(concepts):
        return False
    _save_wiki_concepts(new_concepts)
    return True


def upsert_wiki_article_node(
    item_id: str, slug: str, concepts: List[str], related_articles: List[Dict]
) -> Dict:
    nodes = _load_wiki_article_nodes()
    now = datetime.now().isoformat()
    for node in nodes:
        if node["item_id"] == item_id:
            node.update({
                "slug": slug,
                "concepts": concepts,
                "related_articles": related_articles,
                "wiki_synced_at": now,
            })
            _save_wiki_article_nodes(nodes)
            return node
    new_node = {
        "item_id": item_id,
        "slug": slug,
        "concepts": concepts,
        "related_articles": related_articles,
        "wiki_synced_at": now,
    }
    nodes.append(new_node)
    _save_wiki_article_nodes(nodes)
    return new_node
