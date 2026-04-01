import Database from 'better-sqlite3';
import { join } from 'path';
import type { DailyBriefing, ContentItem } from '@tokenburner/shared';

const DB_PATH = process.env.DATABASE_PATH || join(process.cwd(), '..', '..', 'data', 'tokenburner.db');

export function getDb() {
  return new Database(DB_PATH);
}

export function getLatestBriefing(): DailyBriefing | null {
  const db = getDb();
  
  const row = db.prepare(`
    SELECT * FROM daily_briefings
    ORDER BY date DESC
    LIMIT 1
  `).get() as any;

  if (!row) {
    db.close();
    return null;
  }

  const itemIds = JSON.parse(row.items) as string[];
  const items: ContentItem[] = [];

  for (const id of itemIds) {
    const itemRow = db.prepare('SELECT * FROM content_items WHERE id = ?').get(id) as any;
    if (itemRow) {
      items.push({
        id: itemRow.id,
        source: itemRow.source,
        sourceType: itemRow.source_type,
        title: itemRow.title,
        url: itemRow.url,
        originalContent: itemRow.original_content,
        summary: itemRow.summary ?? undefined,
        insights: itemRow.insights ? JSON.parse(itemRow.insights) : [],
        relevanceScore: itemRow.relevance_score,
        category: JSON.parse(itemRow.category),
        createdAt: new Date(itemRow.created_at)
      });
    }
  }

  db.close();

  return {
    id: row.id,
    date: row.date,
    items,
    summary: row.summary ?? undefined,
    generatedAt: new Date(row.generated_at)
  };
}
