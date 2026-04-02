import type { ContentItem } from '@tokenburner/shared';

export function generateMarkdownBriefing(
  date: string,
  items: ContentItem[],
  summary?: string
): string {
  const sections = groupBySourceType(items);

  let markdown = `# TokenBurner AI 日报 - ${date}\n\n`;

  if (summary) {
    markdown += `## 📋 今日概览\n\n${summary}\n\n`;
  }

  markdown += `## 📊 统计\n\n`;
  markdown += `- 总文章数: ${items.length}\n`;
  markdown += `- 论文: ${sections.papers?.length ?? 0}\n`;
  markdown += `- 开源仓库: ${sections.repos?.length ?? 0}\n`;
  markdown += `- 新闻: ${sections.news?.length ?? 0}\n\n`;

  if (sections.papers?.length) {
    markdown += `## 📄 研究论文\n\n`;
    for (const item of sections.papers) {
      markdown += formatPaperItem(item);
    }
  }

  if (sections.repos?.length) {
    markdown += `## 🛠️ 热门仓库\n\n`;
    for (const item of sections.repos) {
      markdown += formatRepoItem(item);
    }
  }

  if (sections.news?.length) {
    markdown += `## 📰 新闻与文章\n\n`;
    for (const item of sections.news) {
      markdown += formatNewsItem(item);
    }
  }

  markdown += `---\n\n`;
  markdown += `*由 TokenBurner 生成*`;

  return markdown;
}

function groupBySourceType(items: ContentItem[]) {
  return {
    papers: items.filter(i => i.sourceType === 'paper'),
    repos: items.filter(i => i.sourceType === 'repo'),
    news: items.filter(i => i.sourceType === 'news')
  };
}

function formatPaperItem(item: ContentItem): string {
  let md = `### ${item.title}\n\n`;
  if (item.summary) {
    md += `${item.summary}\n\n`;
  }
  if (item.insights?.length) {
    md += `**核心见解：**\n`;
    for (const insight of item.insights) {
      md += `- ${insight}\n`;
    }
    md += '\n';
  }
  md += `[阅读更多](${item.url}) | 来源: ${item.source}\n\n`;
  return md;
}

function formatRepoItem(item: ContentItem): string {
  let md = `### ${item.title.split(':')[0]}\n\n`;
  const desc = item.title.split(':')[1]?.trim();
  if (desc) {
    md += `${desc}\n\n`;
  }
  if (item.summary) {
    md += `${item.summary}\n\n`;
  }
  md += `[GitHub](${item.url}) | 来源: ${item.source}\n\n`;
  return md;
}

function formatNewsItem(item: ContentItem): string {
  let md = `### ${item.title}\n\n`;
  if (item.summary) {
    md += `${item.summary}\n\n`;
  }
  md += `[阅读更多](${item.url}) | 来源: ${item.source}\n\n`;
  return md;
}
