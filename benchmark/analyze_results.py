#!/usr/bin/env python3
"""Summarize official PLE run output and classify task-level failures."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
from statistics import mean

TASK_IDS = set("""data-hall-mep-routing fire-test-validation-memo data-hall-mep-routing-offset
eor-review-corrections foundation-strategy landscape-sheet-revision data-center-site-model
engineers-estimate-check footing-settlement-verification solar-supplemental-review
solar-witness-test-package frame-extension-method fire-solve-convergence les-mesh-resolution
mv-conveyance-study data-hall-device-takeoff division-26-specifications
heat-rejection-life-cycle-cost cooling-water-flush-plan wind-diaphragm-shear
seismic-diaphragm-shear roof-deck-design fill-compaction-acceptance shoring-design-verification
emergency-spillway-check pre-application-capacity-response permission-to-operate-memo
backfeed-energization-reply lv-cable-sizing""".split())

def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def flatten_records(obj):
    """Yield dicts that look like task summaries, including nested official schemas."""
    if isinstance(obj, dict):
        if any(k in obj for k in ("task_id", "task", "id")) and any(
            k in obj for k in ("score", "reward", "status", "kind", "measured")
        ):
            yield obj
        for v in obj.values():
            yield from flatten_records(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from flatten_records(v)

def task_key(record):
    for key in ("task_id", "id", "task"):
        val = record.get(key)
        if isinstance(val, str):
            if val in TASK_IDS:
                return val
            # Some schemas store task as a dict with an id/name.
        if isinstance(val, dict):
            for k in ("id", "name", "task_id"):
                if val.get(k) in TASK_IDS:
                    return val[k]
    return None

def numeric(v):
    try:
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except (ValueError, TypeError):
        return None

def score_from(record):
    for k in ("score", "normalized_score", "normalized", "mean_score"):
        x = numeric(record.get(k))
        if x is not None:
            return x
    reward = numeric(record.get("reward"))
    scale = numeric(record.get("reward_scale"))
    if reward is not None and scale:
        return reward / scale
    return None

def tokens_from(record):
    tok = record.get("tokens")
    if isinstance(tok, dict):
        return sum(numeric(v) or 0 for v in tok.values())
    for k in ("total_tokens", "tokens_total"):
        n = numeric(record.get(k))
        if n is not None:
            return n
    return None

def seconds_from(record):
    for k in ("seconds", "runtime_sec", "duration_sec", "elapsed_sec"):
        n = numeric(record.get(k))
        if n is not None:
            return n
    return None

def status_from(record):
    return str(record.get("status") or record.get("kind") or "unknown")

def gather_trial_records(run_dir: Path):
    rows = {}
    for attempt in sorted(run_dir.glob("attempt*/jobs/**/result.json")):
        obj = load_json(attempt)
        if not isinstance(obj, dict):
            continue
        # Task ID is often embedded in config.json sibling, task path or directory.
        task = None
        cfg = load_json(attempt.parent / "config.json")
        if isinstance(cfg, dict):
            path = ((cfg.get("task") or {}).get("path") or "")
            task = Path(path).name if path else None
        if task not in TASK_IDS:
            for t in TASK_IDS:
                if t in str(attempt):
                    task = t
                    break
        if task not in TASK_IDS:
            continue
        agent_result = obj.get("agent_result") or {}
        verifier = obj.get("verifier_result") or {}
        rewards = verifier.get("rewards") or {}
        score = numeric(rewards.get("reward"))
        tokens = sum(numeric(agent_result.get(f"n_{k}_tokens")) or 0
                    for k in ("input", "cache", "output"))
        elapsed = None
        exec_data = obj.get("agent_execution") or {}
        if isinstance(exec_data, dict):
            elapsed = numeric(exec_data.get("duration")) or numeric(exec_data.get("seconds"))
        exception = obj.get("exception_info") or {}
        rows[task] = {
            "task_id": task,
            "score": score,
            "status": str(exception.get("exception_type") or ("measured" if score is not None else "unmeasured")),
            "tokens": tokens or None,
            "runtime_seconds": elapsed,
            "failure_detail": str(exception.get("exception_message") or "")[:300],
            "source": str(attempt),
        }
    return rows

def failure_category(row):
    status = (row.get("status") or "").lower()
    detail = (row.get("failure_detail") or "").lower()
    score = row.get("score")
    if score is None:
        if "grader_failed" in status or "grader failed" in status or "verifier" in detail and "timeout" in detail:
            return "grader/evaluator failure (unmeasured)"
        if "timeout" in status or "timeout" in detail or "cutoff" in detail:
            return "timeout/cut-off"
        if "context" in detail and ("overflow" in detail or "length" in detail):
            return "context limit"
        if "rate" in detail or "429" in detail or "quota" in detail:
            return "model rate-limit/quota"
        if "api" in detail or "connection" in detail or "proxy" in detail:
            return "model API/proxy failure"
        return "unmeasured/unknown"
    if score <= 0.00001:
        return "measured zero"
    if score < 0.5:
        return "low partial score (<0.50)"
    if score < 0.8:
        return "partial score (0.50–0.79)"
    if score < 0.99999:
        return "near-full score (0.80–0.99)"
    return "full score"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    args = ap.parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    official = load_json(run_dir / "results.json")
    if official is None:
        raise SystemExit(f"results.json not found or unreadable: {run_dir}")

    rows = {}
    # Prefer official per-task summary records if their schema is recognizable.
    for rec in flatten_records(official):
        tid = task_key(rec)
        if not tid:
            continue
        rows[tid] = {
            "task_id": tid,
            "score": score_from(rec),
            "status": status_from(rec),
            "tokens": tokens_from(rec),
            "runtime_seconds": seconds_from(rec),
            "failure_detail": str(rec.get("error") or rec.get("message") or "")[:300],
            "source": "results.json",
        }
    # Fill gaps from raw Harbor trial folders; useful for exception details and token/runtime.
    raw = gather_trial_records(run_dir)
    for tid, rec in raw.items():
        if tid not in rows or rows[tid].get("score") is None:
            rows[tid] = rec
        else:
            for k in ("tokens", "runtime_seconds", "failure_detail"):
                if rows[tid].get(k) in (None, "", 0) and rec.get(k) not in (None, "", 0):
                    rows[tid][k] = rec[k]

    requested = load_json(run_dir / "requested_tasks.json")
    expected = requested.get("task_ids") if isinstance(requested, dict) else None
    expected_ids = [t for t in expected if t in TASK_IDS] if isinstance(expected, list) else sorted(TASK_IDS)
    for tid in expected_ids:
        if tid not in rows:
            rows[tid] = {
                "task_id": tid, "score": None, "status": "missing task record",
                "tokens": None, "runtime_seconds": None,
                "failure_detail": "No matching official summary or Harbor trial record was found.",
                "source": "missing",
            }
    domains = {
        "Mechanical": {"data-hall-mep-routing","fire-test-validation-memo","data-hall-mep-routing-offset","fire-solve-convergence","les-mesh-resolution","heat-rejection-life-cycle-cost","cooling-water-flush-plan"},
        "Civil": {"foundation-strategy","landscape-sheet-revision","data-center-site-model","engineers-estimate-check","footing-settlement-verification","frame-extension-method","fill-compaction-acceptance","shoring-design-verification","emergency-spillway-check"},
        "Electrical": {"solar-supplemental-review","solar-witness-test-package","mv-conveyance-study","data-hall-device-takeoff","division-26-specifications","pre-application-capacity-response","permission-to-operate-memo","backfeed-energization-reply","lv-cable-sizing"},
    }
    for row in rows.values():
        row["discipline"] = next((d for d, ids in domains.items() if row["task_id"] in ids), "Structural")
        row["failure_category"] = failure_category(row)

    ordered = [rows[t] for t in sorted(rows) if t in expected_ids]
    output = run_dir / "northstar_task_scores.csv"
    fields = ["task_id", "discipline", "score", "status", "runtime_seconds", "tokens", "failure_category", "failure_detail", "source"]
    with output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        for r in ordered:
            w.writerow({k: r.get(k) for k in fields})

    measured = [r for r in ordered if r.get("score") is not None]
    all_scores = [r["score"] for r in measured]
    mean_measured = mean(all_scores) if all_scores else None
    lower_bound = mean([r.get("score") or 0 for r in ordered]) if ordered else None
    missing = sorted(set(expected_ids) - set(rows))
    unmeasured = [r for r in ordered if r.get("score") is None]
    categories = {}
    for r in ordered:
        cat = r["failure_category"]
        categories.setdefault(cat, []).append(r["task_id"])

    report = [
        "# NORTHSTAR-PLE Benchmark Failure Analysis",
        "",
        f"- Run folder: `{run_dir}`",
        f"- Tasks requested in this run: **{len(expected_ids)}**",
        f"- Measured: **{len(measured)}**",
        f"- Unmeasured: **{len(unmeasured)}**",
        f"- Missing records: **{len(missing)}**",
        f"- Mean of measured tasks: **{mean_measured:.4f}**" if mean_measured is not None else "- Mean of measured tasks: not available",
        f"- Conservative 29-task mean (unmeasured/missing counted as 0): **{lower_bound:.4f}**" if lower_bound is not None else "- Conservative mean: not available",
        "",
        "> This is an analysis of the official run outputs. It does not replace the official evaluator or its scoring rules.",
        "",
        "## Task scores",
        "",
        "| Task | Discipline | Score | Status | Runtime (s) | Tokens | Category |",
        "|---|---:|---|---:|---:|---|",
    ]
    for r in ordered:
        s = "—" if r.get("score") is None else f"{r['score']:.4f}"
        rt = "—" if r.get("runtime_seconds") is None else f"{r['runtime_seconds']:.0f}"
        tk = "—" if r.get("tokens") is None else f"{r['tokens']:.0f}"
        report.append(f"| {r['task_id']} | {r['discipline']} | {s} | {r.get('status','')} | {rt} | {tk} | {r['failure_category']} |")
    if missing:
        report += ["", "## Missing task records", "", *[f"- `{t}`" for t in missing]]
    report += ["", "## Failure buckets", ""]
    for cat, ids in sorted(categories.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        report.append(f"- **{cat}** ({len(ids)}): " + ", ".join(f"`{t}`" for t in ids))
    report += ["", "## Recommended review order", "",
               "1. Unmeasured/evaluator faults first: fix environment, judge, proxy, or container issues and re-run.",
               "2. Measured zero-score tasks: inspect deliverables, grader output, tool traces, and task requirements.",
               "3. Low partial scores: identify missed constraints, calculations, required files, or formatting.",
               "4. Improve the weakest discipline/task clusters, then re-run controlled comparisons.",
               "5. Change one major harness/model variable per comparison; keep a dated run log.",
               ""]
    report_path = run_dir / "northstar_failure_analysis.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"CSV: {output}")
    print(f"Report: {report_path}")
    print(f"Tasks requested: {len(expected_ids)}; records: {len(ordered)}; measured: {len(measured)}; unmeasured: {len(unmeasured)}")
    if mean_measured is not None:
        print(f"Measured-task mean: {mean_measured:.4f}; conservative full-set mean: {lower_bound:.4f}")

if __name__ == "__main__":
    main()
