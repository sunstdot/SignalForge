import sys
import unittest
from argparse import Namespace
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cli


class SharePageCliTest(unittest.TestCase):
    def test_cmd_share_page_generates_html_and_cover_together(self):
        payload = {"date": "2026-05-14", "opportunities": [], "briefings": []}

        with patch("services.share_page.generate_share_page") as generate_page:
            with patch("services.share_page.load_share_payload", return_value=payload):
                with patch("services.social_cover.generate_xiaohongshu_cover") as generate_cover:
                    cli.cmd_share_page(Namespace(date="2026-05-14"))

        output_dir = Path(cli.__file__).parent / "docs" / "share-pages"
        generate_page.assert_called_once_with("2026-05-14", output_dir / "2026-05-14.html")
        generate_cover.assert_called_once_with(payload, output_dir / "2026-05-14-cover.png")

    def test_cmd_share_page_keeps_html_when_cover_render_fails(self):
        payload = {"date": "2026-05-14", "opportunities": [], "briefings": []}

        with patch("services.share_page.generate_share_page") as generate_page:
            with patch("services.share_page.load_share_payload", return_value=payload):
                with patch(
                    "services.social_cover.generate_xiaohongshu_cover",
                    side_effect=CalledProcessError(1, ["node", "render_social_cover.mjs"]),
                ):
                    with patch("builtins.print") as print_mock:
                        cli.cmd_share_page(Namespace(date="2026-05-14"))

        generate_page.assert_called_once()
        printed = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
        self.assertIn("Share page saved", printed)
        self.assertIn("Xiaohongshu cover failed", printed)


if __name__ == "__main__":
    unittest.main()
