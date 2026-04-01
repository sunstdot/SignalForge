CREATE TABLE IF NOT EXISTS content_items (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('paper', 'repo', 'news', 'tweet', 'podcast', 'rss')),
  subscription_id TEXT,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  original_content TEXT NOT NULL,
  raw_text TEXT,
  relevance_score REAL DEFAULT 0,
  category TEXT DEFAULT '[]',
  summary TEXT,
  insights TEXT DEFAULT '[]',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  processed_at DATETIME,
  UNIQUE(url)
);

CREATE TABLE IF NOT EXISTS rss_subscriptions (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('direct', 'rsshub')),
  rsshub_route TEXT,
  category TEXT DEFAULT '[]',
  fetch_interval INTEGER DEFAULT 3600,
  last_fetched_at DATETIME,
  is_active BOOLEAN DEFAULT 1,
  fetch_status TEXT DEFAULT 'pending' CHECK (fetch_status IN ('ok', 'error', 'pending')),
  last_error TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_briefings (
  id TEXT PRIMARY KEY,
  date TEXT NOT NULL UNIQUE,
  items TEXT NOT NULL,
  summary TEXT,
  generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiment_ideas (
  id TEXT PRIMARY KEY,
  content_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  difficulty TEXT CHECK (difficulty IN ('easy', 'medium', 'hard')),
  estimated_days INTEGER,
  tags TEXT DEFAULT '[]',
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'selected', 'in-progress', 'completed', 'archived')),
  priority REAL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (content_id) REFERENCES content_items(id)
);

CREATE INDEX IF NOT EXISTS idx_content_source_type ON content_items(source_type);
CREATE INDEX IF NOT EXISTS idx_content_created ON content_items(created_at);
CREATE INDEX IF NOT EXISTS idx_content_relevance ON content_items(relevance_score);
CREATE INDEX IF NOT EXISTS idx_content_processed ON content_items(processed_at);
