# Wingsbot integration

SignalForge embeds Wingsbot through its Python invoke API. It does not start a Wingsbot CLI, channel, or HTTP gateway.

## Setup

From the SignalForge project root, run:

```zsh
scripts/setup-wingsbot.zsh
```

The script uses `backend/venv/bin/python`, removes both historical package names, installs the local Wingsbot checkout in editable mode, and creates `.wingsbot/workspace`. Override either path when needed:

```zsh
SIGNALFORGE_PYTHON=/path/to/python \
WINGSBOT_SOURCE=/path/to/wingsbot \
scripts/setup-wingsbot.zsh
```

The setup only verifies installation and imports; it does not call a model.

## Configuration

Wingsbot reads `~/.wingsbot/config.json` by default. Keep API keys in that user-level configuration, environment variables, or a secret manager—never commit them to this repository. To use another config with SignalForge, set `SIGNALFORGE_WINGSBOT_CONFIG=/path/to/config.json` before starting the backend.

## SignalForge shared adapter

Application code should reuse the thread-safe adapter in `backend/services/wingsbot_client.py`:

```python
from services.wingsbot_client import invoke_wingsbot

answer = invoke_wingsbot(
    "Summarize this topic",
    session_key="signalforge:summary:topic-id",
)
```

Async callers should use `ainvoke_wingsbot(...)`; it preserves the host event loop rather than blocking it. The adapter owns one long-lived client and the backend lifespan closes it with `close_wingsbot_client()`. Call that function during shutdown in other hosts as well.

Calls with the same `session_key` retain conversation history and execute serially. Different keys isolate history and may execute concurrently. Use a stable key for intentional multi-turn conversations and a unique task-derived key for independent background jobs.

## Structured execution contracts

For workflows that require actual tool use or files, request a structured result and validate it instead of trusting natural-language claims:

```python
result = invoke_wingsbot(
    "Generate the report",
    session_key="signalforge:report:job-123",
    structured=True,
    required_skill="last30days",
    required_tools=["load_skill"],
    required_artifact_glob="/absolute/output/*.json",
    artifact_mtime_after=started_at,
)

if not result.ok:
    raise RuntimeError(result.error)
print(result.content, result.tools_used, result.artifacts)
```

`structured=True` returns a `DirectResult` with content, tool-call details, artifacts, success state, and an error. Keep artifact globs narrowly scoped and validate returned paths before consuming them.

## One-shot direct use

Outside the SignalForge backend, use the client as a context manager so its background thread and MCP connections are always released:

```python
from pathlib import Path
from wingsbot.invoke import WingsbotClient

with WingsbotClient(workspace=Path(".wingsbot/workspace")) as client:
    answer = client.invoke("Explain this repository", session_key="invoke:one-shot")
    print(answer)
```

For async code, use `async with WingsbotClient(...)` and `await client.ainvoke(...)`. Explicit clients can also be closed with `client.close()` or `await client.aclose()`; shutdown is idempotent.

## Troubleshooting

If imports fail or resolve outside the editable checkout, the setup and backend are probably using different interpreters. Run `scripts/setup-wingsbot.zsh` with `SIGNALFORGE_PYTHON` set to the exact interpreter that launches SignalForge, then inspect `python -c 'import sys, wingsbot; print(sys.executable, wingsbot.__file__)'` with that same interpreter. Also confirm `WINGSBOT_SOURCE` exists and contains the expected checkout. A missing or invalid config raises a configuration error; fix the configured path or JSON rather than placing credentials in the repository.
