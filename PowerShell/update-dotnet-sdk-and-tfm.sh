#!/bin/bash
set -e

show_help() {
  echo "Usage: $0 [--global-json|-g] [--all|-a] [--help|-h] [--targetframework|-t]"
  echo "  -g, --global-json   Update only global.json with detected SDK version."
  echo "  -a, --all           Do both (default if no flag is given)."
  echo "  -h, --help          Show this help message."
  echo "  -t, --targetframework  Update only TargetFramework in project files."
}

DO_GLOBAL_JSON=false
DO_TARGETFRAMEWORK=false

# Parse flags
if [ $# -eq 0 ]; then
  DO_GLOBAL_JSON=true
  DO_TARGETFRAMEWORK=true
else
  while [[ $# -gt 0 ]]; do
    case $1 in
      -g|--global-json)
        DO_GLOBAL_JSON=true
        ;;
      -a|--all)
        DO_GLOBAL_JSON=true
        DO_TARGETFRAMEWORK=true
        ;;
      -h|--help)
        show_help
        exit 0
        ;;
      -t|--targetframework)
        DO_TARGETFRAMEWORK=true
        ;;
      *)
        echo "Unknown option: $1"
        show_help
        exit 1
        ;;
    esac
    shift
  done
fi

ORIG_DIR=$(pwd)
cd /tmp

# Detect SDK version and compose TFM (target framework moniker)
SDK_VER=$(dotnet --version)
TFM="net$(echo "$SDK_VER" | cut -d. -f1,2)"

# Detect OS and ARCH for RID
OS=$(dotnet --info | grep -i '^[[:space:]]*OS Platform:' | sed 's/^[[:space:]]*OS Platform:[[:space:]]*//' | tr '[:upper:]' '[:lower:]')
ARCH=$(dotnet --info | grep -i '^[[:space:]]*Architecture:' | sed 's/^[[:space:]]*Architecture:[[:space:]]*//')
RID="${OS}-${ARCH}"

cd "$ORIG_DIR"

echo "✅ Detected .NET SDK version: $SDK_VER"
echo "✅ Updating TargetFramework to: $TFM"
echo "✅ Detected Runtime Identifier (RID): $RID"

if $DO_GLOBAL_JSON; then
  echo "🔧 Updating global.json..."
  sed -i "s/\"version\": *\"[^\"]*\"/\"version\": \"${SDK_VER}\"/" global.json
  echo "📝 Updated global.json:"
  grep '"version":' global.json
fi

if $DO_TARGETFRAMEWORK; then
  EXTENSIONS="csproj props psm1 ps1 psd1"
  echo "🔧 Updating only TargetFramework for extensions: $EXTENSIONS"
  for ext in $EXTENSIONS; do
      find . -type f -name "*.${ext}" -exec sed -i "/<TargetFramework[^>]*>net[0-9.]*<\/TargetFramework>/s/net[0-9.]*/${TFM}/" {} +
  done
  echo "📝 Lines updated for TargetFramework (${TFM}):"
  for ext in $EXTENSIONS; do
      find . -type f -name "*.${ext}" -exec grep -H "<TargetFramework[^>]*>${TFM}</TargetFramework>" {} + || true
  done
fi

echo "📝 Updates completed."
