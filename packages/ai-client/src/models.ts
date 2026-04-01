export interface AIModel {
  id: string;
  name: string;
  provider: 'openrouter' | 'wanqing';
  contextLength: number;
  pricing: {
    prompt: number;
    completion: number;
  };
}

// OpenRouter Models (commented out for reference)
// export const MODELS = {
//   GPT4: {
//     id: 'openai/gpt-4-turbo-preview',
//     name: 'GPT-4 Turbo',
//     provider: 'openrouter' as const,
//     contextLength: 128000,
//     pricing: { prompt: 0.01, completion: 0.03 }
//   },
//   CLAUDE_SONNET: {
//     id: 'anthropic/claude-3.5-sonnet',
//     name: 'Claude 3.5 Sonnet',
//     provider: 'openrouter' as const,
//     contextLength: 200000,
//     pricing: { prompt: 0.003, completion: 0.015 }
//   },
//   KIMI: {
//     id: 'moonshot/kimi-k2',
//     name: 'Kimi K2',
//     provider: 'openrouter' as const,
//     contextLength: 256000,
//     pricing: { prompt: 0.001, completion: 0.002 }
//   }
// } as const;

// WanQing Models
export const WANQING_MODEL_ID_MAP = {
  'claude-4-sonnet': 'app-howejj-1754308237798253446',
  'claude-4.5-sonnet': 'app-lcv5h0-1768531025728238284',
  'gemini-2.5-flash': 'app-efeghv-1756386872976559161',
  'gemini-2.5-pro': 'app-yop6a9-1756386979360888484',
  'gpt-4o': 'app-4w0q1j-1756387195836995863',
  'kimi-k2-instruct': 'app-gg804h-1756387270454327613',
  'qwen3': 'app-benswb-1756387103774007738',
  'claude-4-sonnet-public': 'app-pw7ri6-1753428883373131839',
  'staging': 'app-ygppb1-1755497583881759099',
  'message-compact': 'app-q64zyv-1762783703826199540',
  'Qwen-VL-Max': 'app-xwr8tv-1768481168754368505',
  'Gemini-3-Flash-Preview': 'app-1sve3f-1768292746112847746',
  'GPT-5.2': 'app-1152jv-1768292886396718562',
  "Grok4": 'app-mludio-1768292952598110306',
  "Claude-Opus-4.6": 'app-ck1iaq-1771557657396809606',
  "MiniMax-M25": 'app-puckf9-1772787285399805387',
  "Kimi-K25": 'app-mt36z6-1770726564614261807'
} as const;

export type WanQingModelName = keyof typeof WANQING_MODEL_ID_MAP;

// Active Models (using WanQing)
export const MODELS = {
  GPT4: {
    id: WANQING_MODEL_ID_MAP['gpt-4o'],
    name: 'GPT-4o',
    provider: 'wanqing' as const,
    contextLength: 128000,
    pricing: { prompt: 0, completion: 0 }  // Internal pricing
  },
  CLAUDE_SONNET: {
    id: WANQING_MODEL_ID_MAP['claude-4.5-sonnet'],
    name: 'Claude 4.5 Sonnet',
    provider: 'wanqing' as const,
    contextLength: 200000,
    pricing: { prompt: 0, completion: 0 }
  },
  KIMI: {
    id: WANQING_MODEL_ID_MAP['kimi-k2-instruct'],
    name: 'Kimi K2',
    provider: 'wanqing' as const,
    contextLength: 256000,
    pricing: { prompt: 0, completion: 0 }
  }
} as const;

export type ModelId = typeof MODELS[keyof typeof MODELS]['id'];

export function getWanQingAppId(modelName: WanQingModelName): string {
  return WANQING_MODEL_ID_MAP[modelName] || WANQING_MODEL_ID_MAP['claude-4.5-sonnet'];
}
