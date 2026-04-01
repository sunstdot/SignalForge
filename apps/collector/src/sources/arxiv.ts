import { XMLParser } from 'fast-xml-parser';

import type { ContentItem } from '@tokenburner/shared';

export interface ArxivOptions {
  categories: string[];
  maxResults: number;
}

const ARXIV_API_URL = 'http://export.arxiv.org/api/query';

export async function fetchArxivPapers(options: ArxivOptions): Promise<ContentItem[]> {
  const searchQuery = options.categories
    .map(cat => `cat:${cat}`)
    .join('+OR+');

  // Build URL manually to preserve '+' as OR operator (URLSearchParams encodes '+' as '%2B')
  const params = new URLSearchParams();
  params.set('start', '0');
  params.set('max_results', options.maxResults.toString());
  params.set('sortBy', 'submittedDate');
  params.set('sortOrder', 'descending');
  
  // Append search_query manually to avoid encoding '+'
  const url = `${ARXIV_API_URL}?search_query=${searchQuery}&${params.toString()}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`arXiv API error: ${response.status} ${response.statusText}`);
  }

  const xml = await response.text();
  return parseArxivFeed(xml);
}

interface ArxivEntry {
  id: string;
  title: string;
  summary: string;
  published: string;
  link: { href: string } | { href: string }[];
  category: { term: string } | { term: string }[];
}

function parseArxivFeed(xml: string): ContentItem[] {
  const parser = new XMLParser({
    ignoreAttributes: false,
    attributeNamePrefix: ''
  });

  const feed = parser.parse(xml);
  const entries = feed.feed?.entry ?? [];
  const entriesArray = Array.isArray(entries) ? entries : [entries];

  return entriesArray.map((entry: ArxivEntry) => {
    const links = Array.isArray(entry.link) ? entry.link : [entry.link];
    const pdfLink = links.find((l: any) => l.title === 'pdf');
    const abstractLink = links.find((l: any) => !l.title);

    const categories = Array.isArray(entry.category)
      ? entry.category.map((c: any) => c.term)
      : [entry.category?.term];

    return {
      id: `arxiv-${entry.id.split('/').pop() ?? entry.id}`,
      source: 'arXiv',
      sourceType: 'paper',
      title: cleanText(entry.title),
      url: abstractLink?.href ?? entry.id,
      originalContent: cleanText(entry.summary),
      rawText: cleanText(entry.summary),
      relevanceScore: 0,
      category: categories.filter(Boolean),
      insights: [],
      createdAt: new Date(entry.published)
    };
  });
}

function cleanText(text: string): string {
  return text
    .replace(/\n\s+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
