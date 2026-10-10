import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.last30days_brief import aggregate_brief, synthesize_narrative, build_brief, _load_topic_items, brief_slug


def _item(st, title, score, date, author, vol, eng):
    return {
        "id": f"id-{title}", "source_type": st, "source": st.upper(),
        "title": title, "summary": f"summary of {title}", "url": f"https://x/{title}",
        "relevance_score": score, "date": date, "created_at": date,
        "tags": ["Loop Engineering"],
        "metadata": {"author": author, "engagement": eng, "volume": vol,
                     "topic": "Loop Engineering", "origin": "last30days"},
    }


ITEMS = [
    _item("x", "T1", 10, "2026-06-10", "@a", 63, "54likes, 9rt"),
    _item("reddit", "T2", 5, "2026-06-11", "r/sing", 396, "396upvotes"),
    _item("hn", "T3", 8, "2026-06-10", "dang", 120, "120points"),
]


class AggregateBriefTest(unittest.TestCase):
    def test_meta_counts(self):
        b = aggregate_brief(ITEMS, "Loop Engineering")
        self.assertEqual(b["meta"]["total"], 3)
        self.assertEqual(b["meta"]["platforms"]["x"], 1)
        self.assertEqual(b["meta"]["platforms"]["reddit"], 1)
        self.assertEqual(b["meta"]["platforms"]["hn"], 1)
        self.assertEqual(b["meta"]["featured"], 2)  # score>=8: T1(10), T3(8)

    def test_dashboard_volume(self):
        b = aggregate_brief(ITEMS, "Loop Engineering")
        self.assertEqual(b["dashboard"]["volumeTotal"], "579")  # 63+396+120
        self.assertEqual(b["dashboard"]["volume"][0]["p"], "reddit")  # highest volume

    def test_voices_sorted_by_volume(self):
        b = aggregate_brief(ITEMS, "Loop Engineering")
        self.assertEqual(b["voices"][0], "r/sing")

    def test_timeline_grouped_and_sorted(self):
        b = aggregate_brief(ITEMS, "Loop Engineering")
        # newest day first
        self.assertEqual(b["timeline"][0]["items"][0]["p"], "reddit")  # 2026-06-11
        # within 2026-06-10, higher score first → x(10) before hn(8)
        day2 = b["timeline"][1]["items"]
        self.assertEqual(day2[0]["who"], "@a")
        self.assertEqual(day2[0]["stat"], "54likes, 9rt")
        self.assertTrue(day2[0]["feat"])

    def test_caveat_flags_missing_video_platforms(self):
        b = aggregate_brief(ITEMS, "Loop Engineering")
        self.assertIn("YouTube", b["caveat"])


class SynthesizeTest(unittest.TestCase):
    def test_valid_llm_json_maps_fields(self):
        payload = (
            '{"headline":"H","kicker":"K","lede":"L",'
            '"consensus":{"left":60,"right":40,"leftLabel":"a","leftSub":"a2","rightLabel":"b","rightSub":"b2"},'
            '"themes":[{"n":"01","title":"t","html":"h"}],'
            '"patterns":[{"n":1,"text":"p","src":"@s","lead":true}],'
            '"deepDive":[{"k":"A","q":"q","a":"a"}],'
            '"insight":"ins","reasons":{"id-T1":"because"}}'
        )
        with patch("services.last30days_brief.chat", return_value=payload):
            n = synthesize_narrative(ITEMS, "Loop Engineering")
        self.assertEqual(n["headline"], "H")
        self.assertEqual(n["consensus"]["left"], 60)
        self.assertEqual(n["reasons"]["id-T1"], "because")

    def test_bad_json_degrades_without_raising(self):
        with patch("services.last30days_brief.chat", return_value="not json"):
            n = synthesize_narrative(ITEMS, "Loop Engineering")
        self.assertEqual(n, {})

    def test_tolerates_trailing_commas(self):
        payload = '{"headline":"H","themes":[{"n":"01","title":"t","html":"h"},],}'
        with patch("services.last30days_brief.chat", return_value=payload):
            n = synthesize_narrative(ITEMS, "Loop Engineering")
        self.assertEqual(n["headline"], "H")
        self.assertEqual(len(n["themes"]), 1)


class BuildBriefTest(unittest.TestCase):
    def test_build_merges_aggregate_and_narrative(self):
        import services.last30days_brief as mod
        narrative = {
            "headline": "Big Headline",
            "consensus": {"left": 70, "right": 30, "leftLabel": "x", "leftSub": "", "rightLabel": "y", "rightSub": ""},
            "themes": [{"n": "01", "title": "t", "html": "h"}],
            "reasons": {"id-T1": "key reason"},
            "insight": "the insight",
        }
        with patch.object(mod, "_load_topic_items", return_value=ITEMS):
            with patch.object(mod, "synthesize_narrative", return_value=narrative):
                b = mod.build_brief("Loop Engineering", persist=False)
        self.assertEqual(b["headline"], "Big Headline")
        self.assertEqual(b["consensus"]["left"], 70)
        self.assertEqual(b["themes"][0]["title"], "t")
        self.assertEqual(b["dashboard"]["insight"], "the insight")
        # per-item reason merged into timeline
        t1 = next(it for g in b["timeline"] for it in g["items"] if it["title"] == "T1")
        self.assertEqual(t1["reason"], "key reason")


