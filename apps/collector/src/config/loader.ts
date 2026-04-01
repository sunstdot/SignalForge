import { readFileSync } from 'fs';
import { join } from 'path';
import YAML from 'yaml';
import { z } from 'zod';
import type { CollectorConfig } from '@tokenburner/shared';

// OpenRouter Configuration (commented out)
// const configSchema = z.object({
//   database: z.object({
//     path: z.string().default('./data/tokenburner.db')
//   }),
//   openrouter: z.object({
//     apiKey: z.string(),
//     baseUrl: z.string().optional()
//   }),

// WanQing Configuration
const configSchema = z.object({
  database: z.object({
    path: z.string().default('./data/tokenburner.db')
  }),
  wanqing: z.object({
    apiKey: z.string().optional(),
    baseUrl: z.string().optional()
  }).optional(),
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

  // OpenRouter environment variable (commented out)
  // if (process.env.OPENROUTER_API_KEY) {
  //   config.openrouter = {
  //     ...config.openrouter,
  //     apiKey: process.env.OPENROUTER_API_KEY
  //   };
  // }

  // WanQing environment variable
  if (process.env.WANQING_API_KEY) {
    config.wanqing = {
      ...config.wanqing,
      apiKey: process.env.WANQING_API_KEY
    };
  }

  const parsed = configSchema.parse(config);
  return parsed as CollectorConfig;
}
