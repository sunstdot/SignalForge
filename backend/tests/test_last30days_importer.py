import sys
import importlib
import json
import unittest
import tempfile
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Replace only the client boundary while importing the unit under test. This
# keeps collection working without installing Wingsbot and cannot leak a fake
# top-level ``wingsbot`` package into other tests.
client_module = types.ModuleType("services.wingsbot_client")
client_module.invoke_wingsbot = lambda *args, **kwargs: None
client_module.require_artifact = lambda *args, **kwargs: None
with patch.dict(
    sys.modules,
    {"services.wingsbot_client": client_module},
):
    importer = importlib.import_module("services.last30days_importer")

parse_last30days_json = importer.parse_last30days_json
import_last30days_file = importer.import_last30days_file
import_last30days_dir = importer.import_last30days_dir
_format_engagement = importer._format_engagement
_sum_engagement = importer._sum_engagement
_normalize_score = importer._normalize_score
_parse_date = importer._parse_date
sys.modules.pop("services.last30days_importer", None)

# 真实结构的精简样例（对应 schema.Report）
SAMPLE_REPORT = {
    "topic": "Loop Engineering",
    "range_from": "2026-05-13",
    "range_to": "2026-06-12",
    "generated_at": "2026-06-12T10:00:00Z",
    "clusters": [
        {
            "cluster_id": "cluster-1",
            "title": "Loop engineering takes over",
            "candidate_ids": ["c1", "c2"],
            "representative_ids": ["c1"],
            "sources": ["x", "reddit"],
            "score": 58,
        },
        {
            "cluster_id": "cluster-2",
            "title": "Token cost worries",
            "candidate_ids": ["c3"],
            "representative_ids": ["c3"],
            "sources": ["hackernews"],
            "score": 30,
        },
    ],
    "ranked_candidates": [
        {
            "candidate_id": "https://x.com/DataScienceDojo/status/2064739436395434269",
            "item_id": "X1",
            "source": "x",
            "title": "You should design loops that prompt your agents",
            "url": "https://x.com/DataScienceDojo/status/2064739436395434269",
            "snippet": "You shouldn't be prompting coding agents anymore.",
            "final_score": 43.4,
            "rerank_score": 39.4,
            "cluster_id": "cluster-1",
            "explanation": "fallback-local-score",
            "source_items": [
                {
                    "item_id": "X1",
                    "source": "x",
                    "author": "DataScienceDojo",
                    "body": "You shouldn't be prompting coding agents anymore.",
                    "published_at": "2026-06-10T12:00:00Z",
                    "engagement": {"likes": 54, "replies": 9, "reposts": 0},
                }
            ],
        },
        {
            "candidate_id": "https://www.reddit.com/r/singularity/comments/abc/",
            "item_id": "R1",
            "source": "reddit",
            "title": "Is loop engineering just cron?",
            "url": "https://www.reddit.com/r/singularity/comments/abc/",
            "snippet": "This is just a workflow that runs on a schedule.",
            "final_score": 35.0,
            "rerank_score": 30.0,
            "cluster_id": "cluster-1",
            "source_items": [
                {
                    "item_id": "R1",
                    "source": "reddit",
                    "author": "r/singularity",
                    "body": "This is just a workflow that runs on a schedule.",
                    "published_at": "2026-06-11",
                    "engagement": {"upvotes": 396},
                }
            ],
        },
        {
            "candidate_id": "https://news.ycombinator.com/item?id=999",
            "item_id": "H1",
            "source": "hackernews",
            "title": "Running loops overnight burns tokens",
            "url": "https://news.ycombinator.com/item?id=999",
            "snippet": "Token usage can be orders of magnitude higher.",
            "final_score": 28.0,
            "rerank_score": 25.0,
            "cluster_id": "cluster-2",
            "source_items": [
                {
                    "item_id": "H1",
                    "source": "hackernews",
                    "author": "dang",
                    "body": "Token usage can be orders of magnitude higher.",
                    "published_at": "2026-06-05",
                    "engagement": {"points": 120},
                }
            ],
        },
    ],
    "items_by_source": {},
    "errors_by_source": {},
}