class HistoryTest(unittest.TestCase):
    def test_record_dedups_and_orders_newest_first(self):
        import tempfile
        import services.last30days_brief as mod
        with tempfile.TemporaryDirectory() as d:
            with patch.object(mod, "HISTORY_FILE", Path(d) / "history.json"):
                mod.record_history("Loop Engineering", "loop-engineering", 5)
                mod.record_history("Agents", "agents", 3)
                mod.record_history("Loop Engineering", "loop-engineering", 7)  # re-search
                hist = mod.load_history()
        self.assertEqual([h["slug"] for h in hist], ["loop-engineering", "agents"])
        self.assertEqual(hist[0]["total"], 7)  # updated count, deduped

    def test_record_dedups_same_topic_when_slug_changes(self):
        import tempfile
        import services.last30days_brief as mod
        with tempfile.TemporaryDirectory() as d:
            with patch.object(mod, "HISTORY_FILE", Path(d) / "history.json"):
                mod.record_history("openAI相关的信息", "openai", 0)
                mod.record_history("openAI相关的信息", "openai-b3dc6240", 16)
                hist = mod.load_history()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["slug"], "openai-b3dc6240")
        self.assertEqual(hist[0]["total"], 16)

    def test_load_history_empty_when_missing(self):
        import tempfile
        import services.last30days_brief as mod
        with tempfile.TemporaryDirectory() as d:
            with patch.object(mod, "HISTORY_FILE", Path(d) / "nope.json"):
                self.assertEqual(mod.load_history(), [])


class BriefFileTest(unittest.TestCase):
    def test_build_persists_file_and_load_reads_it(self):
        import tempfile
        import services.last30days_brief as mod
        from services.last30days_brief import brief_slug, load_brief
        with tempfile.TemporaryDirectory() as d:
            with patch.object(mod, "BRIEFS_DIR", Path(d)), \
                 patch.object(mod, "HISTORY_FILE", Path(d) / "history.json"), \
                 patch.object(mod, "_load_topic_items", return_value=ITEMS), \
                 patch.object(mod, "synthesize_narrative", return_value={}):
                mod.build_brief("Loop Engineering")  # persist=True default
                slug = brief_slug("Loop Engineering")
                self.assertTrue(slug.startswith("loop-engineering-"))
                self.assertTrue((Path(d) / f"{slug}.json").exists())
                loaded = load_brief(slug)
                self.assertEqual(loaded["meta"]["total"], 3)
        # missing slug → None
        with patch.object(mod, "BRIEFS_DIR", Path(d)):
            self.assertIsNone(load_brief("loop-engineering"))


class LoadTopicItemsTest(unittest.TestCase):
    def test_finds_topic_items_beyond_default_content_page(self):
        distractors = [
            {
                "title": f"Other item {i}",
                "tags": ["Other"],
                "metadata": {"origin": "last30days", "topic": "Other"},
            }
            for i in range(600)
        ]
        target = {
            "title": "OpenAI chip discussion",
            "tags": ["OpenAI"],
            "metadata": {"origin": "last30days", "topic": "OpenAI"},
        }
        all_items = distractors + [target]

        def fake_get_content_items(limit):
            return all_items[:limit]

        with patch("services.last30days_brief.get_content_items", side_effect=fake_get_content_items):
            items = _load_topic_items("OpenAI")

        self.assertEqual(items, [target])

    def test_matches_named_entity_inside_descriptive_query(self):
        target = {
            "title": "OpenAI chip discussion",
            "tags": ["OpenAI"],
            "metadata": {"origin": "last30days", "topic": "OpenAI"},
        }

        with patch("services.last30days_brief.get_content_items", return_value=[target]):
            items = _load_topic_items("openAI相关的信息")

        self.assertEqual(items, [target])

    def test_descriptive_query_token_does_not_match_unrelated_titles(self):
        unrelated = {
            "title": "Peter Steinberger joins OpenAI",
            "tags": ["Peter Steinberger"],
            "metadata": {"origin": "last30days", "topic": "Peter Steinberger"},
        }

        with patch("services.last30days_brief.get_content_items", return_value=[unrelated]):
            items = _load_topic_items("openAI相关的信息")

        self.assertEqual(items, [])


class SlugTest(unittest.TestCase):
    def test_slug_keeps_readable_prefix_and_hashes_original_topic(self):
        self.assertRegex(brief_slug("OpenAI"), r"^openai-[0-9a-f]{8}$")
        self.assertRegex(brief_slug("openAI相关的信息"), r"^openai-[0-9a-f]{8}$")
        self.assertRegex(brief_slug("大模型推理成本"), r"^topic-[0-9a-f]{8}$")

    def test_slug_distinguishes_mixed_and_plain_topics(self):
        self.assertNotEqual(brief_slug("OpenAI"), brief_slug("openAI相关的信息"))


if __name__ == "__main__":
    unittest.main()
