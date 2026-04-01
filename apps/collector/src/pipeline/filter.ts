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
