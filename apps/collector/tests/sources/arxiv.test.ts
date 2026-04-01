import { describe, it, expect } from 'vitest';
import { fetchArxivPapers } from '../../src/sources/arxiv';

describe('fetchArxivPapers', () => {
  it('should fetch and parse arXiv papers', async () => {
    const papers = await fetchArxivPapers({
      categories: ['cs.CL', 'cs.AI'],
      maxResults: 5
    });

    expect(papers.length).toBeGreaterThan(0);
    expect(papers.length).toBeLessThanOrEqual(5);

    const paper = papers[0];
    expect(paper).toHaveProperty('id');
    expect(paper).toHaveProperty('title');
    expect(paper).toHaveProperty('url');
    expect(paper.sourceType).toBe('paper');
    expect(paper.source).toBe('arXiv');
  });
});
