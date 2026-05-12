#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
source "${REPO_ROOT}/python-versions/trivy-assets.sh"

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
  local curl_auth_args=()

  if [ -n "${GITHUB_TOKEN:-}" ]; then
    curl_auth_args=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
  elif [ -n "${GH_TOKEN:-}" ]; then
    curl_auth_args=(-H "Authorization: Bearer ${GH_TOKEN}")
  fi

  headers_file="$(mktemp)"
  body_file="$(mktemp)"

  curl_exit=0
  http_code="$(curl -sSL \
    -D "$headers_file" \
    -o "$body_file" \
    -w '%{http_code}' \
    "${curl_auth_args[@]}" \
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
    trivy_version="${TRIVY_VERSION#v}"
    while IFS= read -r arch; do
      asset_ok=0
      asset="$(trivy_asset_name "$trivy_version" "$arch")"
      url="https://github.com/aquasecurity/trivy/releases/download/${TRIVY_VERSION}/${asset}"

      for attempt in 1 2 3; do
        if request_release_tag "$url" -H "User-Agent: curl" -H "Accept: application/octet-stream"; then
          asset_ok=1
          break
        fi
        rm -f "$RELEASE_TAG_HEADERS_FILE" "$RELEASE_TAG_RESPONSE_FILE"
        if [ "$attempt" -lt 3 ]; then
          sleep 1
        fi
      done

      if [ "$asset_ok" -ne 1 ]; then
        echo "ERROR: Trivy asset ${asset} for ${TRIVY_VERSION} is unavailable." >&2
        echo "URL: ${url}" >&2
        echo "HTTP status: ${RELEASE_TAG_HTTP_CODE:-000}; curl exit: ${RELEASE_TAG_CURL_EXIT:-1}" >&2
        if [ -f "${RELEASE_TAG_RESPONSE_FILE:-}" ]; then
          tr -d '\r' < "$RELEASE_TAG_RESPONSE_FILE" | sed -n '1,10p' >&2 || true
        fi
        rm -f "${RELEASE_TAG_HEADERS_FILE:-}" "${RELEASE_TAG_RESPONSE_FILE:-}"
        exit 1
      fi
    done < <(trivy_supported_arches)
    exit 0
    ;;

  checksums)
    # Verify pinned checksums file contains entries for expected assets
    trivy_version="${TRIVY_VERSION#v}"
    while IFS= read -r arch; do
      asset="$(trivy_asset_name "$trivy_version" "$arch")"
      if ! awk -v asset="$asset" '{sub(/\r$$/, "", $2)} $2 == asset && length($1) == 64 && $1 ~ /^[0-9a-f]+$/ {found=1} END {exit found ? 0 : 1}' python-versions/trivy-checksums.txt; then
        echo "ERROR: Missing pinned checksum for ${asset} in python-versions/trivy-checksums.txt" >&2
        exit 1
      fi
    done < <(trivy_supported_arches)
    ;;

  *)
    usage
    ;;
esac

exit 0
