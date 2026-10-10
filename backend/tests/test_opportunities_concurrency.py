import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routers import briefing


def _make_items(n):
    return [
        {
            "id": f"id-{i}",
            "title": f"title-{i}",
            "source": "X",
            "source_type": "x",
            "url": f"https://example.com/{i}",
            "summary": f"summary-{i}",
        }
        for i in range(n)
    ]


class ConcurrencyTest(unittest.IsolatedAsyncioTestCase):
    async def test_batches_run_concurrently(self):
        state = {"current": 0, "max": 0}

        async def fake_chat_async(messages, provider=None, **kwargs):
            state["current"] += 1
            state["max"] = max(state["max"], state["current"])
            await asyncio.sleep(0.05)
            state["current"] -= 1
            # 每条返回空机会即可，本用例只验证并发度
            return "[]"

        items = _make_items(30)  # 3 个批次（BATCH_SIZE=10）
        with patch.object(briefing, "chat_async", side_effect=fake_chat_async):
            await briefing._analyze_items_for_opportunities(items, "2026-06-18")

        # 串行执行时 max 恒为 1；并发时应 >= 2
        self.assertGreaterEqual(state["max"], 2)

    async def test_idx_maps_to_item_within_batch(self):
        async def fake_chat_async(messages, provider=None, **kwargs):
            # 标记该批次第 2 条有机会
            return json.dumps([
                {"idx": 2, "has_opportunities": True, "ideas": [
                    {"title": "T", "scores": {"pain_point": 3}},
                ]},
            ])

        items = _make_items(10)
        with patch.object(briefing, "chat_async", side_effect=fake_chat_async):
            opps = await briefing._analyze_items_for_opportunities(items, "2026-06-18")

        self.assertEqual(len(opps), 1)
        self.assertEqual(opps[0]["item_id"], "id-1")  # 批次内第 2 条 = items[1]
        self.assertEqual(opps[0]["total_score"], 3)


if __name__ == "__main__":
    unittest.main()
