#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT_INPUT="${PROJECT_ROOT_OVERRIDE:-$SCRIPT_DIR/..}"
PROJECT_ROOT=$(cd -- "$PROJECT_ROOT_INPUT" && pwd)
DIST_DIR="$PROJECT_ROOT/frontend/dist"
REMOTE="${GITHUB_PAGES_REMOTE:-git@github.com:sunstdot/token-burn.git}"
BRANCH="${GITHUB_PAGES_BRANCH:-gh-pages}"

if ! command -v git >/dev/null 2>&1; then
  echo "deploy-github-pages: git command not found" >&2
  exit 1
fi

if [[ ! -f "$DIST_DIR/index.html" ]]; then
  echo "deploy-github-pages: missing $DIST_DIR/index.html" >&2
  exit 1
fi

TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/signalforge-gh-pages.XXXXXX")
cleanup() {
  rm -rf -- "$TMP_ROOT"
}
trap cleanup EXIT INT TERM

PUBLISH_DIR="$TMP_ROOT/publish"
mkdir -p "$PUBLISH_DIR"
cp -R "$DIST_DIR"/. "$PUBLISH_DIR"/
cp "$PUBLISH_DIR/index.html" "$PUBLISH_DIR/404.html"
touch "$PUBLISH_DIR/.nojekyll"

git -C "$PUBLISH_DIR" init >/dev/null
git -C "$PUBLISH_DIR" checkout --orphan "$BRANCH" >/dev/null 2>&1
git -C "$PUBLISH_DIR" add .
git -C "$PUBLISH_DIR" -c user.name='SignalForge Pages Bot' -c user.email='pages@signalforge.local' commit -m "Publish static site to $BRANCH" >/dev/null
git -C "$PUBLISH_DIR" remote add origin "$REMOTE"
git -C "$PUBLISH_DIR" push --force origin "HEAD:$BRANCH"

echo "deploy-github-pages: published $DIST_DIR to $REMOTE ($BRANCH)"
