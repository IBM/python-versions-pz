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
# In CI: set GITHUB_TOKEN or GH_TOKEN for authenticated requests.
# Locally: runs without auth (unauthenticated requests work but have lower
#          GitHub API rate limits).
# ------------------------------------------------------------------------------
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <python-version>" >&2
  exit 1
fi

PYTHON_VERSION="$1"
UPSTREAM_REPO="actions/python-versions"

# Use GITHUB_TOKEN or GH_TOKEN if available, otherwise run unauthenticated
TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
AUTH_HEADER=""
if [ -n "$TOKEN" ]; then
  AUTH_HEADER="-H \"Authorization: Bearer $TOKEN\""
fi

# Query the upstream releases API and find the release whose name
# matches the requested Python version exactly.
TAG_NAME=$(eval curl -sL "$AUTH_HEADER" \
  "https://api.github.com/repos/${UPSTREAM_REPO}/releases" \
  | jq -r --arg ver "$PYTHON_VERSION" \
    '[.[] | select(.name == $ver)] | first | .tag_name // empty')

if [ -z "$TAG_NAME" ]; then
  echo "ERROR: Could not find upstream release matching Python version '$PYTHON_VERSION' in $UPSTREAM_REPO" >&2
  exit 1
fi

echo "$TAG_NAME"
