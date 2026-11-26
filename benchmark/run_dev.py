#!/usr/bin/env python3
"""Safe wrapper for the pinned official PLE public-dev evaluator."""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import shutil
import subprocess
import sys

KIT_COMMIT = "5cf736f8b6e6f28eea71cae52de0c3bedaa88fa2"
TASK_IDS = [
    "data-hall-mep-routing",
    "fire-test-validation-memo",
    "data-hall-mep-routing-offset",
    "eor-review-corrections",
    "foundation-strategy",
    "landscape-sheet-revision",
    "data-center-site-model",
    "engineers-estimate-check",
    "footing-settlement-verification",
    "solar-supplemental-review",
    "solar-witness-test-package",
    "frame-extension-method",
    "fire-solve-convergence",
    "les-mesh-resolution",
    "mv-conveyance-study",
    "data-hall-device-takeoff",
    "division-26-specifications",
    "heat-rejection-life-cycle-cost",
    "cooling-water-flush-plan",
    "wind-diaphragm-shear",
    "seismic-diaphragm-shear",
    "roof-deck-design",
    "fill-compaction-acceptance",
    "shoring-design-verification",
    "emergency-spillway-check",
    "pre-application-capacity-response",
    "permission-to-operate-memo",
    "backfeed-energization-reply",
    "lv-cable-sizing",
]

def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kit-dir", type=Path, default=root / ".ple-kit",
                   help="External official kit checkout (default: repo/.ple-kit)")
    p.add_argument("--env-file", type=Path, default=root / "benchmark" / "local.env",
                   help="Local secrets env file; keep it outside Git")
    p.add_argument("--tasks", default="all",
                   help="all or comma-separated official task IDs")
    p.add_argument("--trials", type=int, default=None,
                   help="Parallel trials (omit to let kit choose from resources)")
    p.add_argument("--attempts", type=int, default=3)
    p.add_argument("--out", type=Path, default=None,
                   help="Run output directory; default benchmark/runs/<timestamp>")
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--no-export", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-analysis", action="store_true")
    return p.parse_args()

def main() -> int:
    a = parse_args()
    root = Path(__file__).resolve().parents[1]
    kit = a.kit_dir.expanduser().resolve()
    env_file = a.env_file.expanduser().resolve()
    entry = root.resolve()

    if a.tasks.strip().lower() == "all":
        selected = TASK_IDS
    else:
        selected = [x.strip() for x in a.tasks.split(",") if x.strip()]
        bad = sorted(set(selected) - set(TASK_IDS))
        if bad:
            print("Unknown task IDs: " + ", ".join(bad), file=sys.stderr)
            return 2
    if not selected:
        print("No tasks selected.", file=sys.stderr)
        return 2

    if not (kit / "eval" / "run.py").is_file() or not (kit / "kit" / "__main__.py").is_file():
        print(f"Official kit not found at {kit}. Run benchmark/bootstrap_kit.sh first.", file=sys.stderr)
        return 2
    pin_file = kit / ".git"
    if pin_file.exists():
        try:
            commit = subprocess.check_output(["git", "-C", str(kit), "rev-parse", "HEAD"], text=True).strip()
        except Exception:
            commit = "unknown"
        if commit != KIT_COMMIT:
            print(f"WARNING: kit checkout is {commit}; intended pin is {KIT_COMMIT}", file=sys.stderr)

    if not env_file.is_file():
        print(f"Missing env file: {env_file}\nCopy benchmark/local.env.example to benchmark/local.env and fill authorized credentials.", file=sys.stderr)
        return 2

    docker = shutil.which("docker")
    uv = shutil.which("uv")
    if not docker or not uv:
        print("Missing prerequisite: Docker and uv must both be installed.", file=sys.stderr)
        return 2
    try:
        subprocess.run([docker, "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError:
        print("Docker daemon is not running or not accessible.", file=sys.stderr)
        return 2

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = a.out.expanduser().resolve() if a.out else root / "benchmark" / "runs" / f"northstar-dev-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    command = [uv, "run", "python", "eval/run.py", str(entry), "--env-file", str(env_file),
               "--tasks", ",".join(selected), "--attempts", str(a.attempts), "--out", str(out)]
    if a.trials is not None:
        if a.trials < 1:
            print("--trials must be at least 1", file=sys.stderr)
            return 2
        command.extend(["--trials", str(a.trials)])
    if a.rebuild:
        command.append("--rebuild")
    if a.no_export:
        command.append("--no-export")

    print(f"Tasks: {len(selected)} / 29")
    print(f"Official kit: {kit}")
    print(f"Entry: {entry}")
    print(f"Env file: {env_file} (contents are not displayed)")
    print(f"Output: {out}")
    print("Command:", " ".join(command))
    if a.dry_run:
        print("DRY RUN: command not executed.")
        return 0

    print("\nStarting official PLE evaluator. Interrupt with Ctrl-C for graceful Harbor cleanup.")
    try:
        code = subprocess.run(command, cwd=kit).returncode
    except KeyboardInterrupt:
        print("Interrupted by user.", file=sys.stderr)
        code = 130

    result_json = out / "results.json"
    if result_json.is_file() and not a.skip_analysis:
        analyzer = root / "benchmark" / "analyze_results.py"
        subprocess.run([sys.executable, str(analyzer), str(out)], check=False)
    print(f"\nRun directory: {out}")
    print(f"Official evaluator exit code: {code}")
    print("A nonzero exit can mean unmeasured tasks or artifact validation problems; inspect the report.")
    return code

if __name__ == "__main__":
    raise SystemExit(main())
