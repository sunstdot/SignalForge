import { AIClient } from '@tokenburner/ai-client';
import { DatabaseClient } from './database/client';
import { loadConfig } from './config/loader';
import { fetchArxivPapers } from './sources/arxiv';
import { fetchGitHubTrending } from './sources/github';
import { filterContent } from './pipeline/filter';
import { summarizeContent } from './pipeline/summarize';
import { generateBriefing } from './briefing/generator';
import { mkdirSync, writeFileSync } from 'fs';
import { dirname } from 'path';

async function main() {
  console.log('🚀 TokenBurner Collector starting...\n');

  const config = loadConfig();
  console.log('✓ Configuration loaded');

  mkdirSync(dirname(config.database.path), { recursive: true });

  const db = new DatabaseClient(config.database.path);
  console.log('✓ Database connected');

  // OpenRouter AI client (commented out)
  // const aiClient = new AIClient({
  //   apiKey: config.openrouter.apiKey,
  //   baseURL: config.openrouter.baseUrl
  // });

  // WanQing AI client
  const aiClient = new AIClient({
    apiKey: config.wanqing?.apiKey,
    baseURL: config.wanqing?.baseUrl
  });
  console.log('✓ WanQing AI client initialized');

  console.log('\n📥 Fetching data from sources...');
  const allItems = await fetchFromSources(config);
  console.log(`✓ Fetched ${allItems.length} items`);

  for (const item of allItems) {
    db.insertContentItem(item);
  }
  console.log(`✓ Stored ${allItems.length} items in database`);

  console.log('\n🤖 Processing items with AI...');
  const unprocessed = db.getUnprocessedItems(50);
  console.log(`Found ${unprocessed.length} unprocessed items`);

  for (const item of unprocessed) {
    try {
      const filterResult = await filterContent(aiClient, item);
      
      if (filterResult.score < config.pipeline.relevanceThreshold) {
        db.updateProcessedItem(item.id, {
          relevanceScore: filterResult.score,
          category: filterResult.categories
        });
        continue;
      }

      const summaryResult = await summarizeContent(aiClient, item);

      db.updateProcessedItem(item.id, {
        relevanceScore: filterResult.score,
        category: filterResult.categories,
        summary: summaryResult.summary,
        insights: summaryResult.insights
      });

      console.log(`  ✓ Processed: ${item.title.slice(0, 60)}... (score: ${filterResult.score})`);
    } catch (error) {
      console.error(`  ✗ Failed to process: ${item.title}`, error);
    }
  }

  console.log('\n📝 Generating daily briefing...');
  // 获取最近 3 天的文章（而不是仅今天）
  const since = new Date();
  since.setDate(since.getDate() - 3);
  since.setHours(0, 0, 0, 0);
  
  const recentItems = db.getRecentItems(since, config.pipeline.relevanceThreshold);
  console.log(`Found ${recentItems.length} relevant items for briefing`);

  const { briefing, markdown } = await generateBriefing(aiClient, recentItems, {
    maxItems: config.pipeline.maxDailyItems,
    minRelevance: config.pipeline.relevanceThreshold
  });

  db.createBriefing(briefing);

  const briefingPath = `./docs/daily-briefings/${briefing.date}.md`;
  mkdirSync(dirname(briefingPath), { recursive: true });
  writeFileSync(briefingPath, markdown);

  console.log(`✓ Briefing saved: ${briefingPath}`);
  console.log(`\n🎉 Done! Processed ${allItems.length} items, ${recentItems.length} in briefing.`);

  db.close();
}

async function fetchFromSources(config: any) {
  const items = [];

  if (config.sources.arxiv.enabled) {
    try {
      const papers = await fetchArxivPapers(config.sources.arxiv);
      items.push(...papers);
      console.log(`  ✓ arXiv: ${papers.length} papers`);
    } catch (error) {
      console.error('  ✗ arXiv fetch failed:', error);
    }
  }

  if (config.sources.github.enabled) {
    try {
      const repos = await fetchGitHubTrending(config.sources.github);
      items.push(...repos);
      console.log(`  ✓ GitHub: ${repos.length} repos`);
    } catch (error) {
      console.error('  ✗ GitHub fetch failed:', error);
    }
  }

  return items;
}

main().catch(console.error);
