import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.venture_radar_intelligence import (
    build_quality_metrics,
    normalize_report,
    normalize_funding_event,
)


COLOSSAL_RAW = {
    "market_signal": "Colossal Biosciences reportedly in talks to raise new capital at $20B-$30B valuation",
    "source_urls": [
        "https://techcrunch.com/2026/07/20/colossal-biosciences-reportedly-in-talks-to-raise-new-capital-at-20b-30b-valuation"
    ],
    "evidence_gaps": ["official announcement", "lead investors", "business update"],
    "company_name": "Colossal Biosciences reportedly in talks to",
    "amount": "$20B",
    "officially_confirmed": False,
    "confidence": "low",
    "source_type": "media",
    "announced_date": "2026-07-19",
}

COLOSSAL_REPORT = {
    "source_links": [
        {
            "source_name": "TechCrunch",
            "source_type": "media",
            "source_tier": "tier_4_media",
            "published_at": "2026-07-19",
            "title": "Colossal Biosciences reportedly in talks to raise new capital at $20B-$30B valuation",
            "url": COLOSSAL_RAW["source_urls"][0],
        }
    ],
    "companies": [],
    "products": [],
}


class VentureRadarIntelligenceTest(unittest.TestCase):
    def test_preserves_field_level_provenance_objects(self):
        raw = {
            "company_name": "Acme AI",
            "event_status": {
                "value": "announced",
                "source_urls": ["https://acme.ai/news/series-a"],
                "source_types": ["company_press"],
                "confidence": "high",
            },
            "amount_raised": {
                "value": "$25M",
                "source_urls": ["https://acme.ai/news/series-a"],
                "source_types": ["company_press"],
                "confidence": "high",
            },
            "round": {
                "value": "Series A",
                "source_urls": ["https://acme.ai/news/series-a"],
                "source_types": ["company_press"],
                "confidence": "high",
            },
            "announced_date": {
                "value": "2026-07-18",
                "source_urls": ["https://acme.ai/news/series-a"],
                "source_types": ["company_press"],
                "confidence": "high",
            },
            "lead_investors": {
                "value": ["Example Ventures"],
                "source_urls": ["https://acme.ai/news/series-a"],
                "source_types": ["company_press"],
                "confidence": "high",
            },
            "confidence": "high",
            "what_happened": "Acme AI announced a $25M Series A.",
            "why_it_matters": "The round adds capacity for enterprise expansion.",
        }
        report = {"source_links": [{
            "url": "https://acme.ai/news/series-a",
            "source_type": "company_press",
            "source_name": "Acme AI",
        }]}

        event = normalize_funding_event(raw, report)

        self.assertEqual(event["amount_raised"], raw["amount_raised"])
        self.assertEqual(event["round"], raw["round"])
        self.assertEqual(event["lead_investors"], raw["lead_investors"])
        self.assertEqual(event["pipeline_stage"], "verified")

    def test_speculative_title_overrides_explicit_announced_status(self):
        raw = dict(COLOSSAL_RAW, event_status="announced")

        event = normalize_funding_event(raw, COLOSSAL_REPORT)

        self.assertEqual(event["event_status"]["value"], "in_talks")
        self.assertEqual(event["pipeline_stage"], "watchlist")

    def test_media_brand_containing_company_is_not_an_official_source(self):
        raw = {
            "company_name": "Acme AI",
            "event_status": "announced",
            "amount_raised": "$25M",
            "round": "Series A",
            "announced_date": "2026-07-18",
            "lead_investors": ["Example Ventures"],
            "confidence": "medium",
            "source_urls": ["https://fastcompany.com/acme-series-a"],
            "what_happened": "Acme AI announced a $25M Series A.",
            "why_it_matters": "The round funds enterprise expansion.",
        }
        report = {"source_links": [{
            "url": "https://fastcompany.com/acme-series-a",
            "source_type": "media",
            "source_name": "Fast Company",
        }]}

        event = normalize_funding_event(raw, report)

        self.assertEqual(event["official_source_count"], 0)
        self.assertNotEqual(event["pipeline_stage"], "verified")

    def test_social_sources_do_not_count_as_independent_credible_media(self):
        raw = {
            "company_name": "Acme AI",
            "event_status": "announced",
            "amount_raised": "$25M",
            "round": "Series A",
            "announced_date": "2026-07-18",
            "lead_investors": ["Example Ventures"],
            "confidence": "medium",
            "source_urls": ["https://x.com/acme/status/1", "https://news.ycombinator.com/item?id=1"],
            "what_happened": "Acme AI announced a $25M Series A.",
            "why_it_matters": "The round funds enterprise expansion.",
        }
        report = {"source_links": [
            {"url": raw["source_urls"][0], "source_type": "social"},
            {"url": raw["source_urls"][1], "source_type": "community"},
        ]}

        event = normalize_funding_event(raw, report)

        self.assertEqual(event["independent_source_count"], 0)
        self.assertNotEqual(event["pipeline_stage"], "verified")

    def test_valuation_is_not_mapped_to_amount_raised(self):
        event = normalize_funding_event(COLOSSAL_RAW, COLOSSAL_REPORT)

        self.assertIsNone(event["amount_raised"]["value"])
        self.assertEqual(event["valuation"]["value"], "$20B-$30B")
        self.assertIn("valuation", event["valuation"]["source_urls"][0])

    def test_reportedly_in_talks_becomes_watchlist_in_talks(self):
        event = normalize_funding_event(COLOSSAL_RAW, COLOSSAL_REPORT)

        self.assertEqual(event["event_status"]["value"], "in_talks")
        self.assertEqual(event["pipeline_stage"], "watchlist")
        self.assertFalse(event["officially_confirmed"])
        self.assertEqual(event["confidence"], "low")
        self.assertEqual(event["title_zh"], "Colossal Biosciences 据报正在洽谈融资，目标估值 $20B-$30B")

    def test_published_date_does_not_become_announced_date(self):
        event = normalize_funding_event(COLOSSAL_RAW, COLOSSAL_REPORT)

        self.assertEqual(event["published_date"]["value"], "2026-07-19")
        self.assertIsNone(event["announced_date"]["value"])

    def test_low_confidence_single_media_source_cannot_enter_verified(self):
        event = normalize_funding_event(COLOSSAL_RAW, COLOSSAL_REPORT)

        self.assertEqual(event["source_count"], 1)
        self.assertEqual(event["independent_source_count"], 1)
        self.assertEqual(event["official_source_count"], 0)
        self.assertNotEqual(event["pipeline_stage"], "verified")

    def test_official_source_event_can_enter_verified(self):
        raw = {
            "company_name": "Acme AI",
            "amount_raised": "$25M",
            "round": "Series A",
            "lead_investors": ["Example Ventures"],
            "event_status": "announced",
            "announced_date": "2026-07-18",
            "officially_confirmed": True,
            "confidence": "high",
            "source_urls": ["https://acme.ai/news/series-a"],
            "what_happened": "Acme AI announced a $25M Series A led by Example Ventures.",
            "why_it_matters": "The round validates enterprise demand for AI workflow automation.",
        }
        report = {
            "source_links": [{
                "url": "https://acme.ai/news/series-a",
                "source_type": "company_press",
                "source_name": "Acme AI",
                "published_at": "2026-07-18",
            }]
        }

        event = normalize_funding_event(raw, report)

        self.assertEqual(event["pipeline_stage"], "verified")
        self.assertGreaterEqual(event["completeness_score"], 70)
        self.assertGreaterEqual(event["official_source_count"], 1)

    def test_two_independent_sources_can_raise_confidence(self):
        raw = {
            "company_name": "Acme AI",
            "amount_raised": "$25M",
            "round": "Series A",
            "event_status": "announced",
            "announced_date": "2026-07-18",
            "confidence": "medium",
            "source_urls": ["https://techcrunch.com/acme", "https://venturebeat.com/acme"],
        }
        report = {
            "source_links": [
                {"url": "https://techcrunch.com/acme", "source_name": "TechCrunch", "source_type": "media"},
                {"url": "https://venturebeat.com/acme", "source_name": "VentureBeat", "source_type": "media"},
            ]
        }

        event = normalize_funding_event(raw, report)

        self.assertEqual(event["confidence"], "medium")
        self.assertGreaterEqual(event["independent_source_count"], 2)
        self.assertEqual(event["pipeline_stage"], "verified")

    def test_two_media_sources_without_key_field_agreement_stay_watchlist(self):
        urls = ["https://techcrunch.com/acme", "https://venturebeat.com/acme"]
        raw = {
            "company_name": "Acme AI",
            "amount_raised": {
                "value": "$25M",
                "source_urls": [urls[0]],
                "source_types": ["media"],
                "confidence": "medium",
            },
            "round": "Series A",
            "event_status": "announced",
            "announced_date": "2026-07-18",
            "lead_investors": ["Example Ventures"],
            "confidence": "medium",
            "source_urls": urls,
            "what_happened": "Acme AI announced a $25M Series A.",
            "why_it_matters": "The round funds enterprise expansion.",
        }
        report = {"source_links": [
            {"url": urls[0], "source_name": "TechCrunch", "source_type": "media"},
            {"url": urls[1], "source_name": "VentureBeat", "source_type": "media"},
        ]}

        event = normalize_funding_event(raw, report)

        self.assertEqual(event["independent_source_count"], 2)
        self.assertEqual(event["pipeline_stage"], "watchlist")
        self.assertIn("independent sources do not agree on critical fields", event["evidence_conflicts"])

    def test_critical_field_conflict_forces_watchlist(self):
        raw = {
            "company_name": "Acme AI",
            "amount_raised": "$25M",
            "valuation": "$25M",
            "round": "Series A",
            "event_status": "announced",
            "confidence": "high",
            "source_urls": ["https://acme.ai/news/series-a"],
            "officially_confirmed": True,
        }
        report = {
            "source_links": [{"url": "https://acme.ai/news/series-a", "source_type": "company_press"}]
        }

        event = normalize_funding_event(raw, report)

        self.assertEqual(event["pipeline_stage"], "watchlist")
        self.assertIn("amount_raised equals valuation", event["evidence_conflicts"])

    def test_enrichment_tasks_are_structured_per_candidate(self):
        event = normalize_funding_event(COLOSSAL_RAW, COLOSSAL_REPORT)

        task = event["enrichment_tasks"][0]
        self.assertEqual(task["entity"], "Colossal Biosciences")
        self.assertIn("field_to_verify", task)
        self.assertIn("expected_source_type", task)
        self.assertEqual(task["priority"], "high")

    def test_watchlist_event_generates_full_enrichment_task_set(self):
        event = normalize_funding_event(COLOSSAL_RAW, COLOSSAL_REPORT)

        fields = {task["field_to_verify"] for task in event["enrichment_tasks"]}

        self.assertTrue({
            "company_website",
            "company_newsroom",
            "investor_announcement",
            "company_profile",
            "previous_round",
            "independent_source",
            "business_update",
            "amount_classification",
            "lead_investors",
            "event_status",
        }.issubset(fields))

    def test_duplicate_events_are_rejected_and_metrics_use_type_specific_keys(self):
        report = {
            "products": [
                {"name": "Acme Canvas", "launch_date": "2026-07-20", "source_urls": ["https://producthunt.com/acme"]},
                {"name": "Other Copilot", "launch_date": "2026-07-20", "source_urls": ["https://producthunt.com/other"]},
                {"name": "Acme Canvas", "launch_date": "2026-07-20", "source_urls": ["https://github.com/acme/canvas"]},
            ],
            "funding_rounds": [],
            "source_links": [],
        }

        normalized = normalize_report(report)

        self.assertEqual(len(normalized["by_stage"]["verified"]), 2)
        self.assertEqual(len(normalized["by_stage"]["rejected"]), 1)
        self.assertEqual(normalized["quality_metrics"]["duplicate_rate"], 0.33)

    def test_empty_analysis_template_is_removed_without_replacement_fluff(self):
        raw = dict(
            COLOSSAL_RAW,
            why_it_matters="需要补充公司背景、产品、客户和市场意义后再判断关注优先级。",
            opportunity_angle="需要继续核验官方公告、领投方、业务进展和同类公司的资本动向。",
        )

        event = normalize_funding_event(raw, COLOSSAL_REPORT)

        self.assertEqual(event["why_it_matters"], "")
        self.assertEqual(event["opportunity_angle"], "")
        self.assertEqual(event["risk_and_uncertainty"], "当前证据不足，尚不能判断其市场意义。")

    def test_quality_metrics_prioritize_verified_and_actionable_signals(self):
        verified = normalize_funding_event({
            "company_name": "Acme AI",
            "amount_raised": "$25M",
            "round": "Series A",
            "event_status": "announced",
            "announced_date": "2026-07-18",
            "confidence": "high",
            "officially_confirmed": True,
            "source_urls": ["https://acme.ai/news/series-a"],
        }, {"source_links": [{"url": "https://acme.ai/news/series-a", "source_type": "company_press"}]})
        watch = normalize_funding_event(COLOSSAL_RAW, COLOSSAL_REPORT)

        metrics = build_quality_metrics([verified, watch])

        self.assertEqual(metrics["verified_ratio"], 0.5)
        self.assertEqual(metrics["pending_verification_count"], 1)
        self.assertEqual(metrics["low_confidence_ratio"], 0.5)
        self.assertEqual(metrics["actionable_signal_count"], 1)

    def test_product_launches_enter_verified_feed_without_funding_gate(self):
        report = {
            "products": [{
                "name": "Acme Canvas",
                "company": "Acme AI",
                "product_type": "AI design tool",
                "launch_date": "2026-07-20",
                "confidence": "low",
                "source_urls": ["https://www.producthunt.com/posts/acme-canvas"],
            }],
            "funding_rounds": [],
            "source_links": [{
                "url": "https://www.producthunt.com/posts/acme-canvas",
                "source_type": "product_launch",
                "source_name": "Product Hunt",
                "published_at": "2026-07-20",
            }],
        }

        normalized = normalize_report(report)
        product = normalized["by_stage"]["verified"][0]

        self.assertEqual(product["entity_type"], "product_launch")
        self.assertEqual(product["pipeline_stage"], "verified")
        self.assertEqual(product["name"], "Acme Canvas")
        self.assertEqual(product["launch_date"]["value"], "2026-07-20")


if __name__ == "__main__":
    unittest.main()
