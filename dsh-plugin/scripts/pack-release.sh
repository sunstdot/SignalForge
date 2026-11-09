#!/bin/sh
# Build the GitHub Release assets: a tarball plus SHA256SUMS.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
VERSION=$(node -p "require('$ROOT/package.json').version")
DIST="$ROOT/dist"
mkdir -p "$DIST"
rm -f "$DIST"/dsh-signalforge-*.tgz "$DIST/SHA256SUMS"

cd "$ROOT"
npm pack --pack-destination "$DIST" >/dev/null
cd "$DIST"
if command -v shasum >/dev/null 2>&1; then
	shasum -a 256 "dsh-signalforge-$VERSION.tgz" > SHA256SUMS
else
	sha256sum "dsh-signalforge-$VERSION.tgz" > SHA256SUMS
fi
echo "release assets:"
ls -lh "dsh-signalforge-$VERSION.tgz" SHA256SUMS
echo
echo "upload both files to the GitHub Release for v$VERSION"
