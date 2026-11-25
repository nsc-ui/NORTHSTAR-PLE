# NORTHSTAR-PLE Competition Requirements and Validation Plan

This entry must follow the official PLE instructions. It is a WebSocket server (`serve.py`) that uses only its Google-sponsored model endpoint and the evaluator protocol to operate in the isolated task container. Never copy task content into logs or external storage.

## Required deliverable structure
- `submission.yaml`: valid entry name, supported `google-cloud/...` model API, install and serve commands.
- `serve.py`: bind `0.0.0.0:$PORT`, accept protocol-v1 task frame within 120 seconds, WebSocket max frame 16 MiB.
- `harness.py`: task execution loop using evaluator `exec`, `read_file`, `write_file`, `http` actions; MCP servers are task-local only.
- `artifacts/`: generated ONLY by official `eval/run.py`, containing all 29 public dev-task outputs and manifest; never fabricate or hand-create.
- Tests, prompts, analysis, figures, README, license, writeup.

## Required checks (must run in official repository)
1. `python -m kit check ../NORTHSTAR-PLE` (with Docker, includes schema, build, model, listen, smoke; run `--cancel-test` too if feasible).
2. `uv run python eval/run.py ../NORTHSTAR-PLE` (29 public dev tasks; record run logs and output score).
3. `uv run python -m kit artifacts ../NORTHSTAR-PLE` (artifact validation).
4. `uv run python eval/run.py --artifacts ../NORTHSTAR-PLE` (offline regrade when judge is available).
5. Rerun the dev set whenever harness files change, commit harness + artifacts together, ensure manifest hash is current.
6. Push the final commit to a GitHub repository; Kaggle submission instructions are followed when enabled.

## Engineering-agent workflow
Read task instructions and recursively inventory all files. Build a deliverable checklist and evidence ledger with file/page/sheet/row citations. Resolve ambiguity explicitly; show assumptions, units, calculations, and code/standard references. Use reproducible calculation scripts and independent cross-checks. Save requested files early; run validation and inspect outputs. Finish with a concise `done.final_message` naming outputs. Do not claim engineering approval or construction readiness.

## Competition scoring/report
Writeup max 2,000 words; include three visuals: architecture, measured score-vs-cost, and measured failure breakdown. No benchmark score, cost, failure rate, or test pass may be claimed without logs/results. Commit SHA must be exactly 40 hex characters and match the artifact-generating commit.

## Current blockers
The local environment currently lacks Docker and the official kit/dev dataset. No dev artifacts or benchmark results may be generated until those dependencies, dataset access, and model credentials are available.
