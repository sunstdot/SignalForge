import Database from 'better-sqlite3';
import { join } from 'path';
import type { DailyBriefing, ContentItem } from '@tokenburner/shared';

// 优先使用环境变量，否则指向 collector 的数据库
const DB_PATH = process.env.DATABASE_PATH || join(process.cwd(), '..', 'collector', 'data', 'tokenburner.db');

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

  const result = parseBriefingRow(row, db);
  db.close();
  return result;
}

export function getBriefingByDate(date: string): DailyBriefing | null {
  const db = getDb();
  
  const row = db.prepare(`
    SELECT * FROM daily_briefings
    WHERE date = ?
  `).get(date) as any;

  if (!row) {
    db.close();
    return null;
  }

  const result = parseBriefingRow(row, db);
  db.close();
  return result;
}

export function getAvailableDates(): string[] {
  const db = getDb();
  
  const rows = db.prepare(`
    SELECT date FROM daily_briefings
    ORDER BY date DESC
  `).all() as Array<{ date: string }>;

  db.close();
  return rows.map(row => row.date);
}

export function getAdjacentDates(date: string): { prev: string | null; next: string | null } {
  const db = getDb();
  
  // Get previous date (older)
  const prevRow = db.prepare(`
    SELECT date FROM daily_briefings
    WHERE date < ?
    ORDER BY date DESC
    LIMIT 1
  `).get(date) as { date: string } | undefined;

  // Get next date (newer)
  const nextRow = db.prepare(`
    SELECT date FROM daily_briefings
    WHERE date > ?
    ORDER BY date ASC
    LIMIT 1
  `).get(date) as { date: string } | undefined;

  db.close();
  
  return {
    prev: prevRow?.date || null,
    next: nextRow?.date || null
  };
}

function parseBriefingRow(row: any, db: Database.Database): DailyBriefing {
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

  return {
    id: row.id,
    date: row.date,
    items,
    summary: row.summary ?? undefined,
    generatedAt: new Date(row.generated_at)
  };
}
