import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.dates import router


class DatesRouterTest(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router, prefix="/api/dates")
        self.client = TestClient(app)

    def test_opportunity_dates_endpoint_returns_dedicated_dates(self):
        with patch("routers.dates.get_opportunity_dates", return_value=["2026-07-10"]):
            response = self.client.get("/api/dates/opportunities")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"dates": ["2026-07-10"]})


if __name__ == "__main__":
    unittest.main()
