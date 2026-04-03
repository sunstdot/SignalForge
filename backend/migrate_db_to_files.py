#!/usr/bin/env python3
"""一次性迁移：从 SQLite 数据库导出数据到 JSON 文件"""
import sqlite3
import json
import sys
from pathlib import Path
from collections import defaultdict

# 路径
BACKEND_DIR = Path(__file__).parent
DB_PATH = BACKEND_DIR / "data" / "tokenburner.db"
DATA_DIR = BACKEND_DIR.parent / "data"

CONTENT_DIR = DATA_DIR / "content"
BRIEFINGS_DIR = DATA_DIR / "briefings"
EXPERIMENTS_DIR = DATA_DIR / "experiments"

for d in [CONTENT_DIR, BRIEFINGS_DIR, EXPERIMENTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

if not DB_PATH.exists():
    print(f"DB not found at {DB_PATH}")
    sys.exit(1)

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

# ── 迁移 content_items ──────────────────────────────────────
print("Migrating content_items...")
rows = conn.execute("SELECT * FROM content_items ORDER BY created_at").fetchall()

by_date = defaultdict(list)
for row in rows:
    created = row["created_at"] or ""
    date = created[:10] if created else "unknown"
    item = {
        "id": row["id"],
        "source": row["source"],
        "source_type": row["source_type"],
        "subscription_id": row["subscription_id"],
        "title": row["title"],
        "url": row["url"],
        "original_content": row["original_content"] or "",
        "raw_text": row["raw_text"] or "",
        "relevance_score": row["relevance_score"] or 0,
        "category": json.loads(row["category"]) if row["category"] else [],
        "summary": row["summary"] or "",
        "insights": json.loads(row["insights"]) if row["insights"] else [],
        "created_at": row["created_at"] or "",
        "processed_at": row["processed_at"] or "",
    }
    by_date[date].append(item)

for date, items in by_date.items():
    out = CONTENT_DIR / f"{date}.json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {date}: {len(items)} items → {out}")

# ── 迁移 experiment_ideas ───────────────────────────────────
print("\nMigrating experiment_ideas...")
rows = conn.execute("SELECT * FROM experiment_ideas ORDER BY created_at").fetchall()
ideas = []
for row in rows:
    ideas.append({
        "id": row["id"],
        "content_id": row["content_id"] or "",
        "title": row["title"],
        "description": row["description"],
        "difficulty": row["difficulty"] or "medium",
        "estimated_days": row["estimated_days"] or 7,
        "tags": json.loads(row["tags"]) if row["tags"] else [],
        "status": row["status"] or "pending",
        "priority": row["priority"] or 0,
        "briefing_date": row["briefing_date"] or "",
        "source_type": row["source_type"] or "",
        "source_title": row["source_title"] or "",
        "source_url": row["source_url"] or "",
        "created_at": row["created_at"] or "",
    })

out = EXPERIMENTS_DIR / "ideas.json"
out.write_text(json.dumps(ideas, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"  {len(ideas)} ideas → {out}")

# ── 迁移 experiments ────────────────────────────────────────
print("\nMigrating experiments...")
rows = conn.execute("SELECT * FROM experiments ORDER BY created_at").fetchall()
exps = []
for row in rows:
    exps.append({
        "id": row["id"],
        "title": row["title"],
        "description": row["description"] or "",
        "status": row["status"] or "planning",
        "idea_id": row["idea_id"],
        "target_days": row["target_days"],
        "tech_stack": json.loads(row["tech_stack"]) if row["tech_stack"] else [],
        "started_at": row["started_at"],
        "created_at": row["created_at"] or "",
    })

out = EXPERIMENTS_DIR / "experiments.json"
out.write_text(json.dumps(exps, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"  {len(exps)} experiments → {out}")

# ── 迁移 experiment_logs ────────────────────────────────────
print("\nMigrating experiment_logs...")
rows = conn.execute("SELECT * FROM experiment_logs ORDER BY created_at").fetchall()
logs = []
for row in rows:
    logs.append({
        "id": row["id"],
        "experiment_id": row["experiment_id"],
        "content": row["content"],
        "created_at": row["created_at"] or "",
    })

out = EXPERIMENTS_DIR / "logs.json"
out.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"  {len(logs)} logs → {out}")

conn.close()

total_items = sum(len(v) for v in by_date.values())
print(f"\n✅ Migration complete!")
print(f"   Content items: {total_items} across {len(by_date)} dates")
print(f"   Ideas: {len(ideas)}, Experiments: {len(exps)}, Logs: {len(logs)}")
print(f"   Data directory: {DATA_DIR}")
