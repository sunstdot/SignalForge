import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.cleanup_venture_radar_content import clean_content_dir


class CleanupVentureRadarContentTest(unittest.TestCase):
    def test_removes_only_venture_items_and_deletes_empty_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            content_dir = Path(tmp)
            mixed = content_dir / "2026-07-10.json"
            venture_only = content_dir / "2026-07-20.json"
            untouched = content_dir / "2026-07-21.json"
            mixed.write_text(json.dumps([
                {"id": "daily", "metadata": {"origin": "-"}},
                {"id": "venture", "metadata": {"origin": "venture-product-radar"}},
            ]), encoding="utf-8")
            venture_only.write_text(json.dumps([
                {"id": "venture-2", "metadata": {"origin": "venture-product-radar"}},
            ]), encoding="utf-8")
            untouched_value = [{"id": "rss", "source_type": "rss"}]
            untouched.write_text(json.dumps(untouched_value), encoding="utf-8")

            result = clean_content_dir(content_dir)

            self.assertEqual(json.loads(mixed.read_text(encoding="utf-8")), [
                {"id": "daily", "metadata": {"origin": "-"}},
            ])
            self.assertFalse(venture_only.exists())
            self.assertEqual(json.loads(untouched.read_text(encoding="utf-8")), untouched_value)
            self.assertEqual(result, {
                "files_changed": 1,
                "files_deleted": 1,
                "items_removed": 2,
            })


if __name__ == "__main__":
    unittest.main()
