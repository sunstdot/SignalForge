import unittest
from datetime import datetime
from unittest.mock import patch

from backend.services import collector


class DailyCollectionDateTest(unittest.IsolatedAsyncioTestCase):
    async def test_run_daily_collects_for_requested_date(self):
        calls = {}

        async def fake_run_collection(target_date=None):
            calls["target_date"] = target_date
            return 0

        with (
            patch.object(collector, "run_collection", side_effect=fake_run_collection),
            patch.object(collector, "_run_batch_quick_reads"),
            patch.object(collector, "_load_content_file", return_value=[]),
        ):
            await collector.run_daily("2026-05-12")

        self.assertEqual(calls["target_date"], "2026-05-12")

    async def test_run_collection_stores_all_items_under_target_date(self):
        stored_items = []

        async def fake_fetch_all_sources(config, target_date=None):
            return [
                {"id": "prev-datetime", "created_at": datetime(2026, 5, 11, 9, 0)},
                {"id": "prev-string", "created_at": "2026-05-11T10:00:00"},
                {"id": "missing-date"},
            ]

        def fake_store_content_items(items):
            stored_items.extend(items)
            return len(items)

        with (
            patch.object(collector, "load_config", return_value={"sources": {}}),
            patch.object(collector, "fetch_all_sources", side_effect=fake_fetch_all_sources),
            patch.object(collector, "store_content_items", side_effect=fake_store_content_items),
        ):
            await collector.run_collection(target_date="2026-05-12")

        self.assertEqual(
            [item["created_at"] for item in stored_items],
            ["2026-05-12", "2026-05-12", "2026-05-12"],
        )


if __name__ == "__main__":
    unittest.main()
