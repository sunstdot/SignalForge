import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _client(tmp: Path) -> TestClient:
    from services import last30days_jobs as jobs
    jobs.JOBS_DIR = tmp
    jobs.JOBS_FILE = tmp / "jobs.json"
    from routers.search import router
    app = FastAPI()
    app.include_router(router, prefix="/api/search")
    return TestClient(app)


class SearchBriefRouterTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.client = _client(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_topic_400(self):
        self.assertEqual(self.client.post("/api/search/brief", json={"topic": " "}).status_code, 400)

    def test_unknown_job_404(self):
        self.assertEqual(self.client.get("/api/search/brief/nope").status_code, 404)

    def test_brief_job_runs_to_done(self):
        fake_brief = {"topic": "Loop Engineering", "meta": {"total": 3}, "timeline": []}
        # build_brief returns the brief; the job stores only a slug, and the GET
        # loads the brief from its file (load_brief patched to return it).
        with patch("routers.search.run_last30days_via_wingsbot", return_value=3), \
             patch("routers.search.build_brief", return_value=fake_brief), \
             patch("routers.search.load_brief", return_value=fake_brief):
            body = self.client.post("/api/search/brief", json={"topic": "Loop Engineering"}).json()
            self.assertEqual(body["status"], "running")
            jid = body["job_id"]
            for _ in range(50):
                job = self.client.get(f"/api/search/brief/{jid}").json()
                if job["status"] != "running":
                    break
                time.sleep(0.05)
            self.assertEqual(job["status"], "done")
            self.assertEqual(job["brief_slug"], "loop-engineering")  # job carries slug ref only
            self.assertEqual(job["brief"]["meta"]["total"], 3)       # brief loaded from file

    def test_cached_brief_by_topic(self):
        fake_brief = {"topic": "X", "meta": {"total": 1}}
        with patch("routers.search.load_brief", return_value=fake_brief):
            r = self.client.get("/api/search/brief", params={"topic": "X"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["meta"]["total"], 1)

    def test_cached_brief_missing_404(self):
        with patch("routers.search.load_brief", return_value=None):
            r = self.client.get("/api/search/brief", params={"topic": "nope"})
        self.assertEqual(r.status_code, 404)

    def test_history_endpoint_keeps_entries_with_existing_brief(self):
        hist = [{"slug": "x", "topic": "X", "total": 5, "updated_at": "2026-06-16T10:00:00"}]
        with patch("routers.search.load_history", return_value=hist), \
             patch("routers.search.load_brief", return_value={"meta": {"total": 5}}):
            r = self.client.get("/api/search/history")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["history"][0]["topic"], "X")

    def test_history_endpoint_drops_stale_entries(self):
        hist = [{"slug": "gone", "topic": "Gone", "total": 5}]
        with patch("routers.search.load_history", return_value=hist), \
             patch("routers.search.load_brief", return_value=None):  # brief file missing
            r = self.client.get("/api/search/history")
        self.assertEqual(r.json()["history"], [])

    def test_brief_job_error(self):
        with patch("routers.search.run_last30days_via_wingsbot", side_effect=RuntimeError("boom")):
            jid = self.client.post("/api/search/brief", json={"topic": "x"}).json()["job_id"]
            for _ in range(50):
                job = self.client.get(f"/api/search/brief/{jid}").json()
                if job["status"] != "running":
                    break
                time.sleep(0.05)
            self.assertEqual(job["status"], "error")
            self.assertIn("boom", job["error"])


if __name__ == "__main__":
    unittest.main()
