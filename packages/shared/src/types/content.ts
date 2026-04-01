export interface ContentItem {
  id: string;
  source: string;
  sourceType: 'paper' | 'repo' | 'news' | 'tweet' | 'podcast' | 'rss';
  subscriptionId?: string;
  title: string;
  url: string;
  originalContent: string;
  rawText?: string;
  relevanceScore: number;
  category: string[];
  summary?: string;
  insights?: string[];
  createdAt: Date;
  processedAt?: Date;
}

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

export interface RSSHubConfig {
  instanceUrl: string;
  accessKey?: string;
  isSelfHosted: boolean;
}

export interface DailyBriefing {
  id: string;
  date: string;
  items: ContentItem[];
  summary: string;
  generatedAt: Date;
}
