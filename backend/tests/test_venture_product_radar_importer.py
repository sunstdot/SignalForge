import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import ANY, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.venture_product_radar_importer import (
    _build_wingsbot_prompt,
    build_direct_venture_radar_command,
    import_venture_product_radar_file,
    parse_venture_product_radar_json,
    run_venture_product_radar_direct,
)


SAMPLE_REPORT = {
    "schema_version": "venture-product-radar.v1",
    "command": "venture-vc",
    "mode": "vc",
    "topic": "AI agent startups",
    "generated_at": "2026-07-06T10:00:00Z",
    "lookback_days": 30,
    "sources_requested": ["web", "producthunt", "funding", "vc"],
    "companies": [
        {
            "name": "Acme AI",
            "description": "Builds sales workflow agents for revenue teams.",
            "website": "https://acme.ai",
            "sector": "AI agents",
            "stage": "Seed",
            "investors": ["Example Ventures"],
            "confidence": "high",
            "why_it_matters": "VCs are funding vertical agent workflows.",
            "opportunity_angle": "Build narrow workflow automation for sales ops.",
            "evidence_gaps": ["Customer traction is not independently verified."],
            "source_urls": ["https://example.com/acme-profile"],
        }
    ],
    "products": [
        {
            "name": "Acme Copilot",
            "company": "Acme AI",
            "tagline": "An agent workspace for sales teams.",
            "url": "https://www.producthunt.com/posts/acme-copilot",
            "launch_date": "2026-07-05",
            "platform": "Product Hunt",
            "confidence": "medium",
            "why_it_matters": "Shows early positioning for agent workspaces.",
            "opportunity_angle": "Package agent workflows as templates.",
            "evidence_gaps": [],
        }
    ],
    "funding_rounds": [
        {
            "company": "Acme AI",
            "round_type": "Seed",
            "amount": "$5M",
            "announced_date": "2026-07-04",
            "investors": ["Example Ventures", "Seed Fund"],
            "source_url": "https://example.com/acme-seed",
            "confidence": "high",
            "why_it_matters": "Fresh capital validates the category.",
            "opportunity_angle": "Look for underserved verticals before incumbents expand.",
            "evidence_gaps": ["Valuation not disclosed."],
        }
    ],
    "signals": [
        {
            "type": "market_signal",
            "title": "Sales teams are adopting agent workspaces",
            "summary": "Several new launches target revenue operations.",
            "url": "https://example.com/sales-agent-signal",
            "confidence": "low",
            "why_it_matters": "Multiple companies are converging on the same workflow.",
            "opportunity_angle": "Find repeated manual handoffs in revenue operations.",
            "evidence_gaps": [],
        },
        {
            "type": "research_plan",
            "title": "Suggested source queries",
            "summary": "Should not become a content item.",
            "queries": ["AI agent startups"],
            "confidence": "medium",
        },
    ],
    "source_links": [],
    "errors_by_source": {},
}


