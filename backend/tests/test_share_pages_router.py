import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from routers.share_pages import _filter_opportunities, _filter_content_items

_SAMPLE_OPP_1 = {
    "item_id": "o1", "opportunity_title": "Opp One", "total_score": 18,
    "core_insight": "ci", "product_form": "pf", "business_model": "bm",
    "target_users": "tu", "mvp_features": [], "risks": "r",
}
_SAMPLE_OPP_2 = {
    "item_id": "o2", "opportunity_title": "Opp Two", "total_score": 15,
    "core_insight": "ci2", "product_form": "pf2", "business_model": "bm2",
    "target_users": "tu2", "mvp_features": [], "risks": "r2",
}
_SAMPLE_ITEM_1 = {"id": "s1", "title": "Signal One", "source": "GitHub", "source_type": "repo", "relevance_score": 9}
_SAMPLE_ITEM_2 = {"id": "s2", "title": "Signal Two", "source": "arXiv", "source_type": "paper", "relevance_score": 8}
_QUICK_READS = {"s1": "quick read one", "s2": "quick read two"}


class TestFilterOpportunities(unittest.TestCase):
    def test_match_by_item_id(self):
        result = _filter_opportunities([_SAMPLE_OPP_1, _SAMPLE_OPP_2], ["o1"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["item_id"], "o1")

    def test_match_by_title_when_no_item_id(self):
        opps = [{"opportunity_title": "Opp A"}, {"opportunity_title": "Opp B"}]
        result = _filter_opportunities(opps, ["Opp A"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["opportunity_title"], "Opp A")

    def test_empty_ids_returns_empty(self):
        self.assertEqual(_filter_opportunities([_SAMPLE_OPP_1], []), [])

    def test_multiple_ids(self):
        result = _filter_opportunities([_SAMPLE_OPP_1, _SAMPLE_OPP_2], ["o1", "o2"])
        self.assertEqual(len(result), 2)


class TestFilterContentItems(unittest.TestCase):
    def test_match_by_id(self):
        result = _filter_content_items([_SAMPLE_ITEM_1, _SAMPLE_ITEM_2], ["s1"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "s1")

    def test_empty_ids_returns_empty(self):
        self.assertEqual(_filter_content_items([_SAMPLE_ITEM_1], []), [])


class TestGenerateEndpoint(unittest.TestCase):
    def setUp(self):
        from main import app
        from fastapi.testclient import TestClient
        self.client = TestClient(app)

    def test_returns_url_and_writes_html(self):
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch("routers.share_pages._load_share_sources",
                       return_value=([_SAMPLE_OPP_1, _SAMPLE_OPP_2], [_SAMPLE_ITEM_1, _SAMPLE_ITEM_2], _QUICK_READS)):
                with patch("routers.share_pages.SHARE_PAGES_DIR", tmp_path):
                    resp = self.client.post("/api/share-pages/generate", json={
                        "date": "2026-05-18",
                        "signal_ids": ["s1"],
                        "opportunity_ids": ["o1"],
                    })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["url"], "/api/share-pages/2026-05-18.html")
        html = (tmp_path / "2026-05-18.html").read_text()
        self.assertIn("Opp One", html)
        self.assertNotIn("Opp Two", html)
        self.assertIn("Signal One", html)
        self.assertNotIn("Signal Two", html)
