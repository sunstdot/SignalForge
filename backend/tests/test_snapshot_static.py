import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import snapshot_static


class StaticSnapshotTest(unittest.TestCase):
    def test_snapshots_payloads_for_opportunity_only_dates(self):
        requested = []

        def fake_save(url):
            requested.append(url)
            if url == "/api/dates":
                return {"dates": []}
            if url == "/api/dates/opportunities":
                return {"dates": ["2026-07-10"]}
            return {}

        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(snapshot_static, "OUT", Path(tmp)), \
                patch.object(snapshot_static, "save", side_effect=fake_save), \
                patch.object(snapshot_static, "cached", return_value=True):
            snapshot_static.main_snapshot()

        self.assertIn("/api/dates/opportunities", requested)
        self.assertIn("/api/briefing/2026-07-10/opportunities", requested)
        self.assertIn("/api/briefing/2026-07-10/rdev-opportunities", requested)

    def test_snapshots_venture_radar_week_archives(self):
        requested = []

        def fake_save(url):
            requested.append(url)
            if url == "/api/dates":
                return {"dates": []}
            if url == "/api/venture-radar/weeks":
                return {"weeks": [{"week": "2026-W28"}]}
            return {}

        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(snapshot_static, "OUT", Path(tmp)), \
                patch.object(snapshot_static, "save", side_effect=fake_save):
            snapshot_static.main_snapshot()

        self.assertIn("/api/venture-radar/weeks", requested)
        self.assertIn("/api/venture-radar/weeks/2026-W28", requested)


if __name__ == "__main__":
    unittest.main()