def _report_to_text(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


class ParseTest(unittest.TestCase):
    def test_parses_all_candidates_with_required_fields(self):
        items = parse_last30days_json(_report_to_text(SAMPLE_REPORT))
        self.assertEqual(len(items), 3)

        x = items[0]
        self.assertEqual(x["source_type"], "x")
        self.assertEqual(x["source"], "X")
        self.assertEqual(x["title"], "You should design loops that prompt your agents")
        self.assertEqual(x["url"], "https://x.com/DataScienceDojo/status/2064739436395434269")
        self.assertEqual(x["date"], "2026-06-10")
        self.assertEqual(x["created_at"], "2026-06-10")
        self.assertTrue(x["summary"].startswith("You shouldn't"))
        self.assertTrue(x["id"].startswith("l30-x-"))
        self.assertEqual(x["tags"], ["Loop Engineering"])
        self.assertEqual(x["category"], ["Loop Engineering"])
        self.assertEqual(x["metadata"]["origin"], "last30days")
        self.assertEqual(x["metadata"]["topic"], "Loop Engineering")
        self.assertEqual(x["metadata"]["cluster_id"], "cluster-1")
        self.assertEqual(x["metadata"]["cluster_title"], "Loop engineering takes over")
        self.assertEqual(x["metadata"]["cluster_score"], 58)

    def test_platform_mapping_hackernews_to_hn(self):
        items = parse_last30days_json(_report_to_text(SAMPLE_REPORT))
        hn = items[2]
        self.assertEqual(hn["source_type"], "hn")
        self.assertEqual(hn["source"], "Hacker News")
        self.assertEqual(hn["metadata"]["cluster_score"], 30)

    def test_author_taken_from_primary_source_item(self):
        items = parse_last30days_json(_report_to_text(SAMPLE_REPORT))
        x, reddit, hn = items
        self.assertEqual(x["metadata"]["author"], "DataScienceDojo")
        self.assertEqual(reddit["metadata"]["author"], "r/singularity")
        self.assertEqual(hn["metadata"]["author"], "dang")

    def test_engagement_dict_formatted_as_string_and_volume_summed(self):
        items = parse_last30days_json(_report_to_text(SAMPLE_REPORT))
        x, reddit, hn = items
        # X: {likes:54, replies:9, reposts:0} -> "54 likes, 9 replies, 0 reposts", volume=63
        self.assertEqual(x["metadata"]["engagement"], "54 likes, 9 replies, 0 reposts")
        self.assertEqual(x["metadata"]["volume"], 63)
        # Reddit: {upvotes:396} -> "396 upvotes", volume=396
        self.assertEqual(reddit["metadata"]["engagement"], "396 upvotes")
        self.assertEqual(reddit["metadata"]["volume"], 396)
        # HN: {points:120} -> "120 points", volume=120
        self.assertEqual(hn["metadata"]["engagement"], "120 points")
        self.assertEqual(hn["metadata"]["volume"], 120)

    def test_score_normalized_to_0_10(self):
        items = parse_last30days_json(_report_to_text(SAMPLE_REPORT))
        x, reddit, hn = items
        # final_score 43.4 -> 43.4/5 = 8.68 -> round = 9 (触发 featured >= 8)
        self.assertEqual(x["relevance_score"], 9)
        # final_score 35 -> 35/5 = 7.0 -> round = 7
        self.assertEqual(reddit["relevance_score"], 7)
        # final_score 28 -> 28/5 = 5.6 -> round = 6
        self.assertEqual(hn["relevance_score"], 6)

    def test_date_falls_back_to_range_to_when_published_at_missing(self):
        report = json.loads(_report_to_text(SAMPLE_REPORT))
        report["ranked_candidates"][0]["source_items"][0]["published_at"] = None
        items = parse_last30days_json(_report_to_text(report))
        self.assertEqual(items[0]["date"], "2026-06-12")  # range_to
        self.assertEqual(items[0]["created_at"], "2026-06-12")

    def test_empty_ranked_candidates_returns_empty_list(self):
        report = json.loads(_report_to_text(SAMPLE_REPORT))
        report["ranked_candidates"] = []
        items = parse_last30days_json(_report_to_text(report))
        self.assertEqual(items, [])

    def test_invalid_json_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_last30days_json("not a json")


class HelperTest(unittest.TestCase):
    def test_normalize_score_clamps_to_0_10(self):
        self.assertEqual(_normalize_score(0), 0)
        self.assertEqual(_normalize_score(43.4), 9)  # 43.4/5 = 8.68 -> 9
        self.assertEqual(_normalize_score(100), 10)  # 100/5 = 20 -> clamped to 10
        self.assertEqual(_normalize_score(150), 10)  # clamped
        self.assertEqual(_normalize_score(-5), 0)  # clamped
        self.assertEqual(_normalize_score(None), 0)
        self.assertEqual(_normalize_score("not a number"), 0)

    def test_format_engagement_dict(self):
        self.assertEqual(
            _format_engagement({"likes": 54, "replies": 9, "reposts": 0}),
            "54 likes, 9 replies, 0 reposts",
        )
        self.assertEqual(_format_engagement({"upvotes": 396}), "396 upvotes")
        self.assertEqual(_format_engagement({}), "")
        self.assertEqual(_format_engagement(None), "")

    def test_format_engagement_string_passthrough(self):
        self.assertEqual(_format_engagement("54likes, 9rt"), "54likes, 9rt")

    def test_sum_engagement_dict(self):
        self.assertEqual(_sum_engagement({"likes": 54, "replies": 9, "reposts": 0}), 63)
        self.assertEqual(_sum_engagement({"upvotes": 396}), 396)
        self.assertEqual(_sum_engagement({}), 0)
        self.assertEqual(_sum_engagement(None), 0)

    def test_sum_engagement_string_extracts_numbers(self):
        self.assertEqual(_sum_engagement("54likes, 9rt"), 63)
        self.assertEqual(_sum_engagement("1,234 upvotes"), 1234)

    def test_parse_date_handles_iso_and_date_only(self):
        self.assertEqual(_parse_date("2026-06-30"), "2026-06-30")
        self.assertEqual(_parse_date("2026-06-28T10:30:00Z"), "2026-06-28")
        self.assertEqual(_parse_date(None), "")
        self.assertEqual(_parse_date(""), "")
        self.assertEqual(_parse_date("garbage"), "")


class ImportFileTest(unittest.TestCase):
    def test_file_parses_and_stores(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write(_report_to_text(SAMPLE_REPORT))
            path = f.name
        captured = {}

        def fake_store(items):
            captured["items"] = items
            return len(items)

        with patch.object(importer, "store_content_items", side_effect=fake_store):
            n = import_last30days_file(path)
        self.assertEqual(n, 3)
        self.assertEqual(len(captured["items"]), 3)

    def test_dir_imports_all_json(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.json").write_text(_report_to_text(SAMPLE_REPORT), encoding="utf-8")
            (Path(d) / "b.json").write_text(_report_to_text(SAMPLE_REPORT), encoding="utf-8")
            # 非 json 文件应该被忽略
            (Path(d) / "c.md").write_text("should be ignored", encoding="utf-8")
            with patch.object(importer, "store_content_items", side_effect=lambda items: len(items)):
                n = import_last30days_dir(d)
        self.assertEqual(n, 6)


class WingsbotTriggerTest(unittest.TestCase):
    def test_import_does_not_leave_fake_wingsbot_or_importer_modules_installed(self):
        self.assertNotIn("wingsbot.invoke", sys.modules)
        self.assertNotIn("services.last30days_importer", sys.modules)

    def test_run_imports_newest_report(self):
        mod = importer
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write(_report_to_text(SAMPLE_REPORT))
            path = Path(f.name)
        with patch.object(mod, "_trigger_wingsbot", return_value=path):
            with patch.object(mod, "store_content_items", side_effect=lambda items: len(items)):
                n = mod.run_last30days_via_wingsbot("Loop Engineering")
        self.assertEqual(n, 3)

    def test_trigger_invokes_structured_wingsbot_and_returns_validated_artifact(self):
        mod = importer

        artifact = Path("/tmp/last30days/openai.json")
        result = SimpleNamespace(ok=True, artifacts=[artifact], content="done", error=None)
        with patch.object(mod, "invoke_wingsbot", return_value=result) as invoke:
            with patch.object(mod, "require_artifact", return_value=artifact) as require:
                actual = mod._trigger_wingsbot("OpenAI")

        prompt = mod._build_wingsbot_prompt("OpenAI")
        invoke.assert_called_once_with(
            prompt,
            session_key="signalforge:last30days:OpenAI",
            structured=True,
            required_skill="last30days",
            required_tools=["load_skill", "exec"],
            required_artifact_glob=str(mod.L30_OUTPUT_DIR / "*.json"),
            artifact_mtime_after=ANY,
        )
        require.assert_called_once_with(result, mod.L30_OUTPUT_DIR)
        self.assertEqual(actual, artifact)

    def test_wingsbot_prompt_requires_json_emit(self):
        mod = importer

        prompt = mod._build_wingsbot_prompt("OpenAI")

        # 关键：必须用 --emit=json，不能是 md
        self.assertIn("--emit=json", prompt)
        self.assertNotIn("--emit=md", prompt)
        # 必须指定 save-dir 到 L30_OUTPUT_DIR
        self.assertIn(f"--save-dir={mod.L30_OUTPUT_DIR}", prompt)
        # 必须强调"真正调用工具"，不能编造
        self.assertIn("last30days", prompt)
        self.assertIn("不要凭记忆", prompt)
        # 多源检索要求
        self.assertIn("Reddit", prompt)
        self.assertIn("Hacker News", prompt)
        self.assertIn("不能跳过", prompt)
        # 话题要注入
        self.assertIn("OpenAI", prompt)
        # 完整路径要求
        self.assertIn(".json", prompt)

if __name__ == "__main__":
    unittest.main()
