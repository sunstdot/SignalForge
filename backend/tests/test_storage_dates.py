import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import storage


def _write(content_dir: Path, date: str, items):
    (content_dir / f"{date}.json").write_text(json.dumps(items), encoding="utf-8")


def _write_json(path: Path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


class GetAllDatesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.content_dir = Path(self._tmp.name)
        self._patch = patch.object(storage, "CONTENT_DIR", self.content_dir)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def test_excludes_dates_with_only_last30days_imports(self):
        # 真正的 daily 采集（origin 缺省/为 '-'）
        _write(self.content_dir, "2026-06-18", [
            {"id": "a", "source_type": "arxiv"},
            {"id": "b", "source_type": "rss", "metadata": {"origin": "-"}},
        ])
        # 纯 last30days 导入，应被过滤
        _write(self.content_dir, "2026-06-16", [
            {"id": "c", "source_type": "x", "metadata": {"origin": "last30days"}},
        ])
        # 混合：当天既有 daily 又有 last30days，应保留
        _write(self.content_dir, "2026-06-01", [
            {"id": "d", "source_type": "rss"},
            {"id": "e", "source_type": "reddit", "metadata": {"origin": "last30days"}},
        ])

        dates = storage.get_all_dates()

        self.assertEqual(dates, ["2026-06-18", "2026-06-01"])

    def test_excludes_empty_content_files(self):
        _write(self.content_dir, "2026-06-18", [{"id": "a", "source_type": "arxiv"}])
        _write(self.content_dir, "2026-06-17", [])

        self.assertEqual(storage.get_all_dates(), ["2026-06-18"])

    def test_excludes_dates_with_only_venture_radar_imports(self):
        _write(self.content_dir, "2026-07-20", [
            {"id": "v", "metadata": {"origin": "venture-product-radar"}},
        ])
        _write(self.content_dir, "2026-07-10", [
            {"id": "daily", "source_type": "rss"},
            {"id": "v2", "metadata": {"origin": "venture-product-radar"}},
        ])

        self.assertEqual(storage.get_all_dates(), ["2026-07-10"])


class GetOpportunityDatesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.opportunities_dir = root / "opportunities"
        self.rdev_dir = root / "rdev_opportunities"
        self.opportunities_dir.mkdir()
        self.rdev_dir.mkdir()
        self._patches = [
            patch.object(storage, "OPPORTUNITIES_DIR", self.opportunities_dir),
            patch.object(storage, "RDEV_DIR", self.rdev_dir),
        ]
        for item in self._patches:
            item.start()

    def tearDown(self):
        for item in reversed(self._patches):
            item.stop()
        self._tmp.cleanup()

    def test_requires_non_empty_business_or_rdev_lists(self):
        _write_json(self.opportunities_dir / "2026-07-10.json", {"opportunities": [{"id": "b"}]})
        _write_json(self.rdev_dir / "2026-07-09.json", {"solutions": [{"id": "r"}]})
        _write_json(self.opportunities_dir / "2026-07-08.json", {"opportunities": []})
        _write_json(self.rdev_dir / "2026-07-08.json", {"solutions": []})
        _write_json(self.opportunities_dir / "2026-07-07.json", {"opportunities": "invalid"})

        self.assertEqual(storage.get_opportunity_dates(), ["2026-07-10", "2026-07-09"])


if __name__ == "__main__":
    unittest.main()
