#!/usr/bin/env bash
set -euo pipefail

# Simple build helper for the project
# Usage: ./build.sh [--clean] [--reconfigure] [--jobs N]

CMAKE_ARGS=()
JOBS=0
RECONFIGURE=0
CLEAN=0

while (( "$#" )); do
  case "$1" in
    --clean) CLEAN=1; shift ;;
    --reconfigure) RECONFIGURE=1; shift ;;
    --jobs) JOBS="$2"; shift 2 ;;
    --jobs=*) JOBS="${1#*=}"; shift ;;
    -j) JOBS="$2"; shift 2 ;;
    -j*) JOBS="${1#-j}"; shift ;;
    --) shift; break ;;
    *) CMAKE_ARGS+=("$1"); shift ;;
  esac
done

SCRIPT_DIR="$(pwd)"        # directory where build.sh was called
BUILD_DIR="${SCRIPT_DIR}/build"
TARGET_NAME="my_fastapi_app"

if [ "$CLEAN" -eq 1 ]; then
  echo "Removing ${BUILD_DIR}/ and binary..."
  rm -rf "${BUILD_DIR}" "${SCRIPT_DIR}/${TARGET_NAME}"
  echo "Cleaned."
  exit 0
fi

mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

if [ ! -f CMakeCache.txt ] || [ "$RECONFIGURE" -eq 1 ]; then
  echo "Configuring project with CMake..."
  cmake .. "${CMAKE_ARGS[@]}"
fi

echo "Building..."
if [ "${JOBS}" -gt 0 ]; then
  cmake --build . -- -j"${JOBS}"
else
  cmake --build .
fi

# Locate the binary (CMake puts it in build/ or build/Release etc.)
BIN_PATH=$(find "${BUILD_DIR}" -maxdepth 2 -type f -executable -name "${TARGET_NAME}" | head -n 1 || true)

if [ -z "$BIN_PATH" ]; then
  echo "❌ Could not find built binary '${TARGET_NAME}' in ${BUILD_DIR}"
  exit 1
fi

# Copy to script dir
cp -f "$BIN_PATH" "${SCRIPT_DIR}/${TARGET_NAME}"
echo "✅ Build finished."
echo "Binary copied to: ${SCRIPT_DIR}/${TARGET_NAME}"
