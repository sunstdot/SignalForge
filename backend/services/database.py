"""数据库服务"""
import sqlite3
import os
from pathlib import Path

# 数据库路径：使用 backend/data/tokenburner.db
if os.getenv("DB_PATH"):
    DB_PATH = os.getenv("DB_PATH")
else:
    BACKEND_DIR = Path(__file__).parent.parent
    DB_PATH = str(BACKEND_DIR / "data" / "tokenburner.db")

_db = None


def get_db():
    """获取数据库连接（单例模式）"""
    global _db
    if _db is None:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        _db = sqlite3.connect(DB_PATH, check_same_thread=False)
        _db.row_factory = sqlite3.Row
        _init_schema()
    return _db


def _init_schema():
    """初始化数据库表结构"""
    schema = """
    -- 内容条目表
    CREATE TABLE IF NOT EXISTS content_items (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        source_type TEXT NOT NULL,
        subscription_id TEXT,
        title TEXT NOT NULL,
        url TEXT NOT NULL,
        original_content TEXT,
        raw_text TEXT,
        relevance_score REAL DEFAULT 0,
        category TEXT DEFAULT '[]',
        summary TEXT,
        insights TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMP
    );

    -- 每日简报表
    CREATE TABLE IF NOT EXISTS daily_briefings (
        id TEXT PRIMARY KEY,
        date TEXT UNIQUE NOT NULL,
        items TEXT NOT NULL,
        summary TEXT,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- RSS 订阅表
    CREATE TABLE IF NOT EXISTS rss_subscriptions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        type TEXT NOT NULL,
        rsshub_route TEXT,
        category TEXT DEFAULT '[]',
        fetch_interval INTEGER DEFAULT 3600,
        last_fetched_at TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        fetch_status TEXT DEFAULT 'pending',
        last_error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 实验想法表
    CREATE TABLE IF NOT EXISTS experiment_ideas (
        id TEXT PRIMARY KEY,
        content_id TEXT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        difficulty TEXT CHECK (difficulty IN ('easy', 'medium', 'hard')),
        estimated_days INTEGER,
        tags TEXT DEFAULT '[]',
        status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'selected', 'in-progress', 'completed', 'archived')),
        priority REAL DEFAULT 0,
        briefing_date TEXT,
        source_type TEXT,
        source_title TEXT,
        source_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 实验表
    CREATE TABLE IF NOT EXISTS experiments (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'planning',
        idea_id TEXT,
        target_days INTEGER,
        tech_stack TEXT DEFAULT '[]',
        started_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 实验日志表
    CREATE TABLE IF NOT EXISTS experiment_logs (
        id TEXT PRIMARY KEY,
        experiment_id TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (experiment_id) REFERENCES experiments(id)
    );

    -- 索引
    CREATE INDEX IF NOT EXISTS idx_content_created ON content_items(created_at);
    CREATE INDEX IF NOT EXISTS idx_content_score ON content_items(relevance_score);
    CREATE INDEX IF NOT EXISTS idx_content_source ON content_items(source_type);
    CREATE INDEX IF NOT EXISTS idx_ideas_status ON experiment_ideas(status);
    """
    _db.executescript(schema)

    # 迁移：移除旧的 CHECK 约束（如果存在）
    # SQLite 不支持 ALTER COLUMN，需要重建表
    try:
        table_sql = _db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='content_items'"
        ).fetchone()
        if table_sql and "CHECK" in table_sql[0]:
            _db.executescript("""
                ALTER TABLE content_items RENAME TO _content_items_old;

                CREATE TABLE content_items (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    subscription_id TEXT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    original_content TEXT,
                    raw_text TEXT,
                    relevance_score REAL DEFAULT 0,
                    category TEXT DEFAULT '[]',
                    summary TEXT,
                    insights TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP
                );

                INSERT INTO content_items SELECT * FROM _content_items_old;
                DROP TABLE _content_items_old;

                CREATE INDEX IF NOT EXISTS idx_content_created ON content_items(created_at);
                CREATE INDEX IF NOT EXISTS idx_content_score ON content_items(relevance_score);
                CREATE INDEX IF NOT EXISTS idx_content_source ON content_items(source_type);
            """)
    except Exception:
        pass

    _db.commit()
