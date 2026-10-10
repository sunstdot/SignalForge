import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import venture_radar_reports as reports


SAMPLE_REPORT = {
    "schema_version": "venture-product-radar.v2",
    "command": "venture-radar",
    "mode": "radar",
    "topic": "AI sales automation startup opportunities",
    "generated_at": "2026-07-08T13:47:59+00:00",
    "lookback_days": 30,
    "companies": [],
    "products": [{"name": "JSONbored/awesome-claude", "confidence": "low"}],
    "funding_rounds": [{"company_name": "AI chip maker SambaNova", "amount": "$1B"}],
    "signals": [{"title": "Railway secures $100 million", "signal_score": 57}],
    "source_links": [{"url": "https://example.com/source"}],
    "next_watch_items": ["Find primary product page for JSONbored/awesome-claude."],
    "errors_by_source": {"rss_feeds": ["HTTP Error 403: Forbidden"]},
}


class VentureRadarReportsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name)
        reports.VENTURE_RADAR_DIR = self.data_dir
        reports.REPORTS_DIR = self.data_dir / "reports"
        reports.INDEX_FILE = self.data_dir / "index.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_report(self, name="radar-ai-sales-automation-startup-opportunities-20260708T134819Z.json", data=None):
        path = self.data_dir / name
        path.write_text(json.dumps(data or SAMPLE_REPORT, ensure_ascii=False), encoding="utf-8")
        return path

    def test_import_report_copies_raw_json_and_indexes_summary(self):
        entry = reports.import_venture_radar_report(str(self._write_report()))

        self.assertEqual(entry["id"], "radar-ai-sales-automation-startup-opportunities-20260708T134819Z")
        self.assertEqual(entry["topic"], "AI sales automation startup opportunities")
        self.assertEqual(entry["counts"]["products"], 1)
        self.assertEqual(entry["counts"]["funding_rounds"], 1)
        self.assertEqual(entry["counts"]["signals"], 1)
        self.assertEqual(entry["counts"]["source_links"], 1)
        self.assertEqual(entry["counts"]["next_watch_items"], 1)
        self.assertEqual(entry["counts"]["source_errors"], 1)

        stored = reports.load_venture_radar_report(entry["id"])
        self.assertEqual(stored["topic"], SAMPLE_REPORT["topic"])
        self.assertEqual(stored["products"][0]["name"], "JSONbored/awesome-claude")

    def test_list_reports_orders_by_generated_at_desc(self):
        older = dict(SAMPLE_REPORT, topic="Older", generated_at="2026-07-07T00:00:00+00:00")
        newer = dict(SAMPLE_REPORT, topic="Newer", generated_at="2026-07-09T00:00:00+00:00")
        reports.import_venture_radar_report(str(self._write_report("older.json", older)))
        reports.import_venture_radar_report(str(self._write_report("newer.json", newer)))

        listed = reports.list_venture_radar_reports()

        self.assertEqual([item["topic"] for item in listed], ["Newer", "Older"])

    def test_week_index_and_week_detail_aggregate_reports(self):
        first = dict(SAMPLE_REPORT, topic="AI sales", generated_at="2026-07-08T13:47:59+00:00")
        second = {
            **SAMPLE_REPORT,
            "topic": "AI SDR",
            "generated_at": "2026-07-09T13:47:59+00:00",
            "products": [{"name": "Second product"}],
            "funding_rounds": [],
            "signals": [{"title": "Second signal"}],
            "source_links": [{"url": "https://example.com/second"}],
        }
        reports.import_venture_radar_report(str(self._write_report("first.json", first)))
        reports.import_venture_radar_report(str(self._write_report("second.json", second)))

        weeks = reports.list_venture_radar_weeks()
        self.assertEqual(weeks[0]["week"], "2026-W28")
        self.assertEqual(weeks[0]["report_count"], 2)
        self.assertEqual(weeks[0]["counts"]["products"], 2)
        self.assertEqual(weeks[0]["counts"]["funding_rounds"], 1)
        self.assertEqual(weeks[0]["counts"]["signals"], 2)
        self.assertEqual(weeks[0]["topics"], ["AI SDR", "AI sales"])

        detail = reports.load_venture_radar_week("2026-W28")
        self.assertEqual(detail["week"], "2026-W28")
        self.assertEqual(len(detail["reports"]), 2)
        self.assertEqual(len(detail["aggregate"]["products"]), 2)
        self.assertEqual(len(detail["aggregate"]["funding_rounds"]), 1)
        self.assertEqual(len(detail["aggregate"]["signals"]), 2)

    def test_week_detail_includes_intelligence_stages_and_quality_metrics(self):
        report = {
            **SAMPLE_REPORT,
            "source_links": [{
                "url": "https://techcrunch.com/colossal",
                "source_name": "TechCrunch",
                "source_type": "media",
                "published_at": "2026-07-19",
                "title": "Colossal Biosciences reportedly in talks to raise new capital at $20B-$30B valuation",
            }],
            "funding_rounds": [{
                "company_name": "Colossal Biosciences reportedly in talks to",
                "amount": "$20B",
                "market_signal": "Colossal Biosciences reportedly in talks to raise new capital at $20B-$30B valuation",
                "announced_date": "2026-07-19",
                "officially_confirmed": False,
                "confidence": "low",
                "source_urls": ["https://techcrunch.com/colossal"],
                "evidence_gaps": ["official announcement"],
            }],
        }
        reports.import_venture_radar_report(str(self._write_report("colossal.json", report)))

        detail = reports.load_venture_radar_week("2026-W28")
        event = detail["aggregate"]["intelligence_by_stage"]["watchlist"][0]

        self.assertEqual(event["pipeline_stage"], "watchlist")
        self.assertEqual(event["event_status"]["value"], "in_talks")
        self.assertIsNone(event["amount_raised"]["value"])
        self.assertEqual(event["valuation"]["value"], "$20B-$30B")
        self.assertEqual(detail["aggregate"]["quality_metrics"]["pending_verification_count"], 1)
        self.assertGreaterEqual(len(detail["aggregate"]["enrichment_tasks"]), 1)

    def test_generated_at_falls_back_to_timestamp_in_filename(self):
        report = dict(SAMPLE_REPORT)
        report.pop("generated_at")

        entry = reports.import_venture_radar_report(str(self._write_report(
            "radar-ai-sales-automation-startup-opportunities-20260708T134819Z.json",
            report,
        )))

        self.assertEqual(entry["generated_at"], "2026-07-08T13:48:19+00:00")

    def test_rejects_invalid_schema(self):
        bad = dict(SAMPLE_REPORT, schema_version="other.v1")
        with self.assertRaises(ValueError):
            reports.import_venture_radar_report(str(self._write_report("bad.json", bad)))

    def test_rejects_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            reports.import_venture_radar_report(str(self.data_dir / "missing.json"))


if __name__ == "__main__":
    unittest.main()
