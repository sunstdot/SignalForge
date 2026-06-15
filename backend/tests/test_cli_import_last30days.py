import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cli


class ImportLast30daysCliTest(unittest.TestCase):
    def test_file_mode_calls_file_importer(self):
        with patch("services.last30days_importer.import_last30days_file", return_value=3) as imp:
            cli.cmd_import_last30days(Namespace(file="/tmp/x.md", dir=None))
        imp.assert_called_once_with("/tmp/x.md")

    def test_default_dir_mode(self):
        with patch("services.last30days_importer.import_last30days_dir", return_value=6) as imp:
            cli.cmd_import_last30days(Namespace(file=None, dir=None))
        imp.assert_called_once_with(None)


if __name__ == "__main__":
    unittest.main()
