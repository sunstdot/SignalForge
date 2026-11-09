#!/bin/sh
# Install this bundle into a DeepSeek Harness profile from a local checkout.
# Usage: ./install.sh [profile]   (default: desktop)
set -eu

PROFILE="${1:-desktop}"
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
if [ -z "${DSH_BIN:-}" ]; then
	if command -v dsh >/dev/null 2>&1; then
		DSH_BIN=$(command -v dsh)
	else
		DSH_BIN="/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh"
	fi
fi

if [ ! -x "$DSH_BIN" ]; then
	echo "dsh CLI not found at: $DSH_BIN" >&2
	echo "Set DSH_BIN to the launcher inside DeepSeek Harness.app." >&2
	exit 1
fi

"$DSH_BIN" plugin --profile "$PROFILE" add "link:$HERE"
echo
echo "Installed dsh-signalforge into profile: $PROFILE"
echo "Refresh the Harness page (or restart the app), then open 今日 AI 情报 in the sidebar."
