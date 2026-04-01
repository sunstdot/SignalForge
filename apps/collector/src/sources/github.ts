import type { ContentItem } from '@tokenburner/shared';

export interface GitHubOptions {
  languages: string[];
  timeRange: 'daily' | 'weekly' | 'monthly';
}

export async function fetchGitHubTrending(options: GitHubOptions): Promise<ContentItem[]> {
  const dateFilter = getDateFilter(options.timeRange);
  const items: ContentItem[] = [];

  for (const language of options.languages) {
    const url = new URL('https://api.github.com/search/repositories');
    url.searchParams.set('q', `language:${language} created:>${dateFilter}`);
    url.searchParams.set('sort', 'stars');
    url.searchParams.set('order', 'desc');
    url.searchParams.set('per_page', '10');

    const response = await fetch(url.toString(), {
      headers: {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'TokenBurner-Collector'
      }
    });

    if (!response.ok) {
      console.warn(`GitHub API error for ${language}: ${response.status}`);
      continue;
    }

    const data = await response.json();
    const repos = data.items ?? [];

    for (const repo of repos) {
      items.push({
        id: `github-${repo.id}`,
        source: 'GitHub',
        sourceType: 'repo',
        title: `${repo.full_name}: ${repo.description ?? 'No description'}`,
        url: repo.html_url,
        originalContent: `⭐ ${repo.stargazers_count} stars | ${repo.description ?? 'No description'}`,
        rawText: repo.description ?? '',
        relevanceScore: 0,
        category: [language, 'github'],
        insights: [],
        createdAt: new Date(repo.created_at)
      });
    }
  }

  return items;
}

function getDateFilter(range: 'daily' | 'weekly' | 'monthly'): string {
  const now = new Date();
  const date = new Date(now);

  switch (range) {
    case 'daily':
      date.setDate(date.getDate() - 1);
      break;
    case 'weekly':
      date.setDate(date.getDate() - 7);
      break;
    case 'monthly':
      date.setMonth(date.getMonth() - 1);
      break;
  }

  return date.toISOString().split('T')[0];
}
