#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# resolve-upstream-tag.sh
#
# Resolves a Python version (e.g., "3.14.5" or "3.15.0-beta.1") to the
# corresponding source-code tag from the actions/python-versions upstream
# repository by querying its GitHub releases.
#
# Usage:
#   ./scripts/resolve-upstream-tag.sh <python-version>
#
# Examples:
#   ./scripts/resolve-upstream-tag.sh 3.14.5       # → 3.14.5-25647354415
#   ./scripts/resolve-upstream-tag.sh 3.15.0-beta.1 # → 3.15.0-beta.1-25533511631
#
# Requires: curl, jq, and gh (GitHub CLI). Uses gh's stored token for auth.
# ------------------------------------------------------------------------------
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <python-version>" >&2
  exit 1
fi

PYTHON_VERSION="$1"
UPSTREAM_REPO="actions/python-versions"

# Retrieve the GitHub token from gh CLI for authenticated curl requests
GH_TOKEN="$(gh auth token)"

# Query the upstream releases API and find the release whose name
# matches the requested Python version exactly.
TAG_NAME=$(curl -sL -H "Authorization: Bearer $GH_TOKEN" \
  "https://api.github.com/repos/${UPSTREAM_REPO}/releases" \
  | jq -r --arg ver "$PYTHON_VERSION" \
    '[.[] | select(.name == $ver)] | first | .tag_name // empty')

if [ -z "$TAG_NAME" ]; then
  echo "ERROR: Could not find upstream release matching Python version '$PYTHON_VERSION' in $UPSTREAM_REPO" >&2
  exit 1
fi

echo "$TAG_NAME"
