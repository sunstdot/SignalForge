export type NewsItem = {
  title: string;
  summary: string;
  whyImportant: string;
  opportunity: string;
  tags: string[];
  visualHint: string;
};

export type AiNewsData = {
  meta: {
    date: string;
    title: string;
    durationSeconds: number;
    source: string;
  };
  opening: {
    hook: string;
    subtitle: string;
  };
  items: NewsItem[];
  ending: {
    insight: string;
    cta: string;
  };
};
