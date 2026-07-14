#!/usr/bin/env bash
set -euo pipefail

FILE="${1:-dist/index.html}"
ABS_FILE="$(pwd)/${FILE}"

BROWSERS=(
  "/mnt/c/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"
  "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
  "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
)

die() {
  echo "ERROR: $*" >&2
  exit 1
}

if [[ "$FILE" == "-h" || "$FILE" == "--help" ]]; then
  echo "Usage: open-html.sh [file]"
  echo "  Opens an HTML file in the Windows browser from WSL."
  echo "  Defaults to dist/index.html"
  exit 0
fi

command -v wslpath &>/dev/null || die "wslpath not found — are you running inside WSL?"

[[ -f "$ABS_FILE" ]] || die "File not found: $ABS_FILE"

for browser in "${BROWSERS[@]}"; do
  if [[ -f "$browser" ]]; then
    "$browser" "$(wslpath -w "$ABS_FILE")"
    exit 0
  fi
done

die "No supported browser found. Tried: ${BROWSERS[*]}"