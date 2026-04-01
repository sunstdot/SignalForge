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
  const selectedItems = items
    .filter(i => i.relevanceScore >= config.minRelevance)
    .sort((a, b) => b.relevanceScore - a.relevanceScore)
    .slice(0, config.maxItems);

  const summary = await generateSummary(client, selectedItems);

  const date = new Date().toISOString().split('T')[0];
  const briefing: DailyBriefing = {
    id: `briefing-${date}`,
    date,
    items: selectedItems,
    summary,
    generatedAt: new Date()
  };

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
