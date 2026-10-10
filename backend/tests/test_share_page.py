import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend.services.share_page import build_share_payload, generate_share_page, render_share_page_html
from backend.services.social_cover import build_xiaohongshu_cover_html, generate_xiaohongshu_cover


class SharePayloadTest(unittest.TestCase):
    def test_build_share_payload_selects_top_opportunities_and_diverse_briefings(self):
        opportunities = [
            {"opportunity_title": "Low", "total_score": 10, "core_insight": "low", "product_form": "low"},
            {"opportunity_title": "Top A", "total_score": 18, "core_insight": "a", "product_form": "a"},
            {"opportunity_title": "Top B", "total_score": 17, "core_insight": "b", "product_form": "b"},
            {"opportunity_title": "Top C", "total_score": 16, "core_insight": "c", "product_form": "c"},
        ]
        items = [
            {"id": "repo-1", "title": "Repo 1", "source": "GitHub", "source_type": "repo", "relevance_score": 9},
            {"id": "repo-2", "title": "Repo 2", "source": "GitHub", "source_type": "repo", "relevance_score": 8},
            {"id": "paper-1", "title": "Paper 1", "source": "HF", "source_type": "paper", "relevance_score": 8},
            {"id": "blog-1", "title": "Blog 1", "source": "OpenAI", "source_type": "blog", "relevance_score": 8},
            {"id": "model-1", "title": "Model 1", "source": "HF", "source_type": "model", "relevance_score": 8},
            {"id": "wechat-1", "title": "Wechat 1", "source": "WX", "source_type": "wechat", "relevance_score": 8},
        ]
        quick_reads = {item["id"]: f"quick-{item['id']}" for item in items}

        payload = build_share_payload("2026-05-14", opportunities, items, quick_reads)

        self.assertEqual([i["title"] for i in payload["opportunities"]], ["Top A", "Top B", "Top C"])
        self.assertEqual(
            [i["id"] for i in payload["briefings"]],
            ["repo-1", "paper-1", "blog-1", "model-1", "wechat-1"],
        )
        self.assertEqual(payload["briefings"][0]["quick_read"], "quick-repo-1")

    def test_build_share_payload_skips_items_without_quick_reads(self):
        payload = build_share_payload(
            "2026-05-14",
            [],
            [
                {"id": "repo-1", "title": "Repo 1", "source": "GitHub", "source_type": "repo", "relevance_score": 9},
                {"id": "paper-1", "title": "Paper 1", "source": "HF", "source_type": "paper", "relevance_score": 8},
            ],
            {"paper-1": "paper quick"},
        )

        self.assertEqual([i["id"] for i in payload["briefings"]], ["paper-1"])


class ShareRenderTest(unittest.TestCase):
    def test_render_share_page_html_builds_three_pages(self):
        payload = {
            "date": "2026-05-14",
            "opportunities": [
                {"title": "A", "score": 18, "summary": "alpha"},
                {"title": "B", "score": 17, "summary": "beta"},
                {"title": "C", "score": 16, "summary": "gamma"},
            ],
            "briefings": [
                {"id": f"i-{n}", "title": f"Item {n}", "source_type": "repo", "quick_read": f"quick {n}"}
                for n in range(1, 6)
            ],
        }

        html = render_share_page_html(payload)

        self.assertEqual(html.count('class="xhs-page'), 3)
        self.assertIn("今天最值得看的 3 个 AI 商业机会", html)
        self.assertIn("今天值得继续跟踪的 AI 情报 01", html)
        self.assertIn("今天值得继续跟踪的 AI 情报 02", html)
        self.assertIn("quick 5", html)


class ShareGenerationTest(unittest.TestCase):
    def test_generate_share_page_writes_html_file(self):
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "2026-05-14.html"
            with patch("backend.services.share_page._load_share_sources") as load_sources:
                load_sources.return_value = (
                    [{"opportunity_title": "A", "total_score": 18, "product_form": "alpha"}],
                    [{"id": "repo-1", "title": "Repo", "source": "GitHub", "source_type": "repo", "relevance_score": 9}],
                    {"repo-1": "**核心内容**：quick"},
                )

                generated = generate_share_page("2026-05-14", output_path)

            self.assertEqual(generated, output_path)
            self.assertTrue(output_path.exists())
            self.assertIn("今天最值得看的 3 个 AI 商业机会", output_path.read_text())


class XiaohongshuCoverTest(unittest.TestCase):
    def test_build_xiaohongshu_cover_html_uses_payload_story(self):
        payload = {
            "date": "2026-05-14",
            "opportunities": [
                {
                    "title": "AI 代码评审助手",
                    "score": 18,
                    "core_insight": "团队需要更快发现 Pull Request 风险",
                    "product_form": "浏览器插件 + GitHub Bot",
                }
            ],
            "briefings": [
                {"title": "OpenAI 发布新模型", "source_type": "model", "quick_read": "quick"}
            ],
        }

        html = build_xiaohongshu_cover_html(payload)

        self.assertIn('id="xhs-cover"', html)
        self.assertIn("AI 代码评审助手", html)
        self.assertIn("团队需要更快发现 Pull Request 风险", html)
        self.assertIn("2026-05-14", html)
        self.assertIn("1080px", html)
        self.assertIn("1440px", html)

    def test_generate_xiaohongshu_cover_writes_html_next_to_png_and_renders(self):
        payload = {
            "date": "2026-05-14",
            "opportunities": [{"title": "A", "score": 18}],
            "briefings": [],
        }

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "2026-05-14-cover.png"
            with patch("backend.services.social_cover.subprocess.run") as run:
                generated = generate_xiaohongshu_cover(payload, output_path)

            self.assertEqual(generated, output_path)
            html_path = Path(tmpdir) / "2026-05-14-cover.html"
            self.assertTrue(html_path.exists())
            self.assertIn("A", html_path.read_text(encoding="utf-8"))
            run.assert_called_once()
            command = run.call_args.args[0]
            self.assertEqual(command[0], "node")
            self.assertEqual(Path(command[1]).name, "render_social_cover.mjs")
            self.assertEqual(command[-2:], [str(html_path), str(output_path)])
