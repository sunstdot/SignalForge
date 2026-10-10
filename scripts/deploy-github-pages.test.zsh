#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
REAL_PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
DEPLOY_SCRIPT="$REAL_PROJECT_ROOT/scripts/deploy-github-pages.zsh"

DEPLOY_SCRIPT_SOURCE=$(cat -- "$DEPLOY_SCRIPT")
[[ "$DEPLOY_SCRIPT_SOURCE" == *'git@github.com:sunstdot/SignalForge.git'* ]]

TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/signalforge-gh-pages-test.XXXXXX")
cleanup() {
  rm -rf -- "$TMP_ROOT"
}
trap cleanup EXIT INT TERM

FAKE_PROJECT_ROOT="$TMP_ROOT/fake-project"
FAKE_FRONTEND_DIR="$FAKE_PROJECT_ROOT/frontend"
BUILD_LOG="$TMP_ROOT/build.log"
mkdir -p "$FAKE_FRONTEND_DIR/dist/assets" "$TMP_ROOT/bin"
cat > "$FAKE_FRONTEND_DIR/package.json" <<'JSON'
{
  "scripts": {
    "build:pages": "fake-pages-build"
  }
}
JSON
cat > "$FAKE_FRONTEND_DIR/dist/index.html" <<'HTML'
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
cat > "$FAKE_FRONTEND_DIR/dist/assets/app.js" <<'JS'
console.log('signalforge test bundle');
JS

cat > "$TMP_ROOT/bin/pnpm" <<'ZSH'
#!/bin/zsh
set -euo pipefail

print -r -- "$*" > "$FAKE_BUILD_LOG"
rm -rf dist
mkdir -p dist/assets dist/api-static/dates dist/api-static/venture-radar
asset_path="/SignalForge/assets/app.js"
if [[ "${FAKE_BUILD_MODE:-complete}" == "wrong-base" ]]; then
  asset_path="/assets/app.js"
fi
cat > dist/index.html <<HTML
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>SignalForge Pages Test</title>
    <script type="module" src="$asset_path"></script>
  </head>
  <body>
    <div id="root">fresh pages build</div>
  </body>
</html>
HTML
cat > dist/assets/app.js <<'JS'
console.log('fresh signalforge pages bundle');
JS
print -r -- '{"dates":["2026-08-10"]}' > dist/api-static/dates.json
print -r -- '{"weeks":[{"week":"2026-W33"}]}' > dist/api-static/venture-radar/weeks.json
if [[ "${FAKE_BUILD_MODE:-complete}" != "missing-opportunities" ]]; then
  print -r -- '{"dates":["2026-08-10"]}' > dist/api-static/dates/opportunities.json
fi
ZSH
chmod +x "$TMP_ROOT/bin/pnpm"

REMOTE_ROOT="$TMP_ROOT/remote.git"
git init --bare "$REMOTE_ROOT" >/dev/null

REAL_BRANCH_BEFORE=$(cd -- "$REAL_PROJECT_ROOT" && git branch --show-current)
REAL_STATUS_BEFORE=$(cd -- "$REAL_PROJECT_ROOT" && git status --porcelain)

PATH="$TMP_ROOT/bin:$PATH" \
FAKE_BUILD_LOG="$BUILD_LOG" \
PROJECT_ROOT_OVERRIDE="$FAKE_PROJECT_ROOT" \
GITHUB_PAGES_REMOTE="$REMOTE_ROOT" \
GITHUB_PAGES_BRANCH="gh-pages" \
zsh "$DEPLOY_SCRIPT"

if [[ "$(<"$BUILD_LOG")" != "run build:pages" ]]; then
  echo "deploy-github-pages test: expected pnpm run build:pages" >&2
  exit 1
fi

CLONE_ROOT="$TMP_ROOT/clone"
git clone --branch gh-pages "$REMOTE_ROOT" "$CLONE_ROOT" >/dev/null

cmp -s "$CLONE_ROOT/index.html" "$CLONE_ROOT/404.html"
[[ -f "$CLONE_ROOT/.nojekyll" ]]
[[ -f "$CLONE_ROOT/assets/app.js" ]]
[[ -f "$CLONE_ROOT/api-static/dates.json" ]]
[[ -f "$CLONE_ROOT/api-static/dates/opportunities.json" ]]
[[ -f "$CLONE_ROOT/api-static/venture-radar/weeks.json" ]]
grep -qF '/SignalForge/assets/app.js' "$CLONE_ROOT/index.html"
[[ ! -e "$CLONE_ROOT/frontend" ]]

INVALID_REMOTE_ROOT="$TMP_ROOT/invalid-remote.git"
INVALID_OUTPUT="$TMP_ROOT/invalid-deploy.log"
git init --bare "$INVALID_REMOTE_ROOT" >/dev/null

if PATH="$TMP_ROOT/bin:$PATH" \
  FAKE_BUILD_LOG="$BUILD_LOG" \
  FAKE_BUILD_MODE="missing-opportunities" \
  PROJECT_ROOT_OVERRIDE="$FAKE_PROJECT_ROOT" \
  GITHUB_PAGES_REMOTE="$INVALID_REMOTE_ROOT" \
  GITHUB_PAGES_BRANCH="gh-pages" \
  zsh "$DEPLOY_SCRIPT" >"$INVALID_OUTPUT" 2>&1; then
  echo "deploy-github-pages test: expected missing cache to stop deployment" >&2
  exit 1
fi

grep -qF "missing " "$INVALID_OUTPUT"
grep -qF "api-static/dates/opportunities.json" "$INVALID_OUTPUT"
if git --git-dir="$INVALID_REMOTE_ROOT" show-ref --verify --quiet refs/heads/gh-pages; then
  echo "deploy-github-pages test: invalid build must not create gh-pages" >&2
  exit 1
fi

WRONG_BASE_REMOTE_ROOT="$TMP_ROOT/wrong-base-remote.git"
WRONG_BASE_OUTPUT="$TMP_ROOT/wrong-base-deploy.log"
git init --bare "$WRONG_BASE_REMOTE_ROOT" >/dev/null

if PATH="$TMP_ROOT/bin:$PATH" \
  FAKE_BUILD_LOG="$BUILD_LOG" \
  FAKE_BUILD_MODE="wrong-base" \
  PROJECT_ROOT_OVERRIDE="$FAKE_PROJECT_ROOT" \
  GITHUB_PAGES_REMOTE="$WRONG_BASE_REMOTE_ROOT" \
  GITHUB_PAGES_BRANCH="gh-pages" \
  zsh "$DEPLOY_SCRIPT" >"$WRONG_BASE_OUTPUT" 2>&1; then
  echo "deploy-github-pages test: expected wrong base path to stop deployment" >&2
  exit 1
fi

grep -qF "/SignalForge/" "$WRONG_BASE_OUTPUT"
if git --git-dir="$WRONG_BASE_REMOTE_ROOT" show-ref --verify --quiet refs/heads/gh-pages; then
  echo "deploy-github-pages test: wrong base build must not create gh-pages" >&2
  exit 1
fi

REAL_BRANCH_AFTER=$(cd -- "$REAL_PROJECT_ROOT" && git branch --show-current)
REAL_STATUS_AFTER=$(cd -- "$REAL_PROJECT_ROOT" && git status --porcelain)

[[ "$REAL_BRANCH_BEFORE" == "$REAL_BRANCH_AFTER" ]]
[[ "$REAL_STATUS_BEFORE" == "$REAL_STATUS_AFTER" ]]

echo "deploy-github-pages test: PASS"
