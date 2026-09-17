#!/usr/bin/env zsh
set -euo pipefail

SCRIPT_DIR=${0:A:h}
PROJECT_ROOT=${SCRIPT_DIR:h}
PYTHON_BIN="${SIGNALFORGE_PYTHON:-$PROJECT_ROOT/backend/venv/bin/python}"
WINGSBOT_SOURCE="${WINGSBOT_SOURCE:-/Users/shitaosun/Project/AI-Personal/wingsbot}"

PREPARED_WHEEL_DIR=$(mktemp -d "${TMPDIR:-/tmp}/signalforge-wingsbot-wheel.XXXXXX")
trap 'rm -rf "$PREPARED_WHEEL_DIR"' EXIT
"$PYTHON_BIN" -m pip wheel --no-build-isolation --no-deps --wheel-dir "$PREPARED_WHEEL_DIR" "$WINGSBOT_SOURCE"
"$PYTHON_BIN" -m pip uninstall -y wingsbot-ai ks-wingsbot || true
"$PYTHON_BIN" -m pip install -e "$WINGSBOT_SOURCE"
mkdir -p "$PROJECT_ROOT/.wingsbot/workspace"

WINGSBOT_SOURCE="$WINGSBOT_SOURCE" "$PYTHON_BIN" - <<'PY'
import importlib.metadata
import os
from pathlib import Path

import wingsbot
from wingsbot.invoke import WingsbotClient

source = Path(os.environ["WINGSBOT_SOURCE"]).resolve()
origin = Path(wingsbot.__file__).resolve()
if not origin.is_relative_to(source):
    raise SystemExit(f"wingsbot imported from {origin}, expected source under {source}")

try:
    version = importlib.metadata.version("ks-wingsbot")
except importlib.metadata.PackageNotFoundError as exc:
    raise SystemExit("ks-wingsbot distribution metadata is unavailable") from exc

print(f"ks-wingsbot {version} | module: {origin}")
print(f"WingsbotClient import OK: {WingsbotClient.__module__}.{WingsbotClient.__name__}")
PY

print "Wingsbot setup complete. Workspace: $PROJECT_ROOT/.wingsbot/workspace"
