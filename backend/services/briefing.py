"""简报生成服务"""
import json
from datetime import datetime, timedelta


def get_briefing_by_date(db, date: str):
    """获取指定日期的简报"""
    cursor = db.execute(
        "SELECT * FROM daily_briefings WHERE date = ?",
        (date,)
    )
    row = cursor.fetchone()
    
    if not row:
        # 如果没有生成过简报，尝试实时生成
        return generate_briefing_for_date(db, date)
    
    return {
        "id": row["id"],
        "date": row["date"],
        "items": json.loads(row["items"]),
        "summary": row["summary"],
        "generated_at": row["generated_at"]
    }


def get_latest_briefing(db):
    """获取最新简报"""
    cursor = db.execute(
        "SELECT * FROM daily_briefings ORDER BY date DESC LIMIT 1"
    )
    row = cursor.fetchone()
    
    if not row:
        # 生成今天的简报
        today = datetime.now().strftime("%Y-%m-%d")
        return generate_briefing_for_date(db, today)
    
    return {
        "id": row["id"],
        "date": row["date"],
        "items": json.loads(row["items"]),
        "summary": row["summary"],
        "generated_at": row["generated_at"]
    }


def generate_briefing_for_date(db, date: str, min_score: float = 6.0):
    """为指定日期生成简报"""
    # 获取最近 3 天的高相关性内容
    since = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=3)).strftime("%Y-%m-%d")
    
    cursor = db.execute("""
        SELECT * FROM content_items 
        WHERE date(created_at) >= ? AND relevance_score >= ?
        ORDER BY relevance_score DESC, created_at DESC
        LIMIT 20
    """, (since, min_score))
    
    rows = cursor.fetchall()
    if not rows:
        return None
    
    items = [{
        "id": row["id"],
        "title": row["title"],
        "source": row["source"],
        "source_type": row["source_type"],
        "url": row["url"],
        "summary": row["summary"],
        "category": json.loads(row["category"]) if row["category"] else [],
        "relevance_score": row["relevance_score"]
    } for row in rows]
    
    # 保存到数据库
    import uuid
    briefing_id = str(uuid.uuid4())
    db.execute("""
        INSERT OR REPLACE INTO daily_briefings (id, date, items, generated_at)
        VALUES (?, ?, ?, datetime('now'))
    """, (briefing_id, date, json.dumps([item["id"] for item in items])))
    db.commit()
    
    return {
        "id": briefing_id,
        "date": date,
        "items": items,
        "summary": None,
        "generated_at": datetime.now().isoformat()
    }
