/**
 * Smol AI News crawler
 * https://news.smol.ai/
 * 
 * URL format: https://news.smol.ai/issues/26-04-01-not-much
 * Date format in URL: YY-MM-DD
 */

import type { ContentItem } from '@tokenburner/shared';

const SMOLAI_BASE_URL = 'https://news.smol.ai';

export interface SmolAIOptions {
  maxIssues: number;  // Number of recent issues to fetch
}

/**
 * Generate possible issue URLs for the last N days
 */
function generateIssueUrls(days: number): string[] {
  const urls: string[] = [];
  const today = new Date();
  
  for (let i = 0; i < days; i++) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    
    const year = date.getFullYear().toString().slice(-2);  // 26
    const month = (date.getMonth() + 1).toString().padStart(2, '0');  // 04
    const day = date.getDate().toString().padStart(2, '0');  // 01
    
    // Try common slug patterns
    const datePrefix = `${year}-${month}-${day}`;
    urls.push(`${SMOLAI_BASE_URL}/issues/${datePrefix}-not-much`);
    urls.push(`${SMOLAI_BASE_URL}/issues/${datePrefix}-ai`);
    urls.push(`${SMOLAI_BASE_URL}/issues/${datePrefix}-news`);
  }
  
  return urls;
}

/**
 * Fetch and parse a single issue page
 */
async function fetchIssue(url: string): Promise<ContentItem | null> {
  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    });
    
    if (!response.ok) {
      return null;
    }
    
    const html = await response.text();
    return parseIssuePage(html, url);
  } catch (error) {
    console.error(`Failed to fetch ${url}:`, error);
    return null;
  }
}

/**
 * Parse HTML content of an issue page
 */
function parseIssuePage(html: string, url: string): ContentItem | null {
  try {
    // Extract date from URL
    const dateMatch = url.match(/issues\/(\d{2})-(\d{2})-(\d{2})/);
    if (!dateMatch) return null;
    
    const [, year, month, day] = dateMatch;
    const fullYear = `20${year}`;
    const date = new Date(`${fullYear}-${month}-${day}`);
    
    // Extract title from HTML (look for h1 or title)
    const titleMatch = html.match(/<h1[^>]*>([^<]+)<\/h1>/i) || 
                       html.match(/<title>([^<]+)<\/title>/i);
    const title = titleMatch ? titleMatch[1].trim() : `Smol AI News ${year}-${month}-${day}`;
    
    // Extract main content
    // Try to find the main article content
    let content = '';
    
    // Look for article or main content div
    const articleMatch = html.match(/<article[^>]*>([\s\S]*?)<\/article>/i) ||
                        html.match(/<main[^>]*>([\s\S]*?)<\/main>/i) ||
                        html.match(/<div[^>]*class=["']content["'][\s\S]*?>([\s\S]*?)<\/div>/i);
    
    if (articleMatch) {
      content = cleanHtml(articleMatch[1]);
    } else {
      // Fallback: extract text from body
      const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
      if (bodyMatch) {
        content = cleanHtml(bodyMatch[1]);
      }
    }
    
    // Extract links from the content
    const links: string[] = [];
    const linkRegex = /href=["'](https?:\/\/[^"']+)["']/g;
    let match;
    while ((match = linkRegex.exec(html)) !== null) {
      links.push(match[1]);
    }
    
    // Create a summary from the content (first 500 chars)
    const summary = content.slice(0, 500).trim();
    
    return {
      id: `smolai-${year}${month}${day}`,
      source: 'Smol AI News',
      sourceType: 'news',
      title: title,
      url: url,
      originalContent: content.slice(0, 2000),
      rawText: content,
      relevanceScore: 0,
      category: ['ai', 'news', 'daily'],
      insights: links.slice(0, 5),  // Store top 5 links as insights
      createdAt: date
    };
  } catch (error) {
    console.error('Failed to parse issue page:', error);
    return null;
  }
}

/**
 * Clean HTML tags from content
 */
function cleanHtml(html: string): string {
  return html
    // Remove script and style tags
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    // Replace common tags with newlines
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<\/div>/gi, '\n')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<li>/gi, '• ')
    // Remove all remaining HTML tags
    .replace(/<[^>]+>/g, '')
    // Decode HTML entities
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
    // Clean up whitespace
    .replace(/\n\s*\n/g, '\n\n')
    .trim();
}

/**
 * Main fetch function
 */
export async function fetchSmolAINews(options: SmolAIOptions): Promise<ContentItem[]> {
  console.log(`Fetching Smol AI News (last ${options.maxIssues} issues)...`);
  
  const urls = generateIssueUrls(options.maxIssues);
  const items: ContentItem[] = [];
  
  // Try to fetch each URL
  for (const url of urls) {
    const item = await fetchIssue(url);
    if (item) {
      items.push(item);
      console.log(`  ✓ Fetched: ${item.title}`);
    }
  }
  
  console.log(`✓ Smol AI News: ${items.length} issues fetched`);
  return items;
}
