#!/usr/bin/env bash
set -euo pipefail
# Run from any directory. Set PLE_REPO to a local google-research/ple clone.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLE_REPO="${PLE_REPO:-$(cd "$ROOT/.." && pwd)/ple-official}"
if [[ ! -d "$PLE_REPO/kit" || ! -f "$PLE_REPO/eval/run.py" ]]; then
  echo "ERROR: Official PLE repository not found at $PLE_REPO" >&2
  echo "Clone google-research/ple, accept the dataset terms, set HF_TOKEN and model-proxy environment, then set PLE_REPO." >&2
  exit 2
fi
cd "$PLE_REPO"
uv run python -m kit check "$ROOT" --cancel-test
uv run python eval/run.py "$ROOT"
uv run python -m kit artifacts "$ROOT"
uv run python eval/run.py --artifacts "$ROOT"
echo "Official validation sequence completed. Inspect logs and artifacts before claiming submission readiness."
