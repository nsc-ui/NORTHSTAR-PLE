# Validation Record

Last updated: 2026-11-25 UTC

## Local verification
- `python -m compileall -q .` — PASS
- `python scripts/check_entry.py` — PASS (15/15 structural, model, license, asset, and writeup checks)
- `python tests_unit.py` — PASS (MCP SSE multiline/session handling and catalog search)
- `python tests_context.py` — PASS (history compression retains task, summary, recent turn, and usage accounting)
- `python tests_cancel.py` — PASS (cancel frame during tool call; best-effort `done` returned)
- `python tests_smoke.py` — PASS (mocked model: tool call, evaluator protocol exchange, final audit, done; 3 model calls)
- `python analysis/plot_results.py` — PASS (placeholder figures are generated; empty datasets are explicitly marked)
- `submission.yaml` — model API selected as `google-cloud/gemini-4-neon`; listed in the current official model catalog. Model choice has not been benchmarked by NORTHSTAR.
- Cover asset — present in `media/cover.jpg` for the Kaggle Media Gallery.
- Architecture — implementation diagram present under `figures/`.
- Writeup draft — present and under the 2,000-word cap; it contains placeholders and explicit pending-evaluation disclosure.

## Repository and CI
- Public GitHub repository — PASS: `https://github.com/nsc-ui/NORTHSTAR-PLE`
- Git bundle — present as `NORTHSTAR-PLE.bundle`.
- Docker runtime — configured with `Dockerfile`, `compose.yaml`, `.dockerignore`, and `.env.example`.
- GitHub Actions — PASS: CI workflow completed successfully for commit `264e67e93d329650ee38642b9e9ce44aa3a29ab7`.
- Docker image build — not run locally because Docker is unavailable in this sandbox; the CI workflow includes a Docker build job.

## Official minimum checks: NOT PASSED / BLOCKED
- `uv run python -m kit check NORTHSTAR-PLE` — BLOCKED: the official PLE repository/kit is absent from this environment, Docker is unavailable locally, and `python -m kit` is unavailable.
- `uv run python eval/run.py NORTHSTAR-PLE` — BLOCKED: the official evaluator is absent, gated HF dataset access/token is not configured, and local model proxy/API credentials are not configured.
- `uv run python -m kit artifacts NORTHSTAR-PLE` — NOT RUN: official `artifacts/` have not been generated.
- `uv run python eval/run.py --artifacts NORTHSTAR-PLE` — NOT RUN: no official artifacts exist.
- Kaggle Writeup — NOT SUBMITTED: no Kaggle submission action is available in this environment.

No PLE scores, measured costs, task-level failures, or official pass claims are included. Do not submit until the blocked checks and artifacts are completed in the official environment.
