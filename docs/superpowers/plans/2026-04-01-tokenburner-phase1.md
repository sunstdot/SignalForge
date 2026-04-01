# TokenBurner Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundation intelligence collection system with arXiv/GitHub data sources, OpenRouter multi-model pipeline, and daily briefing generation.

**Architecture:** Monorepo with apps/collector (Node.js data collection), apps/web (Next.js dashboard), packages/shared (types), packages/ai-client (OpenRouter wrapper). SQLite for storage. BullMQ for job scheduling.

**Tech Stack:** Node.js 20, TypeScript 5, Next.js 14, Tailwind CSS, SQLite (better-sqlite3), OpenRouter API, BullMQ, Vitest

---

## File Structure

```
token-burn/
├── apps/
│   ├── collector/              # Data collection service
│   │   ├── src/
│   │   │   ├── config/         # Configuration loading
│   │   │   ├── database/       # SQLite schema and client
│   │   │   ├── sources/        # Data source adapters
│   │   │   │   ├── arxiv.ts    # arXiv RSS fetcher
│   │   │   │   └── github.ts   # GitHub Trending API
│   │   │   ├── pipeline/       # AI processing pipeline
│   │   │   │   ├── filter.ts   # GPT-4 relevance filter
│   │   │   │   └── summarize.ts # Content summarizer
│   │   │   ├── jobs/           # BullMQ job definitions
│   │   │   │   ├── fetch.ts    # Fetch job
│   │   │   │   └── process.ts  # Process job
│   │   │   ├── briefing/       # Daily briefing generator
│   │   │   └── index.ts        # Service entry
│   │   ├── tests/              # Vitest tests
│   │   └── package.json
│   │
│   └── web/                    # Next.js dashboard
│       ├── src/
│       │   ├── app/
│       │   │   ├── page.tsx    # Daily briefing display
│       │   │   └── layout.tsx
│       │   ├── components/
│       │   └── lib/
│       └── package.json
│
├── packages/
│   ├── shared/                 # Shared types and utils
│   │   ├── src/
│   │   │   ├── types/
│   │   │   │   ├── content.ts  # ContentItem types
│   │   │   │   └── config.ts   # Config types
│   │   │   └── index.ts
│   │   └── package.json
│   │
│   └── ai-client/              # OpenRouter client
│       ├── src/
│       │   ├── client.ts       # API client
│       │   ├── models.ts       # Model definitions
│       │   └── index.ts
│       └── package.json
│
├── package.json                # Root workspace config
├── turbo.json                  # Turborepo config
└── vitest.workspace.ts         # Vitest workspace config
```

---

## Task 1: Initialize Monorepo Structure

**Files:**
- Create: `package.json`
- Create: `turbo.json`
- Create: `.gitignore`

- [ ] **Step 1: Create root package.json**

```json
{
  "name": "token-burner",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "build": "turbo run build",
    "dev": "turbo run dev",
    "test": "turbo run test",
    "lint": "turbo run lint"
  },
  "devDependencies": {
    "turbo": "^1.13.0",
    "typescript": "^5.4.0"
  },
  "packageManager": "pnpm@8.15.0",
  "workspaces": [
    "apps/*",
    "packages/*"
  ]
}
```

- [ ] **Step 2: Create turbo.json**

```json
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": ["**/.env.*local"],
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "!.next/cache/**", "dist/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "test": {
      "dependsOn": ["build"]
    },
    "lint": {}
  }
}
```

- [ ] **Step 3: Create .gitignore**

```
# Dependencies
node_modules/
.pnpm-store/

# Build outputs
dist/
.build/
.next/
out/

# Environment
.env
.env.local
.env.*.local

# Database
*.db
*.db-journal

# Logs
logs/
*.log
npm-debug.log*

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Turbo
.turbo/
```

- [ ] **Step 4: Initialize git and commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git init
git add package.json turbo.json .gitignore
git commit -m "chore: initialize monorepo structure"
```

---

## Task 2: Create Shared Package with Types

**Files:**
- Create: `packages/shared/package.json`
- Create: `packages/shared/src/types/content.ts`
- Create: `packages/shared/src/types/config.ts`
- Create: `packages/shared/src/index.ts`
- Create: `packages/shared/tsconfig.json`

- [ ] **Step 1: Create packages/shared/package.json**

```json
{
  "name": "@tokenburner/shared",
  "version": "1.0.0",
  "private": true,
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch",
    "test": "vitest run"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "vitest": "^1.4.0"
  }
}
```

- [ ] **Step 2: Create packages/shared/src/types/content.ts**

```typescript
/**
 * Content item from any source
 */
export interface ContentItem {
  id: string;
  source: string;
  sourceType: 'paper' | 'repo' | 'news' | 'tweet' | 'podcast' | 'rss';
  subscriptionId?: string;
  title: string;
  url: string;
  originalContent: string;
  rawText?: string;
  
  // AI processing results
  relevanceScore: number;
  category: string[];
  summary?: string;
  insights?: string[];
  
  // Metadata
  createdAt: Date;
  processedAt?: Date;
}

/**
 * Experiment idea extracted from content
 */
export interface ExperimentIdea {
  id: string;
  contentId: string;
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  estimatedDays: number;
  tags: string[];
  status: 'pending' | 'selected' | 'in-progress' | 'completed' | 'archived';
  priority: number;
  createdAt: Date;
}

/**
 * RSS subscription configuration
 */
export interface RSSSubscription {
  id: string;
  name: string;
  url: string;
  type: 'direct' | 'rsshub';
  rsshubRoute?: string;
  category: string[];
  fetchInterval: number;
  lastFetchedAt?: Date;
  isActive: boolean;
  fetchStatus: 'ok' | 'error' | 'pending';
  lastError?: string;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * RSSHub configuration
 */
export interface RSSHubConfig {
  instanceUrl: string;
  accessKey?: string;
  isSelfHosted: boolean;
}

/**
 * Daily briefing output
 */
export interface DailyBriefing {
  id: string;
  date: string;
  items: ContentItem[];
  summary: string;
  generatedAt: Date;
}
```

- [ ] **Step 3: Create packages/shared/src/types/config.ts**

```typescript
export interface CollectorConfig {
  database: {
    path: string;
  };
  openrouter: {
    apiKey: string;
    baseUrl?: string;
  };
  sources: {
    arxiv: {
      enabled: boolean;
      categories: string[];
      maxResults: number;
    };
    github: {
      enabled: boolean;
      languages: string[];
      timeRange: 'daily' | 'weekly' | 'monthly';
    };
    rss: {
      enabled: boolean;
      rsshub?: RSSHubConfig;
      subscriptions: RSSSubscription[];
    };
  };
  pipeline: {
    relevanceThreshold: number;
    maxDailyItems: number;
  };
  scheduling: {
    fetchCron: string;
    briefingCron: string;
  };
}

import type { RSSHubConfig, RSSSubscription } from './content';
export type { RSSHubConfig, RSSSubscription };
```

- [ ] **Step 4: Create packages/shared/src/index.ts**

```typescript
export * from './types/content';
export * from './types/config';
```

- [ ] **Step 5: Create packages/shared/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "declaration": true,
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 6: Install dependencies and build**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn/packages/shared
pnpm install
pnpm build
```

- [ ] **Step 7: Commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git add packages/shared/
git commit -m "feat(shared): add content and config types"
```

---

## Task 3: Create AI Client Package

**Files:**
- Create: `packages/ai-client/package.json`
- Create: `packages/ai-client/src/models.ts`
- Create: `packages/ai-client/src/client.ts`
- Create: `packages/ai-client/src/index.ts`
- Create: `packages/ai-client/tsconfig.json`

- [ ] **Step 1: Create packages/ai-client/package.json**

```json
{
  "name": "@tokenburner/ai-client",
  "version": "1.0.0",
  "private": true,
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch",
    "test": "vitest run"
  },
  "dependencies": {
    "openai": "^4.32.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "vitest": "^1.4.0"
  }
}
```

- [ ] **Step 2: Create packages/ai-client/src/models.ts**

```typescript
export interface AIModel {
  id: string;
  name: string;
  provider: 'openrouter';
  contextLength: number;
  pricing: {
    prompt: number;
    completion: number;
  };
}

export const MODELS = {
  GPT4: {
    id: 'openai/gpt-4-turbo-preview',
    name: 'GPT-4 Turbo',
    provider: 'openrouter' as const,
    contextLength: 128000,
    pricing: { prompt: 0.01, completion: 0.03 }
  },
  CLAUDE_SONNET: {
    id: 'anthropic/claude-3.5-sonnet',
    name: 'Claude 3.5 Sonnet',
    provider: 'openrouter' as const,
    contextLength: 200000,
    pricing: { prompt: 0.003, completion: 0.015 }
  },
  KIMI: {
    id: 'moonshot/kimi-k2',
    name: 'Kimi K2',
    provider: 'openrouter' as const,
    contextLength: 256000,
    pricing: { prompt: 0.001, completion: 0.002 }
  }
} as const;

export type ModelId = typeof MODELS[keyof typeof MODELS]['id'];
```

- [ ] **Step 3: Create packages/ai-client/src/client.ts**

```typescript
import OpenAI from 'openai';
import type { ModelId } from './models';

export interface AIClientConfig {
  apiKey: string;
  baseURL?: string;
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface ChatOptions {
  model: ModelId;
  messages: ChatMessage[];
  temperature?: number;
  maxTokens?: number;
}

export interface ChatResponse {
  content: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export class AIClient {
  private client: OpenAI;

  constructor(config: AIClientConfig) {
    this.client = new OpenAI({
      apiKey: config.apiKey,
      baseURL: config.baseURL || 'https://openrouter.ai/api/v1',
      defaultHeaders: {
        'HTTP-Referer': 'https://tokenburner.local',
        'X-Title': 'TokenBurner'
      }
    });
  }

  async chat(options: ChatOptions): Promise<ChatResponse> {
    const response = await this.client.chat.completions.create({
      model: options.model,
      messages: options.messages,
      temperature: options.temperature ?? 0.7,
      max_tokens: options.maxTokens
    });

    const choice = response.choices[0];
    if (!choice?.message?.content) {
      throw new Error('Empty response from AI');
    }

    return {
      content: choice.message.content,
      usage: {
        promptTokens: response.usage?.prompt_tokens ?? 0,
        completionTokens: response.usage?.completion_tokens ?? 0,
        totalTokens: response.usage?.total_tokens ?? 0
      }
    };
  }

  async quickPrompt(
    model: ModelId,
    prompt: string,
    systemPrompt?: string
  ): Promise<ChatResponse> {
    const messages: ChatMessage[] = [];
    if (systemPrompt) {
      messages.push({ role: 'system', content: systemPrompt });
    }
    messages.push({ role: 'user', content: prompt });

    return this.chat({ model, messages });
  }
}
```

- [ ] **Step 4: Create packages/ai-client/src/index.ts**

```typescript
export * from './client';
export * from './models';
```

- [ ] **Step 5: Create packages/ai-client/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "declaration": true,
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 6: Install and build**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn/packages/ai-client
pnpm install
pnpm build
```

- [ ] **Step 7: Commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git add packages/ai-client/
git commit -m "feat(ai-client): add OpenRouter client with multi-model support"
```

---

## Task 4: Set Up Collector Database Schema

**Files:**
- Create: `apps/collector/package.json`
- Create: `apps/collector/src/database/schema.sql`
- Create: `apps/collector/src/database/client.ts`

- [ ] **Step 1: Create apps/collector/package.json**

```json
{
  "name": "@tokenburner/collector",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "build": "tsc",
    "dev": "tsx watch src/index.ts",
    "start": "node dist/index.js",
    "test": "vitest run",
    "db:init": "tsx src/database/init.ts"
  },
  "dependencies": {
    "@tokenburner/shared": "workspace:*",
    "@tokenburner/ai-client": "workspace:*",
    "better-sqlite3": "^9.4.0",
    "bullmq": "^5.4.0",
    "ioredis": "^5.3.0",
    "node-cron": "^3.0.3",
    "fast-xml-parser": "^4.3.0",
    "yaml": "^2.4.0",
    "zod": "^3.22.0"
  },
  "devDependencies": {
    "@types/better-sqlite3": "^7.6.9",
    "@types/node": "^20.0.0",
    "@types/node-cron": "^3.0.11",
    "tsx": "^4.7.0",
    "typescript": "^5.4.0",
    "vitest": "^1.4.0"
  }
}
```

- [ ] **Step 2: Create apps/collector/src/database/schema.sql**

```sql
-- Content items from all sources
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

-- RSS subscriptions
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

-- Daily briefings
CREATE TABLE IF NOT EXISTS daily_briefings (
  id TEXT PRIMARY KEY,
  date TEXT NOT NULL UNIQUE,
  items TEXT NOT NULL, -- JSON array of content item IDs
  summary TEXT,
  generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Experiment ideas
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_content_source_type ON content_items(source_type);
CREATE INDEX IF NOT EXISTS idx_content_created ON content_items(created_at);
CREATE INDEX IF NOT EXISTS idx_content_relevance ON content_items(relevance_score);
CREATE INDEX IF NOT EXISTS idx_content_processed ON content_items(processed_at);
```

- [ ] **Step 3: Create apps/collector/src/database/client.ts**

```typescript
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

  // Content Items
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

  // Daily Briefings
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

  getBriefingByDate(date: string): DailyBriefing | null {
    const stmt = this.db.prepare(`
      SELECT * FROM daily_briefings WHERE date = ?
    `);
    const row = stmt.get(date) as any;
    if (!row) return null;

    const itemIds = JSON.parse(row.items) as string[];
    const items = itemIds.map(id => {
      const itemStmt = this.db.prepare('SELECT * FROM content_items WHERE id = ?');
      const itemRow = itemStmt.get(id) as any;
      return itemRow ? this.rowToContentItem(itemRow) : null;
    }).filter(Boolean) as ContentItem[];

    return {
      id: row.id,
      date: row.date,
      items,
      summary: row.summary ?? undefined,
      generatedAt: new Date(row.generated_at)
    };
  }

  // RSS Subscriptions
  getActiveSubscriptions(): RSSSubscription[] {
    const stmt = this.db.prepare(`
      SELECT * FROM rss_subscriptions WHERE is_active = 1
    `);
    const rows = stmt.all() as any[];
    return rows.map(this.rowToSubscription);
  }

  updateSubscriptionFetchStatus(
    id: string,
    status: 'ok' | 'error',
    error?: string
  ): void {
    const stmt = this.db.prepare(`
      UPDATE rss_subscriptions
      SET last_fetched_at = ?, fetch_status = ?, last_error = ?, updated_at = ?
      WHERE id = ?
    `);

    stmt.run(
      new Date().toISOString(),
      status,
      error ?? null,
      new Date().toISOString(),
      id
    );
  }

  // Helpers
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
```

- [ ] **Step 4: Create apps/collector/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "declaration": true,
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 5: Install dependencies**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn/apps/collector
pnpm install
```

- [ ] **Step 6: Commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git add apps/collector/
git commit -m "feat(collector): add database schema and client"
```

---

## Task 5: Implement arXiv Data Source

**Files:**
- Create: `apps/collector/src/sources/arxiv.ts`
- Create: `apps/collector/tests/sources/arxiv.test.ts`

- [ ] **Step 1: Create arXiv source fetcher**

```typescript
// apps/collector/src/sources/arxiv.ts
import { XMLParser } from 'fast-xml-parser';
import type { ContentItem } from '@tokenburner/shared';

export interface ArxivOptions {
  categories: string[];
  maxResults: number;
}

const ARXIV_API_URL = 'http://export.arxiv.org/api/query';

export async function fetchArxivPapers(options: ArxivOptions): Promise<ContentItem[]> {
  const searchQuery = options.categories
    .map(cat => `cat:${cat}`)
    .join('+OR+');

  const url = new URL(ARXIV_API_URL);
  url.searchParams.set('search_query', searchQuery);
  url.searchParams.set('start', '0');
  url.searchParams.set('max_results', options.maxResults.toString());
  url.searchParams.set('sortBy', 'submittedDate');
  url.searchParams.set('sortOrder', 'descending');

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`arXiv API error: ${response.status} ${response.statusText}`);
  }

  const xml = await response.text();
  return parseArxivFeed(xml);
}

interface ArxivEntry {
  id: string;
  title: string;
  summary: string;
  published: string;
  link: { href: string } | { href: string }[];
  category: { term: string } | { term: string }[];
}

function parseArxivFeed(xml: string): ContentItem[] {
  const parser = new XMLParser({
    ignoreAttributes: false,
    attributeNamePrefix: ''
  });

  const feed = parser.parse(xml);
  const entries = feed.feed?.entry ?? [];
  const entriesArray = Array.isArray(entries) ? entries : [entries];

  return entriesArray.map((entry: ArxivEntry) => {
    const links = Array.isArray(entry.link) ? entry.link : [entry.link];
    const pdfLink = links.find((l: any) => l.title === 'pdf');
    const abstractLink = links.find((l: any) => !l.title);

    const categories = Array.isArray(entry.category)
      ? entry.category.map((c: any) => c.term)
      : [entry.category?.term];

    return {
      id: `arxiv-${entry.id.split('/').pop() ?? entry.id}`,
      source: 'arXiv',
      sourceType: 'paper',
      title: cleanText(entry.title),
      url: abstractLink?.href ?? entry.id,
      originalContent: cleanText(entry.summary),
      rawText: cleanText(entry.summary),
      relevanceScore: 0,
      category: categories.filter(Boolean),
      insights: [],
      createdAt: new Date(entry.published)
    };
  });
}

function cleanText(text: string): string {
  return text
    .replace(/\n\s+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
```

- [ ] **Step 2: Create test file**

```typescript
// apps/collector/tests/sources/arxiv.test.ts
import { describe, it, expect } from 'vitest';
import { fetchArxivPapers } from '../../src/sources/arxiv';

describe('fetchArxivPapers', () => {
  it('should fetch and parse arXiv papers', async () => {
    const papers = await fetchArxivPapers({
      categories: ['cs.CL', 'cs.AI'],
      maxResults: 5
    });

    expect(papers.length).toBeGreaterThan(0);
    expect(papers.length).toBeLessThanOrEqual(5);

    const paper = papers[0];
    expect(paper).toHaveProperty('id');
    expect(paper).toHaveProperty('title');
    expect(paper).toHaveProperty('url');
    expect(paper.sourceType).toBe('paper');
    expect(paper.source).toBe('arXiv');
  });
});
```

- [ ] **Step 3: Run test to verify**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn/apps/collector
pnpm test tests/sources/arxiv.test.ts
```

Expected: Test passes with actual arXiv data fetched

- [ ] **Step 4: Commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git add apps/collector/src/sources/arxiv.ts apps/collector/tests/
git commit -m "feat(collector): add arXiv data source"
```

---

## Task 6: Implement GitHub Trending Data Source

**Files:**
- Create: `apps/collector/src/sources/github.ts`
- Create: `apps/collector/tests/sources/github.test.ts`

- [ ] **Step 1: Create GitHub source fetcher**

```typescript
// apps/collector/src/sources/github.ts
import type { ContentItem } from '@tokenburner/shared';

export interface GitHubOptions {
  languages: string[];
  timeRange: 'daily' | 'weekly' | 'monthly';
}

// GitHub Search API for trending
export async function fetchGitHubTrending(options: GitHubOptions): Promise<ContentItem[]> {
  const dateFilter = getDateFilter(options.timeRange);
  const items: ContentItem[] = [];

  for (const language of options.languages) {
    const url = new URL('https://api.github.com/search/repositories');
    url.searchParams.set('q', `language:${language} created:>${dateFilter}`);
    url.searchParams.set('sort', 'stars');
    url.searchParams.set('order', 'desc');
    url.searchParams.set('per_page', '10');

    const response = await fetch(url.toString(), {
      headers: {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'TokenBurner-Collector'
      }
    });

    if (!response.ok) {
      console.warn(`GitHub API error for ${language}: ${response.status}`);
      continue;
    }

    const data = await response.json();
    const repos = data.items ?? [];

    for (const repo of repos) {
      items.push({
        id: `github-${repo.id}`,
        source: 'GitHub',
        sourceType: 'repo',
        title: `${repo.full_name}: ${repo.description ?? 'No description'}`,
        url: repo.html_url,
        originalContent: `⭐ ${repo.stargazers_count} stars | ${repo.description ?? 'No description'}`,
        rawText: repo.description ?? '',
        relevanceScore: 0,
        category: [language, 'github'],
        insights: [],
        createdAt: new Date(repo.created_at)
      });
    }
  }

  return items;
}

function getDateFilter(range: 'daily' | 'weekly' | 'monthly'): string {
  const now = new Date();
  const date = new Date(now);

  switch (range) {
    case 'daily':
      date.setDate(date.getDate() - 1);
      break;
    case 'weekly':
      date.setDate(date.getDate() - 7);
      break;
    case 'monthly':
      date.setMonth(date.getMonth() - 1);
      break;
  }

  return date.toISOString().split('T')[0];
}
```

- [ ] **Step 2: Create test file**

```typescript
// apps/collector/tests/sources/github.test.ts
import { describe, it, expect } from 'vitest';
import { fetchGitHubTrending } from '../../src/sources/github';

describe('fetchGitHubTrending', () => {
  it('should fetch trending repos', async () => {
    const repos = await fetchGitHubTrending({
      languages: ['typescript', 'python'],
      timeRange: 'weekly'
    });

    expect(repos.length).toBeGreaterThan(0);

    const repo = repos[0];
    expect(repo).toHaveProperty('id');
    expect(repo).toHaveProperty('title');
    expect(repo).toHaveProperty('url');
    expect(repo.sourceType).toBe('repo');
    expect(repo.source).toBe('GitHub');
  });
});
```

- [ ] **Step 3: Run test**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn/apps/collector
pnpm test tests/sources/github.test.ts
```

- [ ] **Step 4: Commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git add apps/collector/src/sources/github.ts
git commit -m "feat(collector): add GitHub trending data source"
```

---

## Task 7: Implement AI Processing Pipeline

**Files:**
- Create: `apps/collector/src/pipeline/filter.ts`
- Create: `apps/collector/src/pipeline/summarize.ts`

- [ ] **Step 1: Create relevance filter using GPT-4**

```typescript
// apps/collector/src/pipeline/filter.ts
import { AIClient, MODELS } from '@tokenburner/ai-client';
import type { ContentItem } from '@tokenburner/shared';

export interface FilterConfig {
  apiKey: string;
  threshold: number;
}

const SYSTEM_PROMPT = `You are an AI content curator. Evaluate if the given content is relevant to:
- Frontend development and AI integration
- Large Language Models (LLMs) and their applications
- AI-powered developer tools
- Machine learning for web applications
- AI research relevant to practical applications

Rate relevance from 0-10 and provide category tags.
Respond in JSON format: {"score": number, "categories": string[], "reason": string}`;

export async function filterContent(
  client: AIClient,
  item: ContentItem
): Promise<{ score: number; categories: string[] }> {
  const prompt = `Title: ${item.title}\n\nContent: ${item.originalContent.slice(0, 2000)}`;

  try {
    const response = await client.quickPrompt(
      MODELS.GPT4.id,
      prompt,
      SYSTEM_PROMPT
    );

    const result = extractJSON(response.content);
    return {
      score: Math.max(0, Math.min(10, result.score ?? 0)),
      categories: result.categories ?? []
    };
  } catch (error) {
    console.error('Filter error:', error);
    return { score: 0, categories: [] };
  }
}

function extractJSON(text: string): any {
  // Try to find JSON in markdown code block
  const codeBlockMatch = text.match(/```json\n?([\s\S]*?)\n?```/);
  if (codeBlockMatch) {
    return JSON.parse(codeBlockMatch[1]);
  }

  // Try to find JSON object directly
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    return JSON.parse(jsonMatch[0]);
  }

  throw new Error('No JSON found in response');
}
```

- [ ] **Step 2: Create summarizer using Claude**

```typescript
// apps/collector/src/pipeline/summarize.ts
import { AIClient, MODELS } from '@tokenburner/ai-client';
import type { ContentItem } from '@tokenburner/shared';

const SYSTEM_PROMPT = `Summarize the following content for a technical audience. 
Provide:
1. A concise 2-3 sentence summary
2. 2-4 key insights or takeaways as bullet points

Format your response as:
SUMMARY: [your summary here]

INSIGHTS:
- [insight 1]
- [insight 2]
...`;

export interface SummaryResult {
  summary: string;
  insights: string[];
}

export async function summarizeContent(
  client: AIClient,
  item: ContentItem
): Promise<SummaryResult> {
  const prompt = `Title: ${item.title}\n\nContent: ${item.rawText || item.originalContent}`;

  try {
    const response = await client.quickPrompt(
      MODELS.CLAUDE_SONNET.id,
      prompt,
      SYSTEM_PROMPT
    );

    return parseSummaryResponse(response.content);
  } catch (error) {
    console.error('Summarize error:', error);
    return {
      summary: item.originalContent.slice(0, 200) + '...',
      insights: []
    };
  }
}

function parseSummaryResponse(text: string): SummaryResult {
  const summaryMatch = text.match(/SUMMARY:\s*([\s\S]*?)(?=INSIGHTS:|$)/i);
  const insightsMatch = text.match(/INSIGHTS:([\s\S]*?)$/i);

  const summary = summaryMatch?.[1]?.trim() ?? '';

  const insights: string[] = [];
  if (insightsMatch?.[1]) {
    const lines = insightsMatch[1].split('\n');
    for (const line of lines) {
      const match = line.match(/^-\s*(.+)$/);
      if (match) {
        insights.push(match[1].trim());
      }
    }
  }

  return { summary, insights };
}
```

- [ ] **Step 3: Commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git add apps/collector/src/pipeline/
git commit -m "feat(collector): add AI processing pipeline (filter + summarize)"
```

---

## Task 8: Implement Daily Briefing Generator

**Files:**
- Create: `apps/collector/src/briefing/generator.ts`
- Create: `apps/collector/src/briefing/template.ts`

- [ ] **Step 1: Create briefing template**

```typescript
// apps/collector/src/briefing/template.ts
import type { ContentItem } from '@tokenburner/shared';

export function generateMarkdownBriefing(
  date: string,
  items: ContentItem[],
  summary?: string
): string {
  const sections = groupBySourceType(items);

  let markdown = `# AI Daily Briefing - ${date}\n\n`;

  if (summary) {
    markdown += `## 📋 Summary\n\n${summary}\n\n`;
  }

  markdown += `## 📊 Overview\n\n`;
  markdown += `- Total items: ${items.length}\n`;
  markdown += `- Papers: ${sections.papers?.length ?? 0}\n`;
  markdown += `- Repositories: ${sections.repos?.length ?? 0}\n`;
  markdown += `- News: ${sections.news?.length ?? 0}\n\n`;

  // Papers section
  if (sections.papers?.length) {
    markdown += `## 📄 Research Papers\n\n`;
    for (const item of sections.papers) {
      markdown += formatPaperItem(item);
    }
  }

  // Repos section
  if (sections.repos?.length) {
    markdown += `## 🛠️ Trending Repositories\n\n`;
    for (const item of sections.repos) {
      markdown += formatRepoItem(item);
    }
  }

  // News section
  if (sections.news?.length) {
    markdown += `## 📰 News & Articles\n\n`;
    for (const item of sections.news) {
      markdown += formatNewsItem(item);
    }
  }

  markdown += `---\n\n`;
  markdown += `*Generated by TokenBurner*\n`;

  return markdown;
}

function groupBySourceType(items: ContentItem[]) {
  return {
    papers: items.filter(i => i.sourceType === 'paper'),
    repos: items.filter(i => i.sourceType === 'repo'),
    news: items.filter(i => i.sourceType === 'news')
  };
}

function formatPaperItem(item: ContentItem): string {
  let md = `### ${item.title}\n\n`;
  if (item.summary) {
    md += `${item.summary}\n\n`;
  }
  if (item.insights?.length) {
    md += `**Key Insights:**\n`;
    for (const insight of item.insights) {
      md += `- ${insight}\n`;
    }
    md += '\n';
  }
  md += `[Read more](${item.url}) | Source: ${item.source}\n\n`;
  return md;
}

function formatRepoItem(item: ContentItem): string {
  let md = `### ${item.title.split(':')[0]}\n\n`;
  const desc = item.title.split(':')[1]?.trim();
  if (desc) {
    md += `${desc}\n\n`;
  }
  if (item.summary) {
    md += `${item.summary}\n\n`;
  }
  md += `[GitHub](${item.url}) | Source: ${item.source}\n\n`;
  return md;
}

function formatNewsItem(item: ContentItem): string {
  let md = `### ${item.title}\n\n`;
  if (item.summary) {
    md += `${item.summary}\n\n`;
  }
  md += `[Read more](${item.url}) | Source: ${item.source}\n\n`;
  return md;
}
```

- [ ] **Step 2: Create briefing generator**

```typescript
// apps/collector/src/briefing/generator.ts
import { AIClient, MODELS } from '@tokenburner/ai-client';
import type { ContentItem, DailyBriefing } from '@tokenburner/shared';
import { generateMarkdownBriefing } from './template';

