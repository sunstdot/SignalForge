'use client';

import { useState, useEffect, useMemo } from 'react';
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

export default function HomePage() {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [dates, setDates] = useState<DateInfo[]>([]);
  const [activeCategory, setActiveCategory] = useState<CategoryType>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    setLoading(true);
    try {
      // Fetch latest briefing
      const briefingRes = await fetch('/api/briefing/latest');
      const briefingData = await briefingRes.json();
      setBriefing(briefingData.briefing);

      // Fetch dates list
      const datesRes = await fetch('/api/dates');
      const datesData = await datesRes.json();
      
      const formattedDates = datesData.dates.map((d: string) => ({
        date: d,
        formattedDate: formatDate(d)
      }));
      setDates(formattedDates);
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
          <span className="text-terminal-sm">Initializing TokenBurner...</span>
        </div>
      </div>
    );
  }

  if (!briefing) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4">
        <div className="terminal-window max-w-md w-full">
          <div className="terminal-header">
            <div className="terminal-dot terminal-dot-red" />
            <div className="terminal-dot terminal-dot-yellow" />
            <div className="terminal-dot terminal-dot-green" />
            <span className="terminal-title">system</span>
          </div>
          <div className="terminal-content text-center py-8">
            <div className="text-terminal-yellow mb-4 text-4xl">⚠</div>
            <h2 className="text-terminal-lg font-semibold mb-2">No Briefing Available</h2>
            <p className="text-terminal-text-muted text-terminal-sm mb-6">
              The database appears to be empty. Run the collector to generate briefings.
            </p>
            <div className="text-terminal-xs text-terminal-text-dim font-mono">
              <p>$ npm run collect</p>
              <p className="mt-1">$ npm run generate</p>
            </div>
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
          <div className="flex items-center gap-2 text-terminal-cyan">
            <span className="text-lg">◈</span>
            <span className="font-semibold tracking-tight">TokenBurner</span>
          </div>
          <div className="text-terminal-xs text-terminal-text-muted mt-1">
            AI Intelligence Hub
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto scrollbar-terminal">
          <div className="p-2">
            <div className="text-terminal-xs text-terminal-text-muted uppercase tracking-wider mb-2 px-2">
              Archives
            </div>
            <nav className="space-y-1">
              {dates.map((d, index) => (
                <Link
                  key={d.date}
                  href={`/briefing/${d.date}`}
                  className={`block px-3 py-2 rounded text-terminal-sm transition-all duration-200 ${
                    index === 0
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
          <div className="text-terminal-xs text-terminal-text-muted space-y-1">
            <div>
              <span className="text-terminal-green">⬤</span> System Online
            </div>
            <div className="text-terminal-text-dim">
              v1.0.0 · {dates.length} archives
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-terminal-bg-secondary/50 backdrop-blur border-b border-terminal-border sticky top-0 z-20">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between flex-wrap gap-4">
              {/* Left: Title & Date */}
              <div className="flex items-center gap-4">
                <div className="lg:hidden">
                  <span className="text-terminal-cyan text-lg">◈</span>
                </div>
                
                <div>
                  <div className="flex items-center gap-2">
                    <span className="prompt">❯</span>
                    <Link 
                      href={`/briefing/${briefing.date}`}
                      className="text-terminal-lg font-semibold text-terminal-cyan hover:text-terminal-green transition-colors"
                    >
                      {briefing.date}
                    </Link>
                  </div>
                  <div className="text-terminal-xs text-terminal-text-muted mt-0.5">
                    Daily AI Briefing · {formatFullDate(briefing.date)}
                  </div>
                </div>
              </div>

              {/* Right: Stats */}
              <div className="flex items-center gap-4 text-terminal-xs">
                <div className="hidden sm:flex items-center gap-3 bg-terminal-bg-tertiary rounded-lg px-3 py-2">
                  <StatBadge icon="📄" label="Papers" value={stats.paper} color="cyan" />
                  <span className="text-terminal-border">|</span>
                  <StatBadge icon="🛠️" label="Repos" value={stats.repo} color="green" />
                  <span className="text-terminal-border">|</span>
                  <StatBadge icon="📰" label="News" value={stats.news} color="yellow" />
                </div>
                
                <div className="sm:hidden flex items-center gap-2">
                  <span className="text-terminal-cyan">{stats.total}</span>
                  <span className="text-terminal-text-muted">items</span>
                </div>
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
                    <div className="terminal-dot" style={{ backgroundColor: '#39d0d8' }} />
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
                  <BriefingCard key={item.id} item={item} index={index} />
                ))
              )}
            </section>

            {/* Footer */}
            <footer className="mt-12 pt-6 border-t border-terminal-border">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-terminal-xs text-terminal-text-muted">
                <p className="flex items-center gap-2">
                  <span className="text-terminal-cyan">◈</span>
                  <span>TokenBurner Intelligence Hub</span>
                </p>
                <p>
                  <span className="text-terminal-text-dim">Generated:</span>
                  <span className="ml-1">{new Date(briefing.generatedAt).toLocaleString()}</span>
                </p>
              </div>
            </footer>
          </div>
        </div>
      </main>
    </div>
  );
}

function BriefingCard({ item, index }: { item: ContentItem; index: number }) {
  const dotColor = {
    paper: '#39d0d8',
    repo: '#7ee787',
    news: '#d29922',
    tweet: '#58a6ff',
    podcast: '#a371f7',
    rss: '#ff7b72'
  }[item.sourceType] || '#7d8590';

  const badgeClass = {
    paper: 'badge-paper',
    repo: 'badge-repo',
    news: 'badge-news',
    tweet: 'badge-tweet',
    podcast: 'badge-tweet',
    rss: 'badge-tweet'
  }[item.sourceType] || 'badge-tweet';

  return (
    <article
      className="terminal-window group hover:border-terminal-cyan/50 transition-all duration-300 animate-slide-in"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="terminal-header">
        <div className="terminal-dot" style={{ backgroundColor: dotColor }} />
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
          <span className={`text-terminal-xs px-2 py-1 rounded ${badgeClass}`}>
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
  );
}

function StatBadge({ icon, label, value, color }: { icon: string; label: string; value: number; color: string }) {
  const colorClass = {
    cyan: 'text-terminal-cyan',
    green: 'text-terminal-green',
    yellow: 'text-terminal-yellow'
  }[color] || 'text-terminal-text';

  return (
    <div className="flex items-center gap-1.5">
      <span>{icon}</span>
      <span className="text-terminal-text-muted">{label}:</span>
      <span className={`font-semibold ${colorClass}`}>{value}</span>
    </div>
  );
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  return days[date.getDay()];
}

function formatFullDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric' 
  });
}
