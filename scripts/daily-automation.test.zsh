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
assert_contains '/bin/zsh "$PROJECT_ROOT/scripts/deploy-github-pages.zsh"'

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

# ─── cd "$FRONTEND_DIR" count & order guards ──────────────────────────────
cd_count=$(grep -cF 'cd "$FRONTEND_DIR"' "$DAILY_SCRIPT" || true)
if (( cd_count < 3 )); then
  echo "daily-automation test: expected cd \"\$FRONTEND_DIR\" at least 3 times (Step 2/3/4), found $cd_count" >&2
  exit 1
fi

# Collect the line numbers for each explicit cd "$FRONTEND_DIR" block
step2_cd_line=$(grep -nF 'cd "$FRONTEND_DIR"' "$DAILY_SCRIPT" | head -1 | cut -d: -f1)
step3_cd_line=$(grep -nF 'cd "$FRONTEND_DIR"' "$DAILY_SCRIPT" | sed -n '2p' | cut -d: -f1)
step4_cd_line=$(grep -nF 'cd "$FRONTEND_DIR"' "$DAILY_SCRIPT" | sed -n '3p' | cut -d: -f1)

if [[ -z "$step2_cd_line" || -z "$step3_cd_line" || -z "$step4_cd_line" ]]; then
  echo "daily-automation test: could not locate 3 occurrences of cd \"\$FRONTEND_DIR\"" >&2
  exit 1
fi

if (( step2_cd_line >= step3_cd_line )); then
  echo "daily-automation test: cd \"\$FRONTEND_DIR\" for Step 2 must come before Step 3 ($step2_cd_line >= $step3_cd_line)" >&2
  exit 1
fi

if (( step3_cd_line >= step4_cd_line )); then
  echo "daily-automation test: cd \"\$FRONTEND_DIR\" for Step 3 must come before Step 4 ($step3_cd_line >= $step4_cd_line)" >&2
  exit 1
fi

echo "daily-automation test: PASS"
