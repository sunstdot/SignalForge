import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.content import router


PAPER = {
    "id": "paper-123", "source_type": "paper", "title": "Test Paper",
    "url": "https://arxiv.org/abs/2401.01234", "summary": "A short abstract.",
}
REPORT = "## 一句话贡献\n在给定假设下减少通信。\n\n## 阅读依据\n仅摘要，实验未核实。"


class PaperQuickReadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        app = FastAPI()
        app.include_router(router, prefix="/api/content")
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.data = Path(self.tmp.name)
        self.data_patch = patch("services.storage.DATA_DIR", self.data)
        self.data_patch.start()
        self.addCleanup(self.data_patch.stop)
        self.item_patch = patch("routers.content.get_content_item_by_id", return_value=PAPER.copy())
        self.lookup = self.item_patch.start()
        self.addCleanup(self.item_patch.stop)

    def post(self, **overrides):
        return self.client.post("/api/content/paper-quick-read", json={"item_id": PAPER["id"], **overrides})

    def test_generates_with_required_skill_and_reuses_persistent_cache(self):
        seen = []

        async def invoke(prompt, **kwargs):
            seen.append((prompt, kwargs))
            return SimpleNamespace(ok=True, content=REPORT, error=None)

        with patch("services.wingsbot_client.ainvoke_wingsbot", side_effect=invoke):
            first = self.post()
            self.assertEqual(first.status_code, 200, first.text)
            self.assertEqual(first.json()["summary"], REPORT)
            self.assertFalse(first.json()["cached"])
            second = self.post()
            self.assertEqual(second.json()["summary"], REPORT)
            self.assertTrue(second.json()["cached"])
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][1]["required_skill"], "paper-quick-read")
        self.assertTrue(seen[0][1]["structured"])
        self.assertIn(PAPER["url"], seen[0][0])
        self.assertTrue(list((self.data / "paper_reads").glob("*.json")))
        self.assertFalse((self.data / "quick_reads").exists())

    def test_rejects_unknown_items_and_non_papers(self):
        self.lookup.return_value = None
        self.assertEqual(self.post().status_code, 404)
        self.lookup.return_value = {**PAPER, "source_type": "news"}
        self.assertEqual(self.post().status_code, 400)

    def test_requires_item_id_and_http_url(self):
        self.assertEqual(self.client.post("/api/content/paper-quick-read", json={}).status_code, 422)
        self.lookup.return_value = {**PAPER, "url": "file:///etc/passwd"}
        self.assertEqual(self.post().status_code, 400)

    def test_errors_and_empty_output_are_not_cached_and_can_retry(self):
        for failure in [RuntimeError("provider failed"), SimpleNamespace(ok=False, content="", error="missing skill"), SimpleNamespace(ok=True, content="   ", error=None)]:
            with self.subTest(failure=failure):
                invoke = AsyncMock(side_effect=failure) if isinstance(failure, Exception) else AsyncMock(return_value=failure)
                with patch("services.wingsbot_client.ainvoke_wingsbot", invoke):
                    response = self.post()
                self.assertEqual(response.status_code, 502, response.text)
                self.assertFalse(list((self.data / "paper_reads").glob("*.json")))
        with patch("services.wingsbot_client.ainvoke_wingsbot", AsyncMock(return_value=SimpleNamespace(ok=True, content=REPORT))):
            self.assertEqual(self.post().json()["summary"], REPORT)

    def test_arxiv_is_also_a_paper_and_changed_url_does_not_reuse_stale_cache(self):
        with patch("services.wingsbot_client.ainvoke_wingsbot", AsyncMock(return_value=SimpleNamespace(ok=True, content=REPORT))):
            self.assertEqual(self.post().status_code, 200)
            self.lookup.return_value = {**PAPER, "source_type": "arxiv", "url": "https://arxiv.org/abs/2401.01234v2"}
            result = self.post()
            self.assertEqual(result.status_code, 200)
            self.assertFalse(result.json()["cached"])

    def test_timeout_returns_retryable_error(self):
        with patch("services.wingsbot_client.ainvoke_wingsbot", AsyncMock(side_effect=TimeoutError)):
            response = self.post()
        self.assertEqual(response.status_code, 504)
        self.assertIn("重试", response.json()["detail"])
        self.assertFalse(list((self.data / "paper_reads").glob("*.json")))

    def test_wingsbot_contract_success_with_failure_text_is_not_a_report(self):
        for content in ["达到最大迭代次数，任务可能未完成。已执行：load_skill。", "本轮执行失败，但没有可用的错误详情。"]:
            with self.subTest(content=content):
                with patch("services.wingsbot_client.ainvoke_wingsbot", AsyncMock(return_value=SimpleNamespace(ok=True, content=content))):
                    response = self.post()
                self.assertEqual(response.status_code, 502)
                self.assertFalse(list((self.data / "paper_reads").glob("*.json")))

    def test_concurrent_requests_share_one_generation_even_if_one_caller_leaves(self):
        from services.paper_quick_read import read_paper

        async def scenario():
            started = asyncio.Event()
            finish = asyncio.Event()
            calls = []

            async def invoke(*args, **kwargs):
                calls.append(kwargs)
                started.set()
                await finish.wait()
                return SimpleNamespace(ok=True, content=REPORT)

            with patch("services.wingsbot_client.ainvoke_wingsbot", side_effect=invoke):
                first = asyncio.create_task(read_paper(PAPER))
                await started.wait()
                second = asyncio.create_task(read_paper(PAPER))
                await asyncio.sleep(0)
                first.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await first
                finish.set()
                result = await second
                cached = await read_paper(PAPER)
            self.assertEqual(result["summary"], REPORT)
            self.assertTrue(cached["cached"])
            self.assertEqual(len(calls), 1)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
