import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main


class MainLifespanTest(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_closes_shared_wingsbot_client(self):
        with patch("services.wingsbot_client.close_wingsbot_client") as close:
            async with main.lifespan(main.app):
                close.assert_not_called()

            close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
