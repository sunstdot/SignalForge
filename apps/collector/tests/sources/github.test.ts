import { describe, it, expect } from 'vitest';
import { fetchGitHubTrending } from '../../src/sources/github';

describe('fetchGitHubTrending', () => {
  it('should fetch trending repos', async () => {
    const repos = await fetchGitHubTrending({
      languages: ['typescript', 'python'],
      timeRange: 'weekly'
    });

    expect(repos.length).toBeGreaterThan(0);

    const repo = repos[0];
    expect(repo).toHaveProperty('id');
    expect(repo).toHaveProperty('title');
    expect(repo).toHaveProperty('url');
    expect(repo.sourceType).toBe('repo');
    expect(repo.source).toBe('GitHub');
  });
});
