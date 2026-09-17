import asyncio
import importlib
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))


class PlaceholderClient:
    pass


invoke_module = types.ModuleType("wingsbot.invoke")
invoke_module.WingsbotClient = PlaceholderClient
wingsbot_package = types.ModuleType("wingsbot")
wingsbot_package.__path__ = []

with patch.dict(
    sys.modules,
    {"wingsbot": wingsbot_package, "wingsbot.invoke": invoke_module},
):
    mod = importlib.import_module("services.wingsbot_client")


class FakeClient:
    instances = []

    def __init__(self, **kwargs):
        self.options = kwargs
        self.calls = []
        self.async_calls = []
        self.close_count = 0
        self.__class__.instances.append(self)

    def invoke(self, content, **kwargs):
        self.calls.append((content, kwargs))
        return f"sync:{content}"

    async def ainvoke(self, content, **kwargs):
        self.async_calls.append((content, kwargs))
        return f"async:{content}"

    def close(self):
        self.close_count += 1


class WingsbotClientTest(unittest.TestCase):
    def setUp(self):
        mod.close_wingsbot_client()
        FakeClient.instances.clear()

    def tearDown(self):
        mod.close_wingsbot_client()

    def test_sync_calls_share_client_forward_arguments_and_cleanup_is_idempotent(self):
        with patch.object(mod, "WingsbotClient", FakeClient):
            self.assertEqual(
                mod.invoke_wingsbot("one", session_key="signalforge:a"),
                "sync:one",
            )
            mod.invoke_wingsbot("two", session_key="signalforge:b")

            self.assertEqual(len(FakeClient.instances), 1)
            client = FakeClient.instances[0]
            self.assertEqual(
                client.options,
                {"workspace": PROJECT_ROOT / ".wingsbot" / "workspace"},
            )
            self.assertEqual(
                client.calls,
                [
                    ("one", {"session_key": "signalforge:a"}),
                    ("two", {"session_key": "signalforge:b"}),
                ],
            )

            mod.close_wingsbot_client()
            mod.close_wingsbot_client()
            self.assertEqual(client.close_count, 1)

            mod.invoke_wingsbot("three")
            self.assertEqual(len(FakeClient.instances), 2)

    def test_config_override_and_async_call_are_forwarded(self):
        config_path = "/tmp/signalforge-wingsbot.yaml"
        with (
            patch.object(mod, "WingsbotClient", FakeClient),
            patch.dict(os.environ, {"SIGNALFORGE_WINGSBOT_CONFIG": config_path}),
        ):
            result = asyncio.run(
                mod.ainvoke_wingsbot("hello", session_key="signalforge:async")
            )

        self.assertEqual(result, "async:hello")
        client = FakeClient.instances[0]
        self.assertEqual(client.options["config_path"], config_path)
        self.assertEqual(
            client.async_calls,
            [("hello", {"session_key": "signalforge:async"})],
        )


class RequireArtifactTest(unittest.TestCase):
    def test_returns_existing_json_artifact_inside_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            report = output_dir / "report.json"
            report.write_text("{}", encoding="utf-8")
            result = SimpleNamespace(
                ok=True, error=None, content="done", artifacts=[str(report)]
            )

            self.assertEqual(mod.require_artifact(result, output_dir), report)

    def test_rejects_failed_result_and_limits_content_in_error(self):
        result = SimpleNamespace(
            ok=False,
            error="provider failed",
            content="x" * 600,
            artifacts=[],
        )

        with self.assertRaises(RuntimeError) as raised:
            mod.require_artifact(result, Path("unused"))

        message = str(raised.exception)
        self.assertIn("provider failed", message)
        self.assertIn("x" * 500, message)
        self.assertNotIn("x" * 501, message)

    def test_rejects_result_without_artifacts(self):
        result = SimpleNamespace(ok=True, error=None, content="done", artifacts=[])
        with self.assertRaises(RuntimeError):
            mod.require_artifact(result, Path("unused"))

    def test_rejects_missing_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            result = SimpleNamespace(
                ok=True,
                error=None,
                content="done",
                artifacts=[str(output_dir / "missing.json")],
            )
            with self.assertRaises(RuntimeError):
                mod.require_artifact(result, output_dir)

    def test_rejects_non_json_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            report = output_dir / "report.txt"
            report.write_text("not json", encoding="utf-8")
            result = SimpleNamespace(
                ok=True, error=None, content="done", artifacts=[str(report)]
            )
            with self.assertRaises(RuntimeError):
                mod.require_artifact(result, output_dir)

    def test_rejects_artifact_outside_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_dir = root / "output"
            output_dir.mkdir()
            report = root / "outside.json"
            report.write_text("{}", encoding="utf-8")
            result = SimpleNamespace(
                ok=True, error=None, content="done", artifacts=[str(report)]
            )
            with self.assertRaises(RuntimeError):
                mod.require_artifact(result, output_dir)


if __name__ == "__main__":
    unittest.main()
