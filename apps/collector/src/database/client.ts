import Database from 'better-sqlite3';
import { readFileSync } from 'fs';
import { join } from 'path';
import type { ContentItem, RSSSubscription, DailyBriefing } from '@tokenburner/shared';

export class DatabaseClient {
  private db: Database.Database;

  constructor(dbPath: string) {
    this.db = new Database(dbPath);
    this.init();
  }

  private init(): void {
    const schema = readFileSync(
      join(__dirname, 'schema.sql'),
      'utf-8'
    );
    this.db.exec(schema);
  }

  insertContentItem(item: ContentItem): void {
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO content_items (
        id, source, source_type, subscription_id, title, url,
        original_content, raw_text, relevance_score, category,
        summary, insights, created_at, processed_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      item.id,
      item.source,
      item.sourceType,
      item.subscriptionId ?? null,
      item.title,
      item.url,
      item.originalContent,
      item.rawText ?? null,
      item.relevanceScore,
      JSON.stringify(item.category),
      item.summary ?? null,
      JSON.stringify(item.insights ?? []),
      item.createdAt.toISOString(),
      item.processedAt?.toISOString() ?? null
    );
  }

  getUnprocessedItems(limit: number = 100): ContentItem[] {
    const stmt = this.db.prepare(`
      SELECT * FROM content_items
      WHERE processed_at IS NULL
      ORDER BY created_at DESC
      LIMIT ?
    `);

    const rows = stmt.all(limit) as any[];
    return rows.map(this.rowToContentItem);
  }

  updateProcessedItem(id: string, updates: Partial<ContentItem>): void {
    const stmt = this.db.prepare(`
      UPDATE content_items
      SET relevance_score = ?,
          category = ?,
          summary = ?,
          insights = ?,
          processed_at = ?
      WHERE id = ?
    `);

    stmt.run(
      updates.relevanceScore ?? 0,
      JSON.stringify(updates.category ?? []),
      updates.summary ?? null,
      JSON.stringify(updates.insights ?? []),
      new Date().toISOString(),
      id
    );
  }

  getRecentItems(since: Date, minRelevance: number = 6): ContentItem[] {
    const stmt = this.db.prepare(`
      SELECT * FROM content_items
      WHERE created_at > ? AND relevance_score >= ?
      ORDER BY relevance_score DESC, created_at DESC
    `);

    const rows = stmt.all(since.toISOString(), minRelevance) as any[];
    return rows.map(this.rowToContentItem);
  }

  createBriefing(briefing: DailyBriefing): void {
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO daily_briefings (id, date, items, summary, generated_at)
      VALUES (?, ?, ?, ?, ?)
    `);

    stmt.run(
      briefing.id,
      briefing.date,
      JSON.stringify(briefing.items.map(i => i.id)),
      briefing.summary ?? null,
      briefing.generatedAt.toISOString()
    );
  }

  getActiveSubscriptions(): RSSSubscription[] {
    const stmt = this.db.prepare(`
      SELECT * FROM rss_subscriptions WHERE is_active = 1
    `);
    const rows = stmt.all() as any[];
    return rows.map(this.rowToSubscription);
  }

  private rowToContentItem(row: any): ContentItem {
    return {
      id: row.id,
      source: row.source,
      sourceType: row.source_type,
      subscriptionId: row.subscription_id ?? undefined,
      title: row.title,
      url: row.url,
      originalContent: row.original_content,
      rawText: row.raw_text ?? undefined,
      relevanceScore: row.relevance_score,
      category: JSON.parse(row.category),
      summary: row.summary ?? undefined,
      insights: row.insights ? JSON.parse(row.insights) : [],
      createdAt: new Date(row.created_at),
      processedAt: row.processed_at ? new Date(row.processed_at) : undefined
    };
  }

  private rowToSubscription(row: any): RSSSubscription {
    return {
      id: row.id,
      name: row.name,
      url: row.url,
      type: row.type,
      rsshubRoute: row.rsshub_route ?? undefined,
      category: JSON.parse(row.category),
      fetchInterval: row.fetch_interval,
      lastFetchedAt: row.last_fetched_at ? new Date(row.last_fetched_at) : undefined,
      isActive: Boolean(row.is_active),
      fetchStatus: row.fetch_status,
      lastError: row.last_error ?? undefined,
      createdAt: new Date(row.created_at),
      updatedAt: new Date(row.updated_at)
    };
  }

  close(): void {
    this.db.close();
  }
}
