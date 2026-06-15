import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class JobsStoreTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        from services import last30days_jobs as jobs
        self.jobs = jobs
        self._tmp = tempfile.TemporaryDirectory()
        d = Path(self._tmp.name)
        jobs.JOBS_DIR = d
        jobs.JOBS_FILE = d / "jobs.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_create_then_get_is_running(self):
        jid = self.jobs.create_job("Loop Engineering")
        job = self.jobs.get_job(jid)
        self.assertEqual(job["status"], "running")
        self.assertEqual(job["topic"], "Loop Engineering")
        self.assertIsNone(job["count"])

    def test_finish_with_count_is_done(self):
        jid = self.jobs.create_job("x")
        self.jobs.finish_job(jid, count=7)
        job = self.jobs.get_job(jid)
        self.assertEqual(job["status"], "done")
        self.assertEqual(job["count"], 7)
        self.assertIsNone(job["error"])
        self.assertIsNotNone(job["finished_at"])

    def test_finish_with_error_is_error(self):
        jid = self.jobs.create_job("x")
        self.jobs.finish_job(jid, error="boom")
        job = self.jobs.get_job(jid)
        self.assertEqual(job["status"], "error")
        self.assertEqual(job["error"], "boom")

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.jobs.get_job("nope"))

    def test_persisted_to_file(self):
        jid = self.jobs.create_job("persist me")
        self.assertTrue(self.jobs.JOBS_FILE.exists())
        # fresh read from disk
        import json
        data = json.loads(self.jobs.JOBS_FILE.read_text(encoding="utf-8"))
        self.assertIn(jid, data)


if __name__ == "__main__":
    unittest.main()
