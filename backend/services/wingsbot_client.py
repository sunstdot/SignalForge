import atexit
import os
import threading
from pathlib import Path
from typing import Any

from wingsbot.invoke import WingsbotClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]

_client: WingsbotClient | None = None
_client_lock = threading.Lock()
_atexit_registered = False


def _get_client() -> WingsbotClient:
    global _atexit_registered, _client

    with _client_lock:
        if _client is None:
            options: dict[str, Any] = {
                "workspace": PROJECT_ROOT / ".wingsbot" / "workspace"
            }
            config_path = os.environ.get("SIGNALFORGE_WINGSBOT_CONFIG")
            if config_path:
                options["config_path"] = config_path
            _client = WingsbotClient(**options)
            if not _atexit_registered:
                atexit.register(close_wingsbot_client)
                _atexit_registered = True
        return _client


def invoke_wingsbot(content: str, **kwargs: Any):
    return _get_client().invoke(content, **kwargs)


async def ainvoke_wingsbot(content: str, **kwargs: Any):
    return await _get_client().ainvoke(content, **kwargs)


def close_wingsbot_client() -> None:
    global _client

    with _client_lock:
        client = _client
        _client = None
    if client is not None:
        client.close()


def require_artifact(result: Any, output_dir: Path) -> Path:
    error = getattr(result, "error", None)
    content = str(getattr(result, "content", ""))[:500]

    if not getattr(result, "ok", False):
        raise RuntimeError(f"Wingsbot invocation failed: {error}; content: {content}")

    artifacts = getattr(result, "artifacts", None)
    if not artifacts:
        raise RuntimeError(f"Wingsbot returned no artifacts: {error}; content: {content}")

    artifact = Path(artifacts[0])
    resolved_artifact = artifact.resolve()
    resolved_output_dir = output_dir.resolve()
    if not resolved_artifact.is_relative_to(resolved_output_dir):
        raise RuntimeError(
            f"Wingsbot artifact is outside output directory: {error}; content: {content}"
        )
    if resolved_artifact.suffix.lower() != ".json":
        raise RuntimeError(
            f"Wingsbot artifact is not JSON: {error}; content: {content}"
        )
    if not resolved_artifact.is_file():
        raise RuntimeError(
            f"Wingsbot artifact does not exist: {error}; content: {content}"
        )
    return artifact
