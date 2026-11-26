# NORTHSTAR-PLE Phase 1: Official dev benchmark

This directory is the local integration layer for Google's **official** PLE kit.
The evaluator itself is cloned into `.ple-kit/` at a verified commit and is not
vendored into the NORTHSTAR submission.

## Official status

As of the setup snapshot, the official kit is pinned to commit:

`5cf736f8b6e6f28eea71cae52de0c3bedaa88fa2`

The official dev-set manifest revision recorded by the kit is
`b3857a3fea39a695e18f845d4a88f29442e96e75`. The official kit always downloads
the dataset revision it specifies/records; it should be the source of truth.

## Requirements

- Linux or WSL2 is preferred (keep both repos in the Linux filesystem).
- Docker daemon running.
- `uv`.
- Harbor 0.20.0 with websockets.
- HF access approved for the gated dataset and a read token.
- Authorized Google Cloud Vertex AI access and model proxy setup.
- Judge endpoint (the kit's model proxy is the recommended route).

For the full 29-task run, allow significant resources. Official guidance recommends
at least 6 CPUs and 16.25 GB memory for a task slot; 12 MCP/world task images
can take about 17 GB each. Run on a dedicated machine, with adequate storage.

## Setup

From NORTHSTAR repo root:

```bash
bash benchmark/bootstrap_kit.sh
bash benchmark/install_prereqs.sh
cp benchmark/local.env.example benchmark/local.env
# Edit benchmark/local.env with your own authorized credentials.
```

Set up the official Google model proxy according to `.ple-kit/kit/model_proxy`
and official `docs/models.md`. Do not paste credentials into chat or commit them.
If using Vertex, complete Google Cloud ADC login and set the project/proxy key in
your shell. The proxy key and HF token belong in `benchmark/local.env`.

## Dry-run

```bash
python benchmark/run_dev.py --dry-run
python benchmark/run_dev.py --tasks data-center-site-model,engineers-estimate-check --dry-run
```

## Official kit checks before the benchmark

```bash
uv run --directory .ple-kit python -m kit validate ..
uv run --directory .ple-kit python -m kit check ..
```

Run `kit check` only after credentials and Docker are configured. It builds and
smoke-tests the entry in the official runtime environment.

## Run the full dev set

```bash
python benchmark/run_dev.py --tasks all
```

Start with a 2-task diagnostic subset before spending model credits:

```bash
python benchmark/run_dev.py --tasks data-center-site-model,engineers-estimate-check --trials 1
```

The official runner writes the task run record and, unless `--no-export` is used,
exports official `artifacts/` into the submission repo. The wrapper then creates:

- `northstar_task_scores.csv`
- `northstar_failure_analysis.md`

inside the run folder. The analyzer reads official `results.json` and raw Harbor
trial records; it never fabricates scores. Missing/unmeasured tasks are shown
separately and counted as zero in the conservative 29-task mean.

## Repeat runs and regrading

Use a separate output folder for each run:

```bash
python benchmark/run_dev.py --tasks all --out benchmark/runs/neon-baseline-1
```

For model comparisons, clone the submission directory or make a separate branch,
change only `submission.yaml` model selection, and run the same task subset with
the same evaluator/dataset revision and settings. Save the commit hash in your
experiment notes. Do not compare scores from different task sets.

When the judge has failed but harness outputs are intact, use the official kit's
regrade option directly:

```bash
uv run --directory .ple-kit python eval/run.py --regrade benchmark/runs/<run-name> --env-file benchmark/local.env
```

Offline artifact regrade:

```bash
uv run --directory .ple-kit python eval/run.py --artifacts ..
```

Official readiness:

```bash
uv run --directory .ple-kit python -m kit check ..
```

Do not submit until the official check reports `ready to submit`, the artifacts
are committed, and the submission rules/competition availability are confirmed.

## Failure triage

- **unmeasured/evaluator faults**: Docker image build, missing dataset, judge API,
  proxy, connectivity, or runner faults. Fix these before interpreting score.
- **not started**: model did not begin producing output. Inspect `serve.log`,
  `egress.log`, protocol transcript, proxy response and `trajectory.json`.
- **timeout/cut-off**: inspect progress, MCP latency, tool-loop count, and
  whether final verification/deliverable creation began.
- **context limit**: inspect prompt/history growth and summarization.
- **measured zero/low score**: compare required deliverables and grader output
  with the task prompt. Prioritize constraints, units, safety checks, file
  format/schema, and deliverable completeness.

Keep only genuine official results. Do not edit `artifacts/manifest.json` or
manually create/alter task score artifacts.
