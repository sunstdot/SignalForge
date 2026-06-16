import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.last30days_importer import parse_last30days_markdown, import_last30days_file, import_last30days_dir

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

    def test_captures_author_engagement_volume(self):
        items = parse_last30days_markdown(SAMPLE)
        x, reddit, hn = items
        self.assertEqual(x["metadata"]["author"], "@DataScienceDojo")
        self.assertEqual(x["metadata"]["engagement"], "54likes, 9rt")
        self.assertEqual(x["metadata"]["volume"], 63)  # 54 + 9
        self.assertEqual(reddit["metadata"]["author"], "r/singularity")
        self.assertEqual(reddit["metadata"]["volume"], 396)
        self.assertEqual(hn["metadata"]["author"], "dang")
        self.assertEqual(hn["metadata"]["volume"], 120)

    def test_youtube_author_from_dict_and_views_volume(self):
        md = """# last30days v3.3.2: Loop Engineering
- Date range: 2026-05-13 to 2026-06-12
## Ranked Evidence Clusters
### 1. Clip (score 40, 1 item, sources: Youtube)
1. [youtube] How OpenClaw's creator runs his life
   - 2026-06-02 | {'id': 'UC1', 'title': 'Peter Yang', 'handle': 'PeterYangYT'} | [155,769views, 3,260likes, 106cmt] | score:40
   - URL: https://youtube.com/watch?v=abc
   - Evidence: clip
"""
        it = parse_last30days_markdown(md)[0]
        self.assertEqual(it["metadata"]["author"], "@PeterYangYT")
        self.assertEqual(it["metadata"]["volume"], 159135)  # 155769 + 3260 + 106

    def test_date_unknown_falls_back_to_range_end(self):
        md = SAMPLE.replace(
            "   - 2026-06-10 | @DataScienceDojo | [54likes, 9rt] | score:58",
            "   - date unknown [date:low] | meta | score:58",
        )
        items = parse_last30days_markdown(md)
        self.assertEqual(items[0]["date"], "2026-06-12")
        self.assertEqual(items[0]["created_at"], "2026-06-12")

    def test_multiline_cluster_uses_item_score(self):
        md = """# last30days v3.3.2: Loop Engineering
- Date range: 2026-05-13 to 2026-06-12
## Ranked Evidence Clusters
### 3. "Stop prompting coding agents. Start designing loops."

Most devs are still stuck in:

Prompt -> Wait -> Review (score 56, 1 item, sources: X)
- Uncertainty: single-source
1. [x] Stop prompting coding agents
   - 2026-06-11 | @_princegupta13 | [1likes] | score:56
   - URL: https://x.com/_princegupta13/status/2065181758254203283
   - Evidence: Loop engineering is the main quest.
"""
        items = parse_last30days_markdown(md)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["relevance_score"], 9)  # min(10, round(56/6))
        self.assertEqual(items[0]["date"], "2026-06-11")


class ImportFileTest(unittest.TestCase):
    def test_file_parses_and_stores(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(SAMPLE)
            path = f.name
        captured = {}
        def fake_store(items):
            captured["items"] = items
            return len(items)
        with patch("services.last30days_importer.store_content_items", side_effect=fake_store):
            n = import_last30days_file(path)
        self.assertEqual(n, 3)
        self.assertEqual(len(captured["items"]), 3)

    def test_dir_imports_all_md(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.md").write_text(SAMPLE, encoding="utf-8")
            (Path(d) / "b.md").write_text(SAMPLE, encoding="utf-8")
            with patch("services.last30days_importer.store_content_items",
                       side_effect=lambda items: len(items)):
                n = import_last30days_dir(d)
        self.assertEqual(n, 6)


class WingsbotTriggerTest(unittest.TestCase):
    def test_run_imports_newest_report(self):
        # 不真正联网：打桩 _trigger_wingsbot 返回一个临时报告文件
        from services import last30days_importer as mod
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(SAMPLE)
            path = Path(f.name)
        with patch.object(mod, "_trigger_wingsbot", return_value=path):
            with patch("services.last30days_importer.store_content_items",
                       side_effect=lambda items: len(items)):
                n = mod.run_last30days_via_wingsbot("Loop Engineering")
        self.assertEqual(n, 3)

    def test_newest_report_since_picks_latest(self):
        from services import last30days_importer as mod
        import time
        with tempfile.TemporaryDirectory() as d:
            old = Path(d) / "old.md"; old.write_text("x", encoding="utf-8")
            time.sleep(0.01)
            start = time.time()
            time.sleep(0.01)
            new = Path(d) / "new.md"; new.write_text("y", encoding="utf-8")
            with patch.object(mod, "L30_OUTPUT_DIR", Path(d)):
                picked = mod._newest_report_since(start)
        self.assertEqual(picked.name, "new.md")


class RunAsyncCleanTest(unittest.TestCase):
    def test_returns_value(self):
        import asyncio
        from services.last30days_importer import _run_async_clean

        async def c():
            return 7

        self.assertEqual(_run_async_clean(c()), 7)

    def test_subprocess_no_event_loop_closed_noise(self):
        """跑一个会 spawn 子进程的协程，确认 loop 关闭前 transport 已被终结，
        不再出现 'Event loop is closed' 的 __del__ 噪音。"""
        import asyncio
        import gc
        from services.last30days_importer import _run_async_clean

        async def c():
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c", "pass",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return "done"

        unraisable = []
        old_hook = sys.unraisablehook
        sys.unraisablehook = lambda arg: unraisable.append(arg)
        try:
            result = _run_async_clean(c())
            gc.collect()  # 若有 transport 漏到 loop 关闭后，这里会触发噪音
        finally:
            sys.unraisablehook = old_hook

        self.assertEqual(result, "done")
        leaked = [
            u for u in unraisable
            if isinstance(getattr(u, "exc_value", None), RuntimeError)
            and "Event loop is closed" in str(u.exc_value)
        ]
        self.assertEqual(leaked, [], f"event-loop-closed noise leaked: {leaked}")


if __name__ == "__main__":
    unittest.main()
