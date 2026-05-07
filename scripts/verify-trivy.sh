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

request_release_tag() {
  local url="$1"
  local headers_file body_file http_code curl_exit

  headers_file="$(mktemp)"
  body_file="$(mktemp)"

  curl_exit=0
  http_code="$(curl -sSL \
    -D "$headers_file" \
    -o "$body_file" \
    -w '%{http_code}' \
    "$@")" || curl_exit=$?

  if [ "$curl_exit" -eq 0 ] && [ "$http_code" = "200" ]; then
    rm -f "$headers_file" "$body_file"
    return 0
  fi

  RELEASE_TAG_HTTP_CODE="$http_code"
  RELEASE_TAG_CURL_EXIT="$curl_exit"
  RELEASE_TAG_RESPONSE_FILE="$body_file"
  RELEASE_TAG_HEADERS_FILE="$headers_file"
  return 1
}

case "$cmd" in
  tag)
    url="https://api.github.com/repos/aquasecurity/trivy/releases/tags/${TRIVY_VERSION}"
    curl_args=(
      "$url"
      -H "User-Agent: curl"
      -H "Accept: application/vnd.github+json"
    )
    if [ -n "${GITHUB_TOKEN:-}" ]; then
      curl_args+=( -H "Authorization: Bearer ${GITHUB_TOKEN}" )
    fi

    for attempt in 1 2 3; do
      if request_release_tag "${curl_args[@]}"; then
        exit 0
      fi
      rm -f "$RELEASE_TAG_HEADERS_FILE" "$RELEASE_TAG_RESPONSE_FILE"
      sleep 1
    done

    echo "ERROR: Trivy release ${TRIVY_VERSION} lookup failed via GitHub API." >&2
    echo "HTTP status: ${RELEASE_TAG_HTTP_CODE}; curl exit: ${RELEASE_TAG_CURL_EXIT}" >&2
    if [ -z "${GITHUB_TOKEN:-}" ]; then
      echo "GITHUB_TOKEN was not set. In CI, pass the step-scoped token explicitly." >&2
    elif [ "$RELEASE_TAG_HTTP_CODE" = "403" ]; then
      echo "GitHub API returned 403. Verify token availability, token permissions, and API rate limits." >&2
    elif [ "$RELEASE_TAG_HTTP_CODE" = "404" ]; then
      echo "Release tag ${TRIVY_VERSION} was not found. Update .trivyversion if needed." >&2
    fi
    if [ -f "$RELEASE_TAG_RESPONSE_FILE" ]; then
      tr -d '\r' < "$RELEASE_TAG_RESPONSE_FILE" | sed -n '1,10p' >&2 || true
    fi
    rm -f "$RELEASE_TAG_HEADERS_FILE" "$RELEASE_TAG_RESPONSE_FILE"
    exit 1
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
