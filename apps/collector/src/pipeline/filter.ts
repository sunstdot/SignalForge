import { AIClient, MODELS } from '@tokenburner/ai-client';
import type { ContentItem } from '@tokenburner/shared';

export interface FilterConfig {
  apiKey: string;
  threshold: number;
}

const SYSTEM_PROMPT = `你是一位 AI 内容策展人。评估给定内容是否与以下领域相关：
- 前端开发与 AI 集成
- 大语言模型 (LLM) 及其应用
- AI 驱动的开发者工具
- 面向 Web 应用的机器学习
- 与实用应用相关的 AI 研究

请用 0-10 分评分相关性，并提供中文分类标签（如：["AI研究", "开发者工具", "前端技术"]）。
以 JSON 格式返回：{"score": 数字, "categories": 字符串数组, "reason": "评分理由"}`;

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
  const codeBlockMatch = text.match(/```json\n?([\s\S]*?)\n?```/);
  if (codeBlockMatch) {
    return JSON.parse(codeBlockMatch[1]);
  }

  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    return JSON.parse(jsonMatch[0]);
  }

  throw new Error('No JSON found in response');
}
