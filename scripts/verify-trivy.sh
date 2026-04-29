#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 {tag|checksums} [TRIVY_VERSION]" >&2
  echo "If TRIVY_VERSION is omitted the script will read .trivyversion or default to v0.70.0." >&2
  exit 2
}

if [ $# -lt 1 ]; then
  usage
fi

cmd="$1"; shift

if [ $# -ge 1 ]; then
  TRIVY_VERSION="$1"
else
  TRIVY_VERSION_FILE=".trivyversion"
  if [ -f "${TRIVY_VERSION_FILE}" ]; then
    TRIVY_VERSION="$(cat "${TRIVY_VERSION_FILE}")"
  else
    TRIVY_VERSION="v0.70.0"
  fi
fi

case "$cmd" in
  tag)
    # Use GitHub token when available to avoid unauthenticated rate limits in CI
    url="https://api.github.com/repos/aquasecurity/trivy/releases/tags/${TRIVY_VERSION}"
    if [ -n "${GITHUB_TOKEN:-}" ]; then
      curl -fsSL \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        -H "User-Agent: curl" \
        -H "Accept: application/vnd.github+json" \
        "$url" >/dev/null || {
        echo "ERROR: Trivy release ${TRIVY_VERSION} not found. Set a valid TRIVY_VERSION (or update .trivyversion, e.g. v0.70.0)." >&2
        exit 1
      }
    else
      curl -fsSL \
        -H "User-Agent: curl" \
        -H "Accept: application/vnd.github+json" \
        "$url" >/dev/null || {
        echo "ERROR: Trivy release ${TRIVY_VERSION} not found. Set a valid TRIVY_VERSION (or update .trivyversion, e.g. v0.70.0)." >&2
        exit 1
      }
    fi
    ;;

  checksums)
    # Verify pinned checksums file contains entries for expected assets
    trivy_version="${TRIVY_VERSION#v}"
    for arch in 64bit ARM64 PPC64LE s390x; do
      asset="trivy_${trivy_version}_Linux-${arch}.tar.gz"
      if ! awk -v asset="$asset" '{sub(/\r$$/, "", $2)} $2 == asset && $1 ~ /^[0-9a-f]{64}$/ {found=1} END {exit found ? 0 : 1}' python-versions/trivy-checksums.txt; then
        echo "ERROR: Missing pinned checksum for ${asset} in python-versions/trivy-checksums.txt" >&2
        exit 1
      fi
    done
    ;;

  *)
    usage
    ;;
esac

exit 0
