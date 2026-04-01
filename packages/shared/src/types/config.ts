export interface CollectorConfig {
  database: {
    path: string;
  };
  
  // OpenRouter Configuration (commented out)
  // openrouter: {
  //   apiKey: string;
  //   baseUrl?: string;
  // };
  
  // WanQing Configuration
  wanqing?: {
    apiKey?: string;
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
  scheduling?: {
    fetchCron: string;
    briefingCron: string;
  };
}

import type { RSSHubConfig, RSSSubscription } from './content';
export type { RSSHubConfig, RSSSubscription };
