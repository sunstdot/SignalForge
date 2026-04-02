'use client';

import { useState, useEffect, useMemo } from 'react';
import { useParams } from 'next/navigation';
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
  const dateParam = params.date as string;
  
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [dates, setDates] = useState<DateInfo[]>([]);
  const [activeCategory, setActiveCategory] = useState<CategoryType>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [dateParam]);

  async function fetchData() {
    setLoading(true);
    try {
      const briefingRes = await fetch(`/api/briefing?date=${dateParam}`);
      const briefingData = await briefingRes.json();
      setBriefing(briefingData.briefing);

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
        <div className="flex items-center gap-2 text-[var(--text-muted)]">
          <span className="loading-pulse">▌</span>
          <span className="text-sm">加载中...</span>
        </div>
      </div>
    );
  }

  if (!briefing) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center">
          <div className="window-dots justify-center mb-4">
            <span className="window-dot window-dot-red" />
            <span className="window-dot window-dot-yellow" />
            <span className="window-dot window-dot-green" />
          </div>
          <h2 className="text-lg font-semibold mb-2">暂无简报</h2>
          <p className="text-sm text-[var(--text-muted)]">请先运行 collector 生成简报</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Sidebar - Fixed */}
      <aside className="w-64 flex-shrink-0 border-r border-[var(--border)] bg-[var(--bg-secondary)] fixed left-0 top-0 bottom-0 overflow-y-auto">
        {/* Header */}
        <div className="p-4 border-b border-[var(--border)] bg-[var(--bg-primary)]">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[var(--accent-blue)]">◈</span>
            <span className="font-semibold text-[var(--text-primary)]">TokenBurner</span>
          </div>
          <div className="text-xs text-[var(--text-muted)]">
            AI Intelligence Hub
          </div>
        </div>
        
        {/* Date Navigation */}
        <div className="p-3">
          <div className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider mb-2 px-2">
            Archives
          </div>
          <nav className="space-y-1">
            {dates.map((d) => (
              <Link
                key={d.date}
                href={`/briefing/${d.date}`}
                className={`date-nav-item ${d.date === dateParam ? 'active' : ''}`}
              >
                <span className="font-mono">{d.date}</span>
                <span className="ml-2 text-[var(--text-muted)] text-xs">{d.formattedDate}</span>
              </Link>
            ))}
          </nav>
        </div>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-[var(--border)] bg-[var(--bg-secondary)]">
          <div className="text-xs text-[var(--text-muted)]">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[var(--accent-green)]" />
              System Online
            </div>
            <div className="mt-1 text-[10px]">
              v1.0.0 · {dates.length} archives
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content - Scrollable */}
      <main className="flex-1 ml-64">
        {/* Top Bar */}
        <header className="sticky top-0 z-20 bg-[var(--bg-primary)] border-b border-[var(--border)]">
          {/* Window Controls Bar */}
          <div className="px-4 py-3 flex items-center gap-4">
            <div className="window-dots">
              <span className="window-dot window-dot-red" />
              <span className="window-dot window-dot-yellow" />
              <span className="window-dot window-dot-green" />
            </div>
            
            <div className="flex-1 flex items-center justify-between">
              {/* Breadcrumb */}
              <div className="flex items-center gap-2 text-sm">
                <Link href="/" className="text-[var(--text-muted)] hover:text-[var(--text-primary)]">
                  TokenBurner
                </Link>
                <span className="text-[var(--text-muted)]">/</span>
                <Link 
                  href={`/briefing/${briefing.date}`}
                  className="text-[var(--accent-blue)] font-medium"
                >
                  {briefing.date}
                </Link>
              </div>

              {/* Stats */}
              <div className="flex items-center gap-2">
                <div className="stat-item">
                  <span>📄</span>
                  <span className="text-[var(--text-muted)]">论文</span>
                  <span className="font-medium text-[var(--paper-color)]">{stats.paper}</span>
                </div>
                <div className="stat-item">
                  <span>🛠️</span>
                  <span className="text-[var(--text-muted)]">仓库</span>
                  <span className="font-medium text-[var(--repo-color)]">{stats.repo}</span>
                </div>
                <div className="stat-item">
                  <span>📰</span>
                  <span className="text-[var(--text-muted)]">新闻</span>
                  <span className="font-medium text-[var(--news-color)]">{stats.news}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Category Tabs */}
          <div className="px-4 pb-3">
            <div className="flex gap-1">
              {CATEGORY_TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveCategory(tab.key)}
                  className={`tab-btn ${activeCategory === tab.key ? 'active' : ''}`}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="p-6 max-w-4xl">
          {/* Summary */}
          {briefing.summary && (
            <section className="mb-6">
              <div className="summary-box">
                <div className="markdown-content">
                  <ReactMarkdown>{briefing.summary}</ReactMarkdown>
                </div>
              </div>
            </section>
          )}

          {/* Items */}
          <section className="space-y-4">
            {filteredItems.length === 0 ? (
              <div className="text-center py-12 text-[var(--text-muted)]">
                <span className="text-3xl block mb-2">∅</span>
                <p className="text-sm">该分类下暂无内容</p>
              </div>
            ) : (
              filteredItems.map((item, index) => (
                <ContentCard key={item.id} item={item} />
              ))
            )}
          </section>

          {/* Footer */}
          <footer className="mt-8 pt-4 border-t border-[var(--border)] text-xs text-[var(--text-muted)]">
            <div className="flex items-center justify-between">
              <span>TokenBurner Intelligence Hub</span>
              <span>Generated: {new Date(briefing.generatedAt).toLocaleString()}</span>
            </div>
          </footer>
        </div>
      </main>
    </div>
  );
}

function ContentCard({ item }: { item: ContentItem }) {
  const badgeClass = {
    paper: 'badge-paper',
    repo: 'badge-repo',
    news: 'badge-news',
    tweet: 'badge-news',
    podcast: 'badge-news',
    rss: 'badge-news'
  }[item.sourceType] || 'badge-news';

  const typeLabel = SOURCE_TYPE_MAP[item.sourceType] || item.sourceType;

  return (
    <article className="content-card">
      <div className="card-header">
        <span className={`card-badge ${badgeClass}`}>
          {typeLabel}
        </span>
        <span className="text-xs text-[var(--text-muted)] ml-auto">
          {item.source}
        </span>
      </div>
      
      <div className="p-4">
        {/* Title */}
        <h3 className="text-base font-semibold mb-3">
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--text-primary)] hover:text-[var(--accent-blue)] transition-colors"
          >
            {item.title}
          </a>
        </h3>

        {/* Summary */}
        {item.summary && (
          <div className="markdown-content text-sm mb-4">
            <ReactMarkdown>{item.summary}</ReactMarkdown>
          </div>
        )}

        {/* Insights */}
        {item.insights && item.insights.length > 0 && (
          <div className="insights-list">
            <div className="insights-title">核心见解</div>
            {item.insights.map((insight, idx) => (
              <div key={idx} className="insight-item">
                <span className="insight-bullet">›</span>
                <span>{insight}</span>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="flex flex-wrap items-center gap-2 mt-4 pt-3 border-t border-[var(--border-light)]">
          <span className="relevance-badge">
            相关度: {item.relevanceScore}/10
          </span>
          
          {item.category.slice(0, 4).map((cat) => (
            <span key={cat} className="tag">
              {cat}
            </span>
          ))}
        </div>
      </div>
    </article>
  );
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  return days[date.getDay()];
}
