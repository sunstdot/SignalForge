import { AIClient, MODELS } from '@tokenburner/ai-client';
import type { ContentItem, DailyBriefing } from '@tokenburner/shared';
import { generateMarkdownBriefing } from './template';

export interface BriefingConfig {
  maxItems: number;
  minRelevance: number;
}

const SYSTEM_PROMPT = `你正在为技术读者撰写一份每日 AI 简报总结。
给定一份 AI 相关内容列表，请用中文撰写 2-3 段总览，要求：
1. 突出最重要的进展
2. 识别新兴趋势或模式
3. 提供背景说明这些内容为何重要

语气专业但易懂，适合技术背景读者阅读。`;

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
    return '今日无重要内容。';
  }

  const prompt = items
    .map((item, i) => `${i + 1}. ${item.title} (${item.sourceType === 'paper' ? '论文' : item.sourceType === 'repo' ? '仓库' : '新闻'})`)
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
    return `今日简报包含 ${items.length} 篇文章，涵盖研究论文、开源仓库和新闻。`;
  }
}
