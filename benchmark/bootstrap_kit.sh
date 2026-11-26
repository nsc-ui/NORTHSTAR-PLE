#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KIT_DIR="${PLE_KIT_DIR:-$ROOT/.ple-kit}"
KIT_COMMIT="5cf736f8b6e6f28eea71cae52de0c3bedaa88fa2"

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git is required to bootstrap the official PLE kit." >&2
  exit 2
fi

if [[ -d "$KIT_DIR/.git" ]]; then
  git -C "$KIT_DIR" fetch --depth 1 origin "$KIT_COMMIT"
  git -C "$KIT_DIR" checkout --detach "$KIT_COMMIT"
else
  mkdir -p "$(dirname "$KIT_DIR")"
  git clone --filter=blob:none https://github.com/google-research/ple.git "$KIT_DIR"
  git -C "$KIT_DIR" fetch --depth 1 origin "$KIT_COMMIT"
  git -C "$KIT_DIR" checkout --detach "$KIT_COMMIT"
fi

ACTUAL="$(git -C "$KIT_DIR" rev-parse HEAD)"
if [[ "$ACTUAL" != "$KIT_COMMIT" ]]; then
  echo "ERROR: official kit pin mismatch: expected $KIT_COMMIT, got $ACTUAL" >&2
  exit 3
fi

echo "Official PLE kit checked out at $ACTUAL"
echo "Kit directory: $KIT_DIR"
echo "This is an external tool checkout; do not add it to the NORTHSTAR submission."
