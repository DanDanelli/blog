#!/usr/bin/env bash
#
# apply-patches.sh — clone AWS's upstream at the pinned commit, drop in the credential
# shim, and apply the blueprint patches. Produces a buildable tree.
#
# Usage:  ./apply-patches.sh [target-dir]
#         target-dir defaults to ./upstream
#
# Requires: git. Does not build — see UPSTREAM.md for the build step.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCHES="$HERE/patches"
SHIM_PKG="$HERE/../credential-shim/credential_shim"

ORIGIN="https://github.com/aws-solutions-library-samples/guidance-for-claude-code-with-amazon-bedrock.git"
BASE_COMMIT="d209253c029dbe7481a3d9f1403f02624e380185"
TARGET="${1:-$HERE/upstream}"

if [[ -e "$TARGET" ]]; then
  echo "Target '$TARGET' already exists — remove it or pass a fresh path." >&2
  exit 1
fi

echo "==> Cloning upstream at $BASE_COMMIT"
git clone "$ORIGIN" "$TARGET"
git -C "$TARGET" checkout "$BASE_COMMIT"

echo "==> Dropping in the credential shim at source/credential_shim/"
mkdir -p "$TARGET/source/credential_shim"
cp "$SHIM_PKG/"*.py "$TARGET/source/credential_shim/"

echo "==> Applying patches"
git -C "$TARGET" apply --verbose \
  "$PATCHES/codebuild-windows.yaml.patch" \
  "$PATCHES/package.py.patch" \
  "$PATCHES/distribute.py.patch"

echo
echo "Done. The buildable tree is at: $TARGET"
echo "Next: cd \"$TARGET/source\" && poetry install   (then ccwb init/deploy/package/distribute)"
echo "See patches/UPSTREAM.md for the Nuitka build and the _rust verification step."
