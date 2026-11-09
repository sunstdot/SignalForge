#!/bin/sh
# Publish a clean snapshot of this package to a GitHub repository.
#
# Usage: ./scripts/publish-github.sh <owner/repo>
# Requires: npm, git, and SSH push access to github.com.
set -eu

REPO="${1:-${GITHUB_REPO:-}}"
if [ -z "$REPO" ]; then
	echo "usage: $0 <owner/repo>" >&2
	echo "example: $0 sunstdot/signalforge-dsh" >&2
	exit 1
fi

REMOTE="${GITHUB_REMOTE:-git@github.com:$REPO.git}"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
VERSION=$(node -p "require('$ROOT/package.json').version")
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

cd "$ROOT"
npm pack --pack-destination "$TMP" >/dev/null
TARBALL="$TMP/dsh-signalforge-$VERSION.tgz"
tar -xzf "$TARBALL" -C "$TMP"

WORK="$TMP/repo"
if git clone "$REMOTE" "$WORK" 2>/dev/null; then
	find "$WORK" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
else
	mkdir -p "$WORK"
	cd "$WORK"
	git init -b main >/dev/null
	git remote add origin "$REMOTE"
fi

cp -R "$TMP/package/." "$WORK/"
[ -f "$ROOT/.gitignore" ] && cp "$ROOT/.gitignore" "$WORK/.gitignore"
[ -d "$ROOT/.github" ] && cp -R "$ROOT/.github" "$WORK/.github"

cd "$WORK"
git add -A
if git diff --cached --quiet; then
	echo "no changes for dsh-signalforge v$VERSION"
	exit 0
fi
git commit -m "dsh-signalforge v$VERSION"
git push -u origin HEAD:main
echo "pushed dsh-signalforge v$VERSION to github.com/$REPO"