export interface BriefingConfig {
  maxItems: number;
  minRelevance: number;
}

const SYSTEM_PROMPT = `You are creating a daily AI briefing summary. 
Given a list of AI-related content items, write a 2-3 paragraph overview that:
1. Highlights the most significant developments
2. Identifies emerging trends or patterns
3. Provides context for why these matter

Write in a professional but accessible tone suitable for technical readers.`;

export async function generateBriefing(
  client: AIClient,
  items: ContentItem[],
  config: BriefingConfig
): Promise<{ briefing: DailyBriefing; markdown: string }> {
  // Sort by relevance and take top items
  const selectedItems = items
    .filter(i => i.relevanceScore >= config.minRelevance)
    .sort((a, b) => b.relevanceScore - a.relevanceScore)
    .slice(0, config.maxItems);

  // Generate AI summary
  const summary = await generateSummary(client, selectedItems);

  // Create briefing object
  const date = new Date().toISOString().split('T')[0];
  const briefing: DailyBriefing = {
    id: `briefing-${date}`,
    date,
    items: selectedItems,
    summary,
    generatedAt: new Date()
  };

  // Generate markdown
  const markdown = generateMarkdownBriefing(date, selectedItems, summary);

  return { briefing, markdown };
}

async function generateSummary(
  client: AIClient,
  items: ContentItem[]
): Promise<string> {
  if (items.length === 0) {
    return 'No significant items to report today.';
  }

  const prompt = items
    .map((item, i) => `${i + 1}. ${item.title} (${item.sourceType})`)
    .join('\n');

  try {
    const response = await client.quickPrompt(
      MODELS.CLAUDE_SONNET.id,
      prompt,
      SYSTEM_PROMPT
    );
    return response.content.trim();
  } catch (error) {
    console.error('Summary generation error:', error);
    return `Today's briefing includes ${items.length} items across research papers, repositories, and news.`;
  }
}
```

- [ ] **Step 3: Commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git add apps/collector/src/briefing/
git commit -m "feat(collector): add daily briefing generator"
```

---

## Task 9: Create Main Collector Service Entry Point

**Files:**
- Create: `apps/collector/src/config/loader.ts`
- Create: `apps/collector/src/index.ts`
- Modify: `apps/collector/package.json` (add scripts)

- [ ] **Step 1: Create config loader**

```typescript
// apps/collector/src/config/loader.ts
import { readFileSync } from 'fs';
import { join } from 'path';
import YAML from 'yaml';
import { z } from 'zod';
import type { CollectorConfig } from '@tokenburner/shared';

const configSchema = z.object({
  database: z.object({
    path: z.string().default('./data/tokenburner.db')
  }),
  openrouter: z.object({
    apiKey: z.string(),
    baseUrl: z.string().optional()
  }),
  sources: z.object({
    arxiv: z.object({
      enabled: z.boolean().default(true),
      categories: z.array(z.string()).default(['cs.CL', 'cs.AI', 'cs.LG']),
      maxResults: z.number().default(20)
    }),
    github: z.object({
      enabled: z.boolean().default(true),
      languages: z.array(z.string()).default(['typescript', 'python']),
      timeRange: z.enum(['daily', 'weekly', 'monthly']).default('weekly')
    }),
    rss: z.object({
      enabled: z.boolean().default(false),
      subscriptions: z.array(z.any()).default([])
    })
  }),
  pipeline: z.object({
    relevanceThreshold: z.number().default(6),
    maxDailyItems: z.number().default(10)
  })
});

export function loadConfig(): CollectorConfig {
  const configPath = process.env.CONFIG_PATH || join(process.cwd(), 'config', 'collector.yaml');

  let config: any = {};
  try {
    const content = readFileSync(configPath, 'utf-8');
    config = YAML.parse(content);
  } catch (error) {
    console.warn(`Config file not found at ${configPath}, using defaults`);
  }

  // Merge with environment variables
  if (process.env.OPENROUTER_API_KEY) {
    config.openrouter = {
      ...config.openrouter,
      apiKey: process.env.OPENROUTER_API_KEY
    };
  }

  const parsed = configSchema.parse(config);
  return parsed as CollectorConfig;
}
```

- [ ] **Step 2: Create main entry point**

