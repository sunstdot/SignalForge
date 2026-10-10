import json
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
    from routers.venture_radar import router
    app = FastAPI()
    app.include_router(router, prefix="/api/venture-radar")
    return TestClient(app)


class VentureRadarRouterTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.client = _make_client(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_topic_returns_400(self):
        r = self.client.post("/api/venture-radar/research", json={"topic": "  "})
        self.assertEqual(r.status_code, 400)

    def test_unknown_job_returns_404(self):
        r = self.client.get("/api/venture-radar/research/nope")
        self.assertEqual(r.status_code, 404)

    def test_research_runs_and_polls_to_done(self):
        def fake_run(topic, sources=None, mode="radar"):
            self.assertEqual(topic, "AI agent startups")
            self.assertEqual(sources, ["web", "producthunt"])
            self.assertEqual(mode, "radar")
            return 4

        with patch("routers.venture_radar.run_venture_product_radar_via_wingsbot", side_effect=fake_run):
            r = self.client.post(
                "/api/venture-radar/research",
                json={"topic": "AI agent startups", "sources": ["web", "producthunt"]},
            )
            self.assertEqual(r.status_code, 200)
            body = r.json()
            self.assertEqual(body["status"], "running")
            job_id = body["job_id"]

            for _ in range(50):
                jr = self.client.get(f"/api/venture-radar/research/{job_id}").json()
                if jr["status"] != "running":
                    break
                time.sleep(0.05)
            self.assertEqual(jr["status"], "done")
            self.assertEqual(jr["count"], 4)

    def test_research_failure_marks_error(self):
        def boom(topic, sources=None, mode="radar"):
            raise RuntimeError("wingsbot down")

        with patch("routers.venture_radar.run_venture_product_radar_via_wingsbot", side_effect=boom):
            job_id = self.client.post(
                "/api/venture-radar/research", json={"topic": "AI agent startups"}
            ).json()["job_id"]
            for _ in range(50):
                jr = self.client.get(f"/api/venture-radar/research/{job_id}").json()
                if jr["status"] != "running":
                    break
                time.sleep(0.05)
            self.assertEqual(jr["status"], "error")
            self.assertIn("wingsbot down", jr["error"])

    def test_mode_endpoints_pass_expected_modes(self):
        calls = []

        def fake_run(topic, sources=None, mode="radar"):
            calls.append((topic, tuple(sources or []), mode))
            return 1

        with patch("routers.venture_radar.run_venture_product_radar_via_wingsbot", side_effect=fake_run):
            for path, expected_mode in [
                ("/api/venture-radar/vc", "vc"),
                ("/api/venture-radar/product", "product"),
                ("/api/venture-radar/finance", "finance"),
            ]:
                r = self.client.post(path, json={"topic": "AI infra", "sources": ["web"]})
                self.assertEqual(r.status_code, 200)
                job_id = r.json()["job_id"]
                for _ in range(50):
                    jr = self.client.get(f"/api/venture-radar/research/{job_id}").json()
                    if jr["status"] != "running":
                        break
                    time.sleep(0.05)
                self.assertEqual(jr["status"], "done")
                self.assertEqual(calls[-1], ("AI infra", ("web",), expected_mode))

        self.assertEqual(len(calls), 3)

    def test_import_file_and_read_report_archive(self):
        from services import venture_radar_reports as reports
        reports.VENTURE_RADAR_DIR = Path(self._tmp.name) / "venture_radar"
        reports.REPORTS_DIR = reports.VENTURE_RADAR_DIR / "reports"
        reports.INDEX_FILE = reports.VENTURE_RADAR_DIR / "index.json"

        sample = {
            "schema_version": "venture-product-radar.v2",
            "command": "venture-radar",
            "mode": "radar",
            "topic": "AI sales automation startup opportunities",
            "generated_at": "2026-07-08T13:47:59+00:00",
            "lookback_days": 30,
            "products": [{"name": "JSONbored/awesome-claude"}],
            "funding_rounds": [{"company_name": "AI chip maker SambaNova", "amount": "$1B"}],
            "signals": [{"title": "Railway secures $100 million"}],
            "source_links": [],
            "next_watch_items": [],
        }
        path = Path(self._tmp.name) / "sample-report.json"
        path.write_text(json.dumps(sample), encoding="utf-8")

        imported = self.client.post("/api/venture-radar/import-file", json={"path": str(path)})
        self.assertEqual(imported.status_code, 200)
        report_id = imported.json()["id"]

        listed = self.client.get("/api/venture-radar/reports")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["reports"][0]["id"], report_id)

        loaded = self.client.get(f"/api/venture-radar/reports/{report_id}")
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["topic"], "AI sales automation startup opportunities")

        weeks = self.client.get("/api/venture-radar/weeks")
        self.assertEqual(weeks.status_code, 200)
        self.assertEqual(weeks.json()["weeks"][0]["week"], "2026-W28")

        week = self.client.get("/api/venture-radar/weeks/2026-W28")
        self.assertEqual(week.status_code, 200)
        self.assertEqual(week.json()["aggregate"]["products"][0]["name"], "JSONbored/awesome-claude")

    def test_unknown_report_returns_404(self):
        r = self.client.get("/api/venture-radar/reports/nope")
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
