#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is missing. Install it from https://docs.astral.sh/uv/ and rerun." >&2
  exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is missing. Install Docker Engine/Desktop and ensure it is running." >&2
  exit 2
fi
docker info >/dev/null

uv tool install harbor==0.20.0 --with websockets
echo "Prerequisites checked. Harbor 0.20.0 installed (or already present)."
