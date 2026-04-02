import { AIClient, MODELS } from '@tokenburner/ai-client';
import type { ContentItem } from '@tokenburner/shared';

const SYSTEM_PROMPT = `请为技术读者总结以下内容，用中文输出。
提供：
1. 一段简洁的总结（2-3句话）
2. 2-4 个关键见解或要点，用 bullet points 列出

请按以下格式输出：
SUMMARY: [中文总结内容]

INSIGHTS:
- [见解1]
- [见解2]
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
