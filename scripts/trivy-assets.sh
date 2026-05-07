#!/usr/bin/env bash

trivy_supported_arches() {
  printf '%s\n' 64bit ARM64 PPC64LE s390x
}

trivy_asset_name() {
  local trivy_version="$1"
  local trivy_arch="$2"

  printf 'trivy_%s_Linux-%s.tar.gz\n' "${trivy_version#v}" "$trivy_arch"
}