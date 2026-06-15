import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.last30days_importer import parse_last30days_markdown

SAMPLE = """# last30days v3.3.2: Loop Engineering
- Date range: 2026-05-13 to 2026-06-12
- Sources: 2 active (Reddit, X)
## Ranked Evidence Clusters
### 1. Loop engineering takes over (score 58, 2 items, sources: Reddit, X)
1. [x] You should design loops that prompt your agents
   - 2026-06-10 | @DataScienceDojo | [54likes, 9rt] | score:58
   - URL: https://x.com/DataScienceDojo/status/2064739436395434269
   - Evidence: You shouldn't be prompting coding agents anymore.
2. [reddit] Is loop engineering just cron?
   - 2026-06-11 | r/singularity | [396upvotes] | score:50
   - URL: https://www.reddit.com/r/singularity/comments/abc/
   - Evidence: This is just a workflow that runs on a schedule.
### 2. Token cost worries (score 30, 1 item, sources: Hacker News)
1. [hackernews] Running loops overnight burns tokens
   - 2026-06-05 | dang | [120points] | score:30
   - URL: https://news.ycombinator.com/item?id=999
   - Evidence: Token usage can be orders of magnitude higher.
"""


class ParseTest(unittest.TestCase):
    def test_parses_all_items_with_fields(self):
        items = parse_last30days_markdown(SAMPLE)
        self.assertEqual(len(items), 3)

        x = items[0]
        self.assertEqual(x["source_type"], "x")
        self.assertEqual(x["source"], "X")
        self.assertEqual(x["title"], "You should design loops that prompt your agents")
        self.assertEqual(x["url"], "https://x.com/DataScienceDojo/status/2064739436395434269")
        self.assertEqual(x["date"], "2026-06-10")
        self.assertEqual(x["created_at"], "2026-06-10")
        self.assertTrue(x["summary"].startswith("You shouldn't"))
        self.assertEqual(x["relevance_score"], 10)  # min(10, round(58/6))
        self.assertEqual(x["tags"], ["Loop Engineering"])
        self.assertEqual(x["metadata"]["origin"], "last30days")
        self.assertEqual(x["metadata"]["cluster_score"], 58)
        self.assertTrue(x["id"].startswith("l30-x-"))

    def test_platform_mapping_hackernews_to_hn(self):
        items = parse_last30days_markdown(SAMPLE)
        hn = items[2]
        self.assertEqual(hn["source_type"], "hn")
        self.assertEqual(hn["source"], "Hacker News")
        self.assertEqual(hn["relevance_score"], 5)  # min(10, round(30/6))


if __name__ == "__main__":
    unittest.main()