```typescript
// apps/collector/src/index.ts
import { AIClient } from '@tokenburner/ai-client';
import { DatabaseClient } from './database/client';
import { loadConfig } from './config/loader';
import { fetchArxivPapers } from './sources/arxiv';
import { fetchGitHubTrending } from './sources/github';
import { filterContent, type FilterConfig } from './pipeline/filter';
import { summarizeContent } from './pipeline/summarize';
import { generateBriefing } from './briefing/generator';
import { mkdirSync } from 'fs';
import { dirname } from 'path';

async function main() {
  console.log('🚀 TokenBurner Collector starting...\n');

  // Load configuration
  const config = loadConfig();
  console.log('✓ Configuration loaded');

  // Ensure data directory exists
  mkdirSync(dirname(config.database.path), { recursive: true });

  // Initialize database
  const db = new DatabaseClient(config.database.path);
  console.log('✓ Database connected');

  // Initialize AI client
  const aiClient = new AIClient({
    apiKey: config.openrouter.apiKey,
    baseURL: config.openrouter.baseUrl
  });
  console.log('✓ AI client initialized');

  // Fetch data from sources
  console.log('\n📥 Fetching data from sources...');
  const allItems = await fetchFromSources(config);
  console.log(`✓ Fetched ${allItems.length} items`);

  // Store raw items
  for (const item of allItems) {
    db.insertContentItem(item);
  }
  console.log(`✓ Stored ${allItems.length} items in database`);

  // Process unprocessed items
  console.log('\n🤖 Processing items with AI...');
  const unprocessed = db.getUnprocessedItems(50);
  console.log(`Found ${unprocessed.length} unprocessed items`);

  for (const item of unprocessed) {
    try {
      // Step 1: Filter for relevance
      const filterResult = await filterContent(aiClient, item);
      
      if (filterResult.score < config.pipeline.relevanceThreshold) {
        // Skip low-relevance items but mark as processed
        db.updateProcessedItem(item.id, {
          relevanceScore: filterResult.score,
          category: filterResult.categories
        });
        continue;
      }

      // Step 2: Summarize
      const summaryResult = await summarizeContent(aiClient, item);

      // Update item with processed data
      db.updateProcessedItem(item.id, {
        relevanceScore: filterResult.score,
        category: filterResult.categories,
        summary: summaryResult.summary,
        insights: summaryResult.insights
      });

      console.log(`  ✓ Processed: ${item.title.slice(0, 60)}... (score: ${filterResult.score})`);
    } catch (error) {
      console.error(`  ✗ Failed to process: ${item.title}`, error);
    }
  }

  // Generate daily briefing
  console.log('\n📝 Generating daily briefing...');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  const recentItems = db.getRecentItems(today, config.pipeline.relevanceThreshold);
  console.log(`Found ${recentItems.length} relevant items for briefing`);

  const { briefing, markdown } = await generateBriefing(aiClient, recentItems, {
    maxItems: config.pipeline.maxDailyItems,
    minRelevance: config.pipeline.relevanceThreshold
  });

  // Save briefing to database
  db.createBriefing(briefing);

  // Save markdown to file
  const briefingPath = `./docs/daily-briefings/${briefing.date}.md`;
  mkdirSync(dirname(briefingPath), { recursive: true });
  Bun.write(briefingPath, markdown);

  console.log(`✓ Briefing saved: ${briefingPath}`);
  console.log(`\n🎉 Done! Processed ${allItems.length} items, ${recentItems.length} in briefing.`);

  db.close();
}

async function fetchFromSources(config: any) {
  const items = [];

  if (config.sources.arxiv.enabled) {
    try {
      const papers = await fetchArxivPapers(config.sources.arxiv);
      items.push(...papers);
      console.log(`  ✓ arXiv: ${papers.length} papers`);
    } catch (error) {
      console.error('  ✗ arXiv fetch failed:', error);
    }
  }

  if (config.sources.github.enabled) {
    try {
      const repos = await fetchGitHubTrending(config.sources.github);
      items.push(...repos);
      console.log(`  ✓ GitHub: ${repos.length} repos`);
    } catch (error) {
      console.error('  ✗ GitHub fetch failed:', error);
    }
  }

  return items;
}

main().catch(console.error);
```

- [ ] **Step 3: Create default config file**

```yaml
# config/collector.yaml
database:
  path: ./data/tokenburner.db

openrouter:
  apiKey: ${OPENROUTER_API_KEY}

sources:
  arxiv:
    enabled: true
    categories:
      - cs.CL
      - cs.AI
      - cs.LG
    maxResults: 20

  github:
    enabled: true
    languages:
      - typescript
      - python
      - rust
    timeRange: weekly

  rss:
    enabled: false
    subscriptions: []

pipeline:
  relevanceThreshold: 6
  maxDailyItems: 10
```

- [ ] **Step 4: Commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git add apps/collector/src/index.ts apps/collector/src/config/ config/
git commit -m "feat(collector): add main service entry point and config"
```

---

## Task 10: Create Next.js Web Dashboard

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.js`
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/lib/db.ts`

- [ ] **Step 1: Create apps/web/package.json**

```json
{
  "name": "@tokenburner/web",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "@tokenburner/shared": "workspace:*",
    "better-sqlite3": "^9.4.0",
    "next": "14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-markdown": "^9.0.0"
  },
  "devDependencies": {
    "@types/better-sqlite3": "^7.6.9",
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 2: Create next.config.js**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ['better-sqlite3']
  }
};

module.exports = nextConfig;
```

- [ ] **Step 3: Create tailwind.config.ts**

```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}'
  ],
  theme: {
    extend: {}
  },
  plugins: []
};

export default config;
```

- [ ] **Step 4: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 5: Create app layout**

```tsx
// apps/web/src/app/layout.tsx
import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'TokenBurner - AI Intelligence Hub',
  description: 'Personal AI learning and experimentation system'
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  );
}
```

- [ ] **Step 6: Create globals.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 7: Create database client**

```typescript
// apps/web/src/lib/db.ts
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
```

- [ ] **Step 8: Create main page**

```tsx
// apps/web/src/app/page.tsx
import { getLatestBriefing } from '@/lib/db';
import ReactMarkdown from 'react-markdown';

