#!/usr/bin/env bash

trivy_supported_arches() {
  printf '%s\n' 64bit ARM64 PPC64LE s390x
}

trivy_arch_for_targetarch() {
  local target_arch="$1"

  case "$target_arch" in
    amd64) printf '%s\n' 64bit ;;
    arm64) printf '%s\n' ARM64 ;;
    ppc64le) printf '%s\n' PPC64LE ;;
    s390x) printf '%s\n' s390x ;;
    *) return 1 ;;
  esac
}

trivy_asset_name() {
  local trivy_version="$1"
  local trivy_arch="$2"

  printf 'trivy_%s_Linux-%s.tar.gz\n' "${trivy_version#v}" "$trivy_arch"
}