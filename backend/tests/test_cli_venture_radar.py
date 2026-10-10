import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cli


class VentureRadarCliTest(unittest.TestCase):
    def test_reports_archive_count_without_claiming_generic_content_imports(self):
        result = {
            "report_path": "/tmp/report.json",
            "reports_archived": 1,
            "archive": {"id": "report"},
        }
        args = Namespace(mode="radar", sources="all", lookback_days=7, max_items=30)

        with patch(
            "services.venture_product_radar_importer.run_venture_product_radar_direct",
            return_value=result,
        ), patch("builtins.print") as print_mock:
            cli.cmd_venture_radar(args)

        output = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
        self.assertIn("Archived reports: 1", output)
        self.assertNotIn("Imported content items", output)


if __name__ == "__main__":
    unittest.main()
