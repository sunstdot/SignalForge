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