def _report_to_text(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


class ParseVentureProductRadarTest(unittest.TestCase):
    def test_parses_companies_products_and_actionable_signals_but_hides_unverified_funding(self):
        items = parse_venture_product_radar_json(_report_to_text(SAMPLE_REPORT))
        self.assertEqual(len(items), 3)

        company, product, signal = items
        self.assertEqual(company["source_type"], "vc_company")
        self.assertEqual(company["source"], "Venture Product Radar")
        self.assertEqual(company["title"], "Acme AI")
        self.assertEqual(company["url"], "https://acme.ai")
        self.assertEqual(company["relevance_score"], 8)
        self.assertEqual(company["metadata"]["origin"], "venture-product-radar")
        self.assertEqual(company["metadata"]["topic"], "AI agent startups")
        self.assertEqual(company["metadata"]["command"], "venture-vc")
        self.assertEqual(company["metadata"]["mode"], "vc")
        self.assertEqual(company["metadata"]["stage"], "Seed")
        self.assertEqual(company["metadata"]["why_it_matters"], "VCs are funding vertical agent workflows.")
        self.assertEqual(company["metadata"]["opportunity_angle"], "Build narrow workflow automation for sales ops.")
        self.assertEqual(company["metadata"]["evidence_gaps"], ["Customer traction is not independently verified."])

        self.assertEqual(product["source_type"], "product")
        self.assertEqual(product["source"], "Product Hunt")
        self.assertEqual(product["title"], "Acme Copilot")
        self.assertEqual(product["date"], "2026-07-05")
        self.assertEqual(product["metadata"]["company"], "Acme AI")
        self.assertEqual(product["metadata"]["opportunity_angle"], "Package agent workflows as templates.")

        self.assertEqual(signal["source_type"], "venture_signal")
        self.assertEqual(signal["title"], "Sales teams are adopting agent workspaces")
        self.assertEqual(signal["relevance_score"], 3)
        self.assertEqual(signal["metadata"]["opportunity_angle"], "Find repeated manual handoffs in revenue operations.")

    def test_invalid_json_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_venture_product_radar_json("not json")

    def test_parses_v2_funding_source_urls_and_signal_type_fields(self):
        report = {
            **SAMPLE_REPORT,
            "schema_version": "venture-product-radar.v2",
            "funding_rounds": [
                {
                    "company_name": "AI chip maker SambaNova",
                    "amount": "$1B",
                    "announced_date": "2026-07-07",
                    "market_signal": "AI chip maker SambaNova raises $1B at $11B valuation",
                    "source_urls": ["https://techcrunch.com/sambanova"],
                    "confidence": "low",
                    "evidence_gaps": ["official announcement"],
                }
            ],
            "signals": [
                {
                    "signal_type": "funding",
                    "title": "Railway secures $100 million",
                    "summary": "Railway raised a Series B round.",
                    "source_urls": ["https://venturebeat.com/railway"],
                    "confidence": "medium",
                    "signal_score": 57,
                    "signal_strength": "medium",
                    "evidence_gaps": ["verify primary source"],
                }
            ],
        }

        items = parse_venture_product_radar_json(_report_to_text(report))
        signal = next(item for item in items if item["source_type"] == "venture_signal")

        self.assertFalse(any(item["source_type"] == "funding" for item in items))
        self.assertEqual(signal["url"], "https://venturebeat.com/railway")
        self.assertEqual(signal["metadata"]["signal_type"], "funding")
        self.assertEqual(signal["metadata"]["signal_score"], 57)

    def test_watchlist_funding_does_not_enter_generic_content_feed(self):
        report = {
            "schema_version": "venture-product-radar.v2",
            "mode": "radar",
            "topic": "AI funding",
            "generated_at": "2026-07-20T00:00:00Z",
            "products": [],
            "companies": [],
            "signals": [],
            "funding_rounds": [{
                "company_name": "Colossal Biosciences reportedly in talks to",
                "market_signal": "Colossal Biosciences reportedly in talks to raise new capital at $20B-$30B valuation",
                "amount": "$20B",
                "announced_date": "2026-07-19",
                "confidence": "low",
                "source_urls": ["https://techcrunch.com/colossal-valuation"],
            }],
            "source_links": [{
                "url": "https://techcrunch.com/colossal-valuation",
                "source_type": "media",
                "source_name": "TechCrunch",
                "published_at": "2026-07-19",
            }],
        }

        items = parse_venture_product_radar_json(_report_to_text(report))

        self.assertEqual(items, [])

    def test_verified_funding_uses_normalized_contract_in_generic_content(self):
        report = {
            "schema_version": "venture-product-radar.v2",
            "mode": "radar",
            "topic": "AI funding",
            "generated_at": "2026-07-20T00:00:00Z",
            "products": [],
            "companies": [],
            "signals": [],
            "funding_rounds": [{
                "company_name": "Acme AI",
                "title_zh": "Acme AI 宣布完成 2500 万美元 A 轮融资",
                "event_status": "announced",
                "amount_raised": "$25M",
                "valuation": "$200M",
                "round": "Series A",
                "announced_date": "2026-07-18",
                "lead_investors": ["Example Ventures"],
                "confidence": "high",
                "source_urls": ["https://acme.ai/news/series-a"],
                "what_happened": "Acme AI 宣布完成 2500 万美元 A 轮融资。",
                "why_it_matters": "本轮资金将用于企业客户扩张。",
            }],
            "source_links": [{
                "url": "https://acme.ai/news/series-a",
                "source_type": "company_press",
                "source_name": "Acme AI",
                "published_at": "2026-07-18",
            }],
        }

        items = parse_venture_product_radar_json(_report_to_text(report))

        self.assertEqual(len(items), 1)
        funding = items[0]
        self.assertEqual(funding["title"], "Acme AI 宣布完成 2500 万美元 A 轮融资")
        self.assertEqual(funding["metadata"]["pipeline_stage"], "verified")
        self.assertEqual(funding["metadata"]["amount_raised"]["value"], "$25M")
        self.assertEqual(funding["metadata"]["valuation"]["value"], "$200M")
        self.assertEqual(funding["metadata"]["announced_date"]["value"], "2026-07-18")


class ImportVentureProductRadarTest(unittest.TestCase):
    def test_file_archives_report_without_storing_generic_content(self):
        from services import storage
        from services import venture_radar_reports as reports

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content_dir = root / "content"
            content_dir.mkdir()
            report_path = root / "sample-report.json"
            report_path.write_text(_report_to_text(SAMPLE_REPORT), encoding="utf-8")
            venture_dir = root / "venture_radar"

            with patch.object(storage, "CONTENT_DIR", content_dir), \
                    patch.object(reports, "VENTURE_RADAR_DIR", venture_dir), \
                    patch.object(reports, "REPORTS_DIR", venture_dir / "reports"), \
                    patch.object(reports, "INDEX_FILE", venture_dir / "index.json"):
                result = import_venture_product_radar_file(report_path)

            self.assertEqual(result["id"], "sample-report")
            self.assertTrue((venture_dir / "reports" / "sample-report.json").exists())
            self.assertEqual(list(content_dir.glob("*.json")), [])


class WingsbotPromptTest(unittest.TestCase):
    def test_trigger_wingsbot_uses_structured_shared_client_contract(self):
        from services import venture_product_radar_importer as importer

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            artifact = output_dir / "venture-report.json"
            result = Mock()
            with patch.object(importer, "VPR_OUTPUT_DIR", output_dir), \
                    patch.object(importer, "invoke_wingsbot", return_value=result) as invoke, \
                    patch.object(importer, "require_artifact", return_value=artifact) as require:
                prompt = importer._build_wingsbot_prompt(
                    "AI agent startups",
                    sources=["web", "producthunt"],
                    mode="product",
                )
                actual = importer._trigger_wingsbot(
                    "AI agent startups",
                    sources=["web", "producthunt"],
                    mode="product",
                )

        self.assertEqual(actual, artifact)
        call = invoke.call_args
        invocation_dir = Path(call.kwargs["required_artifact_glob"]).parent
        self.assertEqual(invocation_dir.parent, output_dir)
        self.assertIn(f"--output-dir {invocation_dir}", call.args[0])
        self.assertEqual(
            call.kwargs["session_key"],
            "signalforge:venture-product-radar:product:AI agent startups",
        )
        self.assertTrue(call.kwargs["structured"])
        self.assertEqual(call.kwargs["required_skill"], "venture-product-radar")
        self.assertEqual(call.kwargs["required_tools"], ["load_skill", "exec"])
        self.assertEqual(call.kwargs["artifact_mtime_after"], ANY)
        require.assert_called_once_with(result, invocation_dir)

    def test_concurrent_triggers_cannot_select_each_others_artifacts(self):
        from services import venture_product_radar_importer as importer

        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp)

            def fake_invoke(_prompt, **kwargs):
                invocation_dir = Path(kwargs["required_artifact_glob"]).parent
                artifact = invocation_dir / f"{invocation_dir.name}.json"
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text("{}", encoding="utf-8")
                other_artifacts = list(output_root.glob("*/*.json"))
                return Mock(
                    ok=True,
                    artifacts=other_artifacts + [artifact],
                    content="done",
                    error=None,
                )

            def select_first_artifact(result, expected_dir):
                return next(path for path in result.artifacts if path.parent == expected_dir)

            with patch.object(importer, "VPR_OUTPUT_DIR", output_root), \
                    patch.object(importer, "invoke_wingsbot", side_effect=fake_invoke), \
                    patch.object(importer, "require_artifact", side_effect=select_first_artifact):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    artifacts = list(pool.map(importer._trigger_wingsbot, ["OpenAI", "Anthropic"]))

        self.assertEqual(len(set(artifacts)), 2)
        self.assertTrue(all(path.parent != output_root for path in artifacts))

    def test_prompt_includes_mode_and_command_contract(self):
        prompt = _build_wingsbot_prompt("AI coding agents", mode="product", sources=["web", "producthunt"])

        self.assertIn("venture-product-radar", prompt)
        self.assertIn("--mode product", prompt)
        self.assertIn("--sources web,producthunt", prompt)
        self.assertIn("/venture-product", prompt)
        self.assertIn("opportunity_angle", prompt)
        self.assertIn("pipeline_stage", prompt)
        self.assertIn("event_status", prompt)
        self.assertIn("amount_raised", prompt)
        self.assertIn("valuation", prompt)
        self.assertIn("enrichment_tasks", prompt)

    def test_prompt_uses_mode_specific_default_sources(self):
        self.assertIn("--sources web,vc,funding", _build_wingsbot_prompt("AI apps", mode="vc"))
        self.assertIn("--sources web,producthunt", _build_wingsbot_prompt("AI apps", mode="product"))
        self.assertIn("--sources web,funding,vc", _build_wingsbot_prompt("AI apps", mode="finance"))

    def test_run_via_wingsbot_imports_raw_report_archive(self):
        from services.venture_product_radar_importer import run_venture_product_radar_via_wingsbot

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write(_report_to_text(SAMPLE_REPORT))
            path = f.name

        with patch("services.venture_product_radar_importer._trigger_wingsbot", return_value=Path(path)), \
                patch("services.venture_product_radar_importer.import_venture_product_radar_file", return_value={"id": "report"}) as archive_import:
            n = run_venture_product_radar_via_wingsbot("AI agent startups")

        self.assertEqual(n, 1)
        archive_import.assert_called_once_with(Path(path))


