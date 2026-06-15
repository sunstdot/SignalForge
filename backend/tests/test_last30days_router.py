import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_client(tmpdir: Path) -> TestClient:
    from services import last30days_jobs as jobs
    jobs.JOBS_DIR = tmpdir
    jobs.JOBS_FILE = tmpdir / "jobs.json"
    from routers.last30days import router
    app = FastAPI()
    app.include_router(router, prefix="/api/last30days")
    return TestClient(app)


class Last30daysRouterTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.client = _make_client(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_topic_returns_400(self):
        r = self.client.post("/api/last30days/research", json={"topic": "  "})
        self.assertEqual(r.status_code, 400)

    def test_unknown_job_returns_404(self):
        r = self.client.get("/api/last30days/research/nope")
        self.assertEqual(r.status_code, 404)

    def test_research_runs_and_polls_to_done(self):
        def fake_run(topic):
            return 5
        with patch("routers.last30days.run_last30days_via_wingsbot", side_effect=fake_run):
            r = self.client.post("/api/last30days/research", json={"topic": "Loop Engineering"})
            self.assertEqual(r.status_code, 200)
            body = r.json()
            self.assertEqual(body["status"], "running")
            job_id = body["job_id"]

            # poll until the background thread finishes
            for _ in range(50):
                jr = self.client.get(f"/api/last30days/research/{job_id}").json()
                if jr["status"] != "running":
                    break
                time.sleep(0.05)
            self.assertEqual(jr["status"], "done")
            self.assertEqual(jr["count"], 5)

    def test_research_failure_marks_error(self):
        def boom(topic):
            raise RuntimeError("wingsbot down")
        with patch("routers.last30days.run_last30days_via_wingsbot", side_effect=boom):
            job_id = self.client.post(
                "/api/last30days/research", json={"topic": "x"}
            ).json()["job_id"]
            for _ in range(50):
                jr = self.client.get(f"/api/last30days/research/{job_id}").json()
                if jr["status"] != "running":
                    break
                time.sleep(0.05)
            self.assertEqual(jr["status"], "error")
            self.assertIn("wingsbot down", jr["error"])


if __name__ == "__main__":
    unittest.main()
