#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/trivy-assets.sh"

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 TRIVY_VERSION TARGETARCH CHECKSUM_FILE" >&2
  exit 2
fi

trivy_version="$1"
target_arch="$2"
checksum_file="$3"
download_path="/tmp/trivy.tar.gz"
extract_dir="/tmp"

get_github_token() {
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    printf '%s' "$GITHUB_TOKEN"
    return 0
  fi

  if [ -n "${GH_TOKEN:-}" ]; then
    printf '%s' "$GH_TOKEN"
    return 0
  fi

  if [ -n "${GITHUB_TOKEN_FILE:-}" ] && [ -f "${GITHUB_TOKEN_FILE}" ]; then
    tr -d '\r\n' < "${GITHUB_TOKEN_FILE}"
    return 0
  fi

  if [ -f /run/secrets/github_token ]; then
    tr -d '\r\n' < /run/secrets/github_token
    return 0
  fi

  return 1
}

if ! trivy_arch="$(trivy_arch_for_targetarch "$target_arch")"; then
  echo "Unsupported TARGETARCH for Trivy install: ${target_arch}" >&2
  exit 1
fi

trivy_archive="$(trivy_asset_name "$trivy_version" "$trivy_arch")"
trivy_sha256="$(awk -v archive="${trivy_archive}" 'BEGIN{found=""} {sub(/\r$/, "", $2)} $2 == archive && length($1) == 64 && $1 ~ /^[0-9a-f]+$/ {found=$1} END{print found}' "$checksum_file")"

if [ -z "$trivy_sha256" ]; then
  echo "No pinned Trivy checksum for ${trivy_archive}. Update python-versions/trivy-checksums.txt." >&2
  exit 1
fi

trivy_base_url="https://github.com/aquasecurity/trivy/releases/download/${trivy_version}"
curl_auth_args=()
if github_token="$(get_github_token || true)" && [ -n "$github_token" ]; then
  curl_auth_args=(-H "Authorization: Bearer ${github_token}")
fi

curl -fsSLo "$download_path" "${curl_auth_args[@]}" "${trivy_base_url}/${trivy_archive}"
echo "${trivy_sha256}  ${download_path}" | sha256sum -c -
tar -xzf "$download_path" -C "$extract_dir" trivy
install -m 0755 "${extract_dir}/trivy" /usr/local/bin/trivy
rm -f "${extract_dir}/trivy" "$download_path"
trivy --version