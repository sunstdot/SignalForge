'use client';

import { useState, useEffect, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';

interface ContentItem {
  id: string;
  source: string;
  sourceType: 'paper' | 'repo' | 'news' | 'tweet' | 'podcast' | 'rss';
  title: string;
  url: string;
  summary?: string;
  insights?: string[];
  relevanceScore: number;
  category: string[];
}

interface Briefing {
  id: string;
  date: string;
  items: ContentItem[];
  summary?: string;
  generatedAt: string;
}

interface DateInfo {
  date: string;
  formattedDate: string;
}

type CategoryType = 'all' | 'paper' | 'repo' | 'news';

const CATEGORY_TABS = [
  { key: 'all' as CategoryType, label: '全部', icon: '∗' },
  { key: 'paper' as CategoryType, label: '论文', icon: '📄' },
  { key: 'repo' as CategoryType, label: '仓库', icon: '🛠️' },
  { key: 'news' as CategoryType, label: '新闻', icon: '📰' }
];

const SOURCE_TYPE_MAP: Record<string, string> = {
  paper: '论文',
  repo: '仓库',
  news: '新闻',
  tweet: '动态',
  podcast: '播客',
  rss: '订阅'
};

export default function BriefingPage() {
  const params = useParams();
  const router = useRouter();
  const date = params.date as string;

  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [dates, setDates] = useState<DateInfo[]>([]);
  const [adjacentDates, setAdjacentDates] = useState<{ prev: string | null; next: string | null }>({ prev: null, next: null });
  const [activeCategory, setActiveCategory] = useState<CategoryType>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [date]);

  async function fetchData() {
    setLoading(true);
    try {
      // Fetch dates list
      const datesRes = await fetch('/api/dates');
      const datesData = await datesRes.json();
      
      const formattedDates = datesData.dates.map((d: string) => ({
        date: d,
        formattedDate: formatDate(d)
      }));
      setDates(formattedDates);

      // Fetch briefing
      const briefingRes = await fetch(`/api/briefing?date=${date}`);
      const briefingData = await briefingRes.json();
      setBriefing(briefingData.briefing);

      // Fetch adjacent dates
      const adjacentRes = await fetch(`/api/adjacent-dates?date=${date}`);
      const adjacentData = await adjacentRes.json();
      setAdjacentDates(adjacentData);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  }

  const filteredItems = useMemo(() => {
    if (!briefing) return [];
    if (activeCategory === 'all') return briefing.items;
    return briefing.items.filter(item => item.sourceType === activeCategory);
  }, [briefing, activeCategory]);

  const stats = useMemo(() => {
    if (!briefing) return { paper: 0, repo: 0, news: 0, total: 0 };
    return {
      paper: briefing.items.filter(i => i.sourceType === 'paper').length,
      repo: briefing.items.filter(i => i.sourceType === 'repo').length,
      news: briefing.items.filter(i => i.sourceType === 'news').length,
      total: briefing.items.length
    };
  }, [briefing]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3 text-terminal-cyan">
          <span className="animate-pulse">▌</span>
          <span className="text-terminal-sm">Loading...</span>
        </div>
      </div>
    );
  }

  if (!briefing) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center">
        <div className="terminal-window max-w-md w-full mx-4">
          <div className="terminal-header">
            <div className="terminal-dot terminal-dot-red" />
            <div className="terminal-dot terminal-dot-yellow" />
            <div className="terminal-dot terminal-dot-green" />
            <span className="terminal-title">error</span>
          </div>
          <div className="terminal-content text-center py-8">
            <div className="text-terminal-red mb-4 text-4xl">✕</div>
            <h2 className="text-terminal-lg font-semibold mb-2">Briefing Not Found</h2>
            <p className="text-terminal-text-muted text-terminal-sm mb-6">
              No briefing available for {date}
            </p>
            <Link 
              href="/"
              className="inline-flex items-center gap-2 text-terminal-cyan hover:text-terminal-green transition-colors"
            >
              <span>←</span>
              <span>Return to latest</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Sidebar - Date Navigation */}
      <aside className="w-64 bg-terminal-bg-secondary border-r border-terminal-border flex-shrink-0 hidden lg:flex flex-col">
        <div className="p-4 border-b border-terminal-border">
          <Link href="/" className="flex items-center gap-2 text-terminal-cyan hover:text-terminal-green transition-colors">
            <span className="text-lg">◈</span>
            <span className="font-semibold tracking-tight">TokenBurner</span>
          </Link>
        </div>
        
        <div className="flex-1 overflow-y-auto scrollbar-terminal">
          <div className="p-2">
            <div className="text-terminal-xs text-terminal-text-muted uppercase tracking-wider mb-2 px-2">
              Archives
            </div>
            <nav className="space-y-1">
              {dates.map((d) => (
                <Link
                  key={d.date}
                  href={`/briefing/${d.date}`}
                  className={`block px-3 py-2 rounded text-terminal-sm transition-all duration-200 ${
                    d.date === date
                      ? 'bg-terminal-cyan/10 text-terminal-cyan border-l-2 border-terminal-cyan'
                      : 'text-terminal-text-muted hover:text-terminal-text hover:bg-terminal-bg-tertiary'
                  }`}
                >
                  <span className="font-mono">{d.date}</span>
                  <span className="ml-2 text-terminal-xs opacity-60">{d.formattedDate}</span>
                </Link>
              ))}
            </nav>
          </div>
        </div>

        <div className="p-4 border-t border-terminal-border">
          <div className="text-terminal-xs text-terminal-text-muted">
            <span className="text-terminal-green">⬤</span> System Operational
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-terminal-bg-secondary/50 backdrop-blur border-b border-terminal-border sticky top-0 z-20">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              {/* Mobile Menu Button */}
              <div className="lg:hidden flex items-center gap-3">
                <Link href="/" className="text-terminal-cyan text-lg">◈</Link>
                <span className="text-terminal-sm text-terminal-text-muted">TokenBurner</span>
              </div>

              {/* Date Navigation */}
              <div className="flex items-center gap-4">
                {adjacentDates.prev && (
                  <Link
                    href={`/briefing/${adjacentDates.prev}`}
                    className="flex items-center gap-1 text-terminal-sm text-terminal-text-muted hover:text-terminal-cyan transition-colors"
                  >
                    <span>←</span>
                    <span className="hidden sm:inline">{adjacentDates.prev}</span>
                  </Link>
                )}
                
                <div className="flex items-center gap-3">
                  <span className="prompt">❯</span>
                  <h1 className="text-terminal-lg font-semibold text-terminal-cyan">
                    {date}
                  </h1>
                  <span className="text-terminal-xs text-terminal-text-muted bg-terminal-bg-tertiary px-2 py-1 rounded">
                    {formatDate(date)}
                  </span>
                </div>

                {adjacentDates.next && (
                  <Link
                    href={`/briefing/${adjacentDates.next}`}
                    className="flex items-center gap-1 text-terminal-sm text-terminal-text-muted hover:text-terminal-cyan transition-colors"
                  >
                    <span className="hidden sm:inline">{adjacentDates.next}</span>
                    <span>→</span>
                  </Link>
                )}
              </div>

              {/* Stats Summary */}
              <div className="hidden md:flex items-center gap-4 text-terminal-xs">
                <span className="text-terminal-cyan">Papers: {stats.paper}</span>
                <span className="text-terminal-green">Repos: {stats.repo}</span>
                <span className="text-terminal-yellow">News: {stats.news}</span>
              </div>
            </div>
          </div>

          {/* Category Tabs */}
          <div className="px-6 border-t border-terminal-border">
            <div className="flex gap-1">
              {CATEGORY_TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveCategory(tab.key)}
                  className={`px-4 py-3 text-terminal-sm font-medium transition-all duration-200 relative ${
                    activeCategory === tab.key
                      ? 'text-terminal-cyan'
                      : 'text-terminal-text-muted hover:text-terminal-text'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  <span>{tab.label}</span>
                  {activeCategory === tab.key && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-terminal-cyan shadow-glow-cyan" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto scrollbar-terminal">
          <div className="max-w-4xl mx-auto p-6">
            {/* Summary Section */}
            {briefing.summary && (
              <section className="mb-8 animate-fade-in">
                <div className="terminal-window">
                  <div className="terminal-header">
                    <div className="terminal-dot terminal-dot-cyan" style={{ backgroundColor: '#39d0d8' }} />
                    <span className="terminal-title">Daily Summary</span>
                  </div>
                  <div className="terminal-content">
                    <div className="markdown-content text-terminal-sm">
                      <ReactMarkdown>{briefing.summary}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* Items List */}
            <section className="space-y-4">
              {filteredItems.length === 0 ? (
                <div className="text-center py-12 text-terminal-text-muted">
                  <span className="text-4xl block mb-4">∅</span>
                  <p>No items found for this category</p>
                </div>
              ) : (
                filteredItems.map((item, index) => (
                  <article
                    key={item.id}
                    className="terminal-window group hover:border-terminal-cyan/50 transition-all duration-300 animate-slide-in"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <div className="terminal-header">
                      <div className={`terminal-dot ${
                        item.sourceType === 'paper' ? 'terminal-dot-cyan' :
                        item.sourceType === 'repo' ? 'terminal-dot-green' :
                        item.sourceType === 'news' ? 'terminal-dot-yellow' :
                        'terminal-dot-blue'
                      }`} style={{
                        backgroundColor: item.sourceType === 'paper' ? '#39d0d8' :
                                        item.sourceType === 'repo' ? '#7ee787' :
                                        item.sourceType === 'news' ? '#d29922' : '#58a6ff'
                      }} />
                      <span className="terminal-title uppercase tracking-wider">
                        {SOURCE_TYPE_MAP[item.sourceType] || item.sourceType}
                      </span>
                      <span className="ml-auto text-terminal-xs text-terminal-text-muted">
                        {item.source}
                      </span>
                    </div>
                    
                    <div className="terminal-content">
                      {/* Title */}
                      <h3 className="text-terminal-lg font-semibold mb-3">
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-terminal-text hover:text-terminal-cyan transition-colors duration-200"
                        >
                          {item.title}
                          <span className="inline-block ml-2 text-terminal-xs opacity-0 group-hover:opacity-100 transition-opacity">↗</span>
                        </a>
                      </h3>

                      {/* Summary */}
                      {item.summary && (
                        <div className="markdown-content text-terminal-sm text-terminal-text/90 mb-4">
                          <ReactMarkdown>{item.summary}</ReactMarkdown>
                        </div>
                      )}

                      {/* Insights */}
                      {item.insights && item.insights.length > 0 && (
                        <div className="mb-4 pl-4 border-l-2 border-terminal-green/30">
                          <div className="text-terminal-xs text-terminal-green mb-2 uppercase tracking-wider">
                            Key Insights
                          </div>
                          <ul className="space-y-1">
                            {item.insights.map((insight, idx) => (
                              <li key={idx} className="text-terminal-sm text-terminal-text-muted flex items-start gap-2">
                                <span className="text-terminal-green mt-1">›</span>
                                <span>{insight}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Footer */}
                      <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-terminal-border/50">
                        <span className={`text-terminal-xs px-2 py-1 rounded ${
                          item.sourceType === 'paper' ? 'badge-paper' :
                          item.sourceType === 'repo' ? 'badge-repo' :
                          item.sourceType === 'news' ? 'badge-news' : 'badge-tweet'
                        }`}>
                          Relevance: {item.relevanceScore}/10
                        </span>
                        
                        {item.category.slice(0, 3).map((cat) => (
                          <span
                            key={cat}
                            className="text-terminal-xs text-terminal-text-muted bg-terminal-bg-tertiary px-2 py-1 rounded"
                          >
                            #{cat}
                          </span>
                        ))}
                      </div>
                    </div>
                  </article>
                ))
              )}
            </section>

            {/* Footer */}
            <footer className="mt-12 pt-6 border-t border-terminal-border text-center text-terminal-xs text-terminal-text-muted">
              <p>
                <span className="text-terminal-cyan">◈</span> TokenBurner Intelligence Hub
                <span className="mx-2">·</span>
                <span>Generated: {new Date(briefing.generatedAt).toLocaleString()}</span>
              </p>
            </footer>
          </div>
        </div>
      </main>
    </div>
  );
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  return days[date.getDay()];
}
