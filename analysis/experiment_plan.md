# NORTHSTAR PLE experiment plan

**Do not report planned experiments as completed.**

## A. Baseline (required)
- Run the official 29-task dev set with Gemini 4 Neon, three repetitions if compute permits.
- Record task reward, task/run ID, model ID, elapsed seconds, token counts, approximate USD cost, tool count, finish/cancel status, deliverable validation and retries.
- Record dataset revision, harness SHA, environment, kit version, and all settings.
- Preserve only the permitted evaluation artifacts/aggregate metrics; do not retain hidden task content.

## B. Cross-model comparison
Use the exact same harness commit and configuration on at least two eligible models. Compare task-mean score, variance, cost, latency, tool-call count, completion rate and failure category. Model choice is a measured trade-off; the public model leaderboard's agent-level scores are not direct evidence for NORTHSTAR.

## C. Verification-loop ablation
Compare (1) full checklist + independent audit + critique/repair, (2) checklist/audit without explicit critique, and (3) no final audit. Use the same model, tasks, and budget. Analyze changes in reward, omitted outputs, wrong paths/formats, calculation errors, and cost. Revert the ablation configuration after tests.

## D. Context and tools ablation
Compare context compaction on/off and MCP schema-search on/off where task services exist. Measure context-limit failures, tool selection failures, tool call count, token/cost and score. Do not dump the complete MCP catalog into context in the full configuration.

## E. Failure taxonomy
Classify per-task issues with primary and secondary categories: (1) source/file omission, (2) requirement/format/path miss, (3) engineering reasoning/calculation/units, (4) drawing/CAD/spreadsheet interoperability, (5) tool/MCP/API errors, (6) verification/validation gap, (7) time/context/token limit, (8) task/evaluator fault. Distinguish agent outcomes from evaluator faults and unmeasured runs using official eval classifications.

## F. Cost/score plot
Use actual task-level data and aggregate costs/mean reward by configuration. Plot one point per configuration, include error bars or run variance if repeated, annotate the exact model and commit, and do not compare estimates to measured costs. Populate `analysis/score_cost.csv` only after verified run logs are parsed.
