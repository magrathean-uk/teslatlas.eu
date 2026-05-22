#!/usr/bin/env bash
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
OUT_DIR="$ROOT_DIR/out"
SITE_ASSET_NAME="$(python3 "$ROOT_DIR/scripts/release_manifest.py" site-asset)"
CHECKSUM_ASSET_NAME="$(python3 "$ROOT_DIR/scripts/release_manifest.py" checksum-asset)"

rm -rf "$DIST_DIR" "$OUT_DIR"
mkdir -p "$DIST_DIR" "$OUT_DIR"

tar \
  --exclude='./.git' \
  --exclude='./.github' \
  --exclude='./dist' \
  --exclude='./out' \
  --exclude='./runtime' \
  --exclude='./scripts' \
  --exclude='./ops' \
  --exclude='./deploy.sh' \
  --exclude='./README.md' \
  --exclude='./.gitignore' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  -cf - -C "$ROOT_DIR" . | tar -xf - -C "$OUT_DIR"

if [[ ! -f "$OUT_DIR/index.html" ]]; then
  echo "release requires index.html at repository root" >&2
  exit 1
fi

find "$ROOT_DIR/scripts" -type d -name __pycache__ -prune -exec rm -rf {} +

tar -czf "$DIST_DIR/$SITE_ASSET_NAME" \
  -C "$ROOT_DIR" \
  out \
  deploy.sh \
  scripts \
  ops

pushd "$DIST_DIR" >/dev/null
sha256sum "$SITE_ASSET_NAME" > "$CHECKSUM_ASSET_NAME"
popd >/dev/null
