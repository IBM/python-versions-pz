#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
source "${REPO_ROOT}/python-versions/trivy-assets.sh"

usage() {
  echo "Usage: $0 [TRIVY_VERSION] [--output FILE] [--version-file FILE]" >&2
  echo "Defaults: output=python-versions/trivy-checksums.txt, version-file=.trivyversion" >&2
  exit 2
}

output_file="${REPO_ROOT}/python-versions/trivy-checksums.txt"
version_file="${REPO_ROOT}/.trivyversion"
trivy_version=""

while [ $# -gt 0 ]; do
  case "$1" in
    --output)
      [ $# -ge 2 ] || usage
      output_file="$2"
      shift 2
      ;;
    --version-file)
      [ $# -ge 2 ] || usage
      version_file="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      if [ -n "$trivy_version" ]; then
        usage
      fi
      trivy_version="$1"
      shift
      ;;
  esac
done

if [ -z "$trivy_version" ]; then
  if [ -f "$version_file" ]; then
    trivy_version="$(cat "$version_file")"
  else
    trivy_version="v0.70.0"
  fi
fi

tmp_checksums="$(mktemp)"
tmp_output="$(mktemp)"
trap 'rm -f "$tmp_checksums" "$tmp_output"' EXIT

curl -fsSL \
  -H "User-Agent: curl" \
  -o "$tmp_checksums" \
  "https://github.com/aquasecurity/trivy/releases/download/${trivy_version}/trivy_${trivy_version#v}_checksums.txt"

{
  echo "# Pinned Trivy SHA256 checksums for Linux tar.gz artifacts."
  echo "# Format: <sha256>  <filename>"
  echo "# Source: https://github.com/aquasecurity/trivy/releases"
  echo

  while IFS= read -r arch; do
    asset="$(trivy_asset_name "$trivy_version" "$arch")"
    line="$(awk -v asset="$asset" '$2 == asset && length($1) == 64 && $1 ~ /^[0-9a-f]+$/ {print $1 "  " $2; found=1; exit} END {if (!found) exit 1}' "$tmp_checksums")" || {
      echo "ERROR: Missing checksum for ${asset} in upstream checksums file." >&2
      exit 1
    }
    echo "$line"
  done < <(trivy_supported_arches)
} > "$tmp_output"

printf '%s\n' "$trivy_version" > "$version_file"
mv "$tmp_output" "$output_file"

echo "Updated ${version_file} and ${output_file} for ${trivy_version}"