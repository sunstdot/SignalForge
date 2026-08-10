#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
DAILY_SCRIPT="$PROJECT_ROOT/scripts/daily-automation.zsh"

if [[ ! -f "$DAILY_SCRIPT" ]]; then
  echo "daily-automation test: missing $DAILY_SCRIPT" >&2
  exit 1
fi

SCRIPT_SOURCE=$(<"$DAILY_SCRIPT")

assert_contains() {
  local needle="$1"
  if ! grep -qF -- "$needle" <<< "$SCRIPT_SOURCE"; then
    echo "daily-automation test: missing required snippet: $needle" >&2
    exit 1
  fi
}

first_match_line() {
  local needle="$1"
  local line
  line=$(grep -nF -m 1 -- "$needle" "$DAILY_SCRIPT" | cut -d: -f1 || true)
  if [[ -z "$line" ]]; then
    echo "daily-automation test: could not find line for: $needle" >&2
    exit 1
  fi
  echo "$line"
}

assert_contains "npm run build:static"
assert_contains "/usr/local/bin/jinx dist -e staging"
assert_contains "npm run build:pages"
assert_contains "deploy-github-pages.zsh"

static_line=$(first_match_line "npm run build:static")
staging_line=$(first_match_line "/usr/local/bin/jinx dist -e staging")
pages_build_line=$(first_match_line "npm run build:pages")
pages_deploy_line=$(first_match_line "deploy-github-pages.zsh")

if (( static_line >= staging_line )); then
  echo "daily-automation test: expected static build before staging ($static_line >= $staging_line)" >&2
  exit 1
fi

if (( staging_line >= pages_build_line )); then
  echo "daily-automation test: expected staging before pages build ($staging_line >= $pages_build_line)" >&2
  exit 1
fi

if (( pages_build_line >= pages_deploy_line )); then
  echo "daily-automation test: expected pages build before pages deploy ($pages_build_line >= $pages_deploy_line)" >&2
  exit 1
fi

echo "daily-automation test: PASS"