class DirectVentureRadarCommandTest(unittest.TestCase):
    def test_direct_command_uses_default_weekly_topic_and_all_sources(self):
        command = build_direct_venture_radar_command()

        self.assertIn("--mode", command)
        self.assertIn("radar", command)
        self.assertIn("--topic", command)
        self.assertIn("AI venture funding product launches startup signals", command)
        self.assertIn("--sources", command)
        self.assertIn("all", command)
        self.assertIn("--lookback-days", command)
        self.assertIn("7", command)

    def test_run_direct_executes_skill_script_and_imports_report_archive(self):
        report_path = Path(tempfile.gettempdir()) / "direct-vpr-report.json"
        report_path.write_text(_report_to_text(SAMPLE_REPORT), encoding="utf-8")

        class Completed:
            stdout = f"{report_path}\n"
            stderr = ""

        with patch("services.venture_product_radar_importer.subprocess.run", return_value=Completed()) as run, \
                patch("services.venture_product_radar_importer.import_venture_product_radar_file", return_value={"id": "direct-vpr-report"}) as archive_import:
            result = run_venture_product_radar_direct()

        self.assertEqual(result["reports_archived"], 1)
        self.assertNotIn("items_imported", result)
        self.assertEqual(result["report_path"], str(report_path))
        self.assertEqual(result["archive"]["id"], "direct-vpr-report")
        self.assertEqual(run.call_args.kwargs["check"], True)
        archive_import.assert_called_once_with(report_path)


if __name__ == "__main__":
    unittest.main()