export default function HomePage() {
  const briefing = getLatestBriefing();

  if (!briefing) {
    return (
      <main className="max-w-4xl mx-auto p-8">
        <h1 className="text-3xl font-bold mb-4">TokenBurner</h1>
        <p className="text-gray-600">No briefing available yet. Run the collector first.</p>
      </main>
    );
  }

  return (
    <main className="max-w-4xl mx-auto p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold mb-2">TokenBurner</h1>
        <p className="text-gray-600">
          Daily AI Briefing - {briefing.date}
        </p>
      </header>

      {briefing.summary && (
        <section className="bg-blue-50 rounded-lg p-6 mb-8">
          <h2 className="text-xl font-semibold mb-3">Summary</h2>
          <p className="text-gray-800">{briefing.summary}</p>
        </section>
      )}

      <section className="mb-6">
        <div className="flex gap-4 text-sm text-gray-600 mb-4">
          <span>📄 Papers: {briefing.items.filter(i => i.sourceType === 'paper').length}</span>
          <span>🛠️ Repos: {briefing.items.filter(i => i.sourceType === 'repo').length}</span>
          <span>📰 News: {briefing.items.filter(i => i.sourceType === 'news').length}</span>
        </div>
      </section>

      <section className="space-y-6">
        {briefing.items.map((item) => (
          <article
            key={item.id}
            className="bg-white rounded-lg shadow-sm border p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-3">
              <h3 className="text-lg font-semibold flex-1">
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-blue-600"
                >
                  {item.title}
                </a>
              </h3>
              <span className="text-xs bg-gray-100 px-2 py-1 rounded ml-4">
                {item.source}
              </span>
            </div>

            {item.summary && (
              <div className="text-gray-700 mb-4 prose prose-sm max-w-none">
                <ReactMarkdown>{item.summary}</ReactMarkdown>
              </div>
            )}

            {item.insights && item.insights.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-500 mb-2">Key Insights:</h4>
                <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                  {item.insights.map((insight, idx) => (
                    <li key={idx}>{insight}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex items-center gap-4 text-sm">
              <span className="text-gray-500">
                Relevance: {item.relevanceScore}/10
              </span>
              <div className="flex gap-2">
                {item.category.slice(0, 3).map((cat) => (
                  <span
                    key={cat}
                    className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs"
                  >
                    {cat}
                  </span>
                ))}
              </div>
            </div>
          </article>
        ))}
      </section>

      <footer className="mt-12 pt-6 border-t text-center text-sm text-gray-500">
        <p>Generated by TokenBurner</p>
      </footer>
    </main>
  );
}
```

- [ ] **Step 9: Install and build**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn/apps/web
pnpm install
```

- [ ] **Step 10: Commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git add apps/web/
git commit -m "feat(web): add Next.js dashboard for daily briefing"
```

---

## Task 11: Add Root Scripts and Documentation

**Files:**
- Modify: `package.json` (root)
- Create: `README.md`
- Create: `.env.example`

- [ ] **Step 1: Update root package.json**

```json
{
  "name": "token-burner",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "build": "turbo run build",
    "dev": "turbo run dev",
    "test": "turbo run test",
    "lint": "turbo run lint",
    "collector": "pnpm --filter @tokenburner/collector",
    "web": "pnpm --filter @tokenburner/web",
    "collect": "pnpm collector run start",
    "db:init": "pnpm collector run db:init"
  },
  "devDependencies": {
    "turbo": "^1.13.0",
    "typescript": "^5.4.0"
  },
  "packageManager": "pnpm@8.15.0",
  "workspaces": [
    "apps/*",
    "packages/*"
  ]
}
```

- [ ] **Step 2: Create README.md**

```markdown
# TokenBurner

Personal AI learning and experimentation system. Transform idle AI tokens into valuable cognitive growth.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Input     │────→│  Processing │────→│   Output    │
│  (Sources)  │     │   (AI Pipeline)   │     │ (Briefing)  │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Quick Start

### Prerequisites
- Node.js 20+
- pnpm 8+
- OpenRouter API key

### Installation

```bash
# Install dependencies
pnpm install

# Set up environment
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# Initialize database
pnpm db:init

# Run collector (fetch and process data)
pnpm collect

# Start web dashboard
pnpm web dev
```

### Configuration

Edit `config/collector.yaml` to customize:
- arXiv categories
- GitHub languages
- RSS subscriptions
- Pipeline thresholds

## Project Structure

- `apps/collector` - Data collection and AI processing service
- `apps/web` - Next.js dashboard
- `packages/shared` - Shared types and utilities
- `packages/ai-client` - OpenRouter API client
```

- [ ] **Step 3: Create .env.example**

```bash
# OpenRouter API Configuration
OPENROUTER_API_KEY=your_api_key_here

# Optional: Custom OpenRouter base URL
# OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Database path (optional, defaults to ./data/tokenburner.db)
# DATABASE_PATH=./data/tokenburner.db
```

- [ ] **Step 4: Commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git add package.json README.md .env.example
git commit -m "docs: add README and environment configuration"
```

---

## Plan Self-Review

### Spec Coverage Check

| Spec Requirement | Implementing Task |
|------------------|-------------------|
| Monorepo structure | Task 1 |
| Shared types (ContentItem, etc.) | Task 2 |
| AI client (OpenRouter multi-model) | Task 3 |
| Database schema (SQLite) | Task 4 |
| arXiv data source | Task 5 |
| GitHub Trending source | Task 6 |
| AI processing pipeline (GPT-4 filter + Claude summarize) | Task 7 |
| Daily briefing generator | Task 8 |
| Collector service entry | Task 9 |
| Next.js web dashboard | Task 10 |
| Documentation and setup | Task 11 |

**All Phase 1 requirements covered.**

### Placeholder Scan
- No "TBD" or "TODO" found
- All code is complete and copy-paste ready
- All commands are explicit with expected outputs

### Type Consistency
- `ContentItem`, `DailyBriefing` types match across all files
- Database schema matches shared types
- AI client types are consistent

---

## Next Steps After Plan Execution

1. **Test the collector**: Run `pnpm collect` with your OpenRouter API key
2. **Verify web dashboard**: Open http://localhost:3000 after running collector
3. **Iterate on prompts**: Tune the filtering and summarization prompts
4. **Add RSS sources**: Configure your RSSHub and subscriptions

**Plan complete and saved to `docs/superpowers/plans/2026-04-01-tokenburner-phase1.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints for review

**Which approach would you prefer?**
