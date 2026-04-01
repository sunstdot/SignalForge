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
