#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
REAL_PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
DEPLOY_SCRIPT="$REAL_PROJECT_ROOT/scripts/deploy-github-pages.zsh"

TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/signalforge-gh-pages-test.XXXXXX")
cleanup() {
  rm -rf -- "$TMP_ROOT"
}
trap cleanup EXIT INT TERM

FAKE_PROJECT_ROOT="$TMP_ROOT/fake-project"
mkdir -p "$FAKE_PROJECT_ROOT/frontend/dist/assets"
cat > "$FAKE_PROJECT_ROOT/frontend/dist/index.html" <<'HTML'
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>SignalForge Test</title>
  </head>
  <body>
    <div id="root">ok</div>
  </body>
</html>
HTML
cat > "$FAKE_PROJECT_ROOT/frontend/dist/assets/app.js" <<'JS'
console.log('signalforge test bundle');
JS

REMOTE_ROOT="$TMP_ROOT/remote.git"
git init --bare "$REMOTE_ROOT" >/dev/null

REAL_BRANCH_BEFORE=$(cd -- "$REAL_PROJECT_ROOT" && git branch --show-current)
REAL_STATUS_BEFORE=$(cd -- "$REAL_PROJECT_ROOT" && git status --porcelain)

PROJECT_ROOT_OVERRIDE="$FAKE_PROJECT_ROOT" \
GITHUB_PAGES_REMOTE="$REMOTE_ROOT" \
GITHUB_PAGES_BRANCH="gh-pages" \
zsh "$DEPLOY_SCRIPT"

CLONE_ROOT="$TMP_ROOT/clone"
git clone --branch gh-pages "$REMOTE_ROOT" "$CLONE_ROOT" >/dev/null

cmp -s "$CLONE_ROOT/index.html" "$CLONE_ROOT/404.html"
[[ -f "$CLONE_ROOT/.nojekyll" ]]
[[ -f "$CLONE_ROOT/assets/app.js" ]]
[[ ! -e "$CLONE_ROOT/frontend" ]]

REAL_BRANCH_AFTER=$(cd -- "$REAL_PROJECT_ROOT" && git branch --show-current)
REAL_STATUS_AFTER=$(cd -- "$REAL_PROJECT_ROOT" && git status --porcelain)

[[ "$REAL_BRANCH_BEFORE" == "$REAL_BRANCH_AFTER" ]]
[[ "$REAL_STATUS_BEFORE" == "$REAL_STATUS_AFTER" ]]

echo "deploy-github-pages test: PASS"
