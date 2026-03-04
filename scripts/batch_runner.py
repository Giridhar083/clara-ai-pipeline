"""
batch_runner.py
---------------
Runs Pipeline A on all 5 demo transcripts, then Pipeline B on all 5 onboarding
transcripts. Produces a full batch summary report.

Usage:
  python scripts/batch_runner.py
  python scripts/batch_runner.py --demo-dir inputs/demo --onboarding-dir inputs/onboarding
  python scripts/batch_runner.py --pipeline a   # only run Pipeline A
  python scripts/batch_runner.py --pipeline b   # only run Pipeline B
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pipeline_a import run_pipeline_a
from pipeline_b import run_pipeline_b
from task_tracker import get_task_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("batch_runner")


def run_batch(
    demo_dir: str = "inputs/demo",
    onboarding_dir: str = "inputs/onboarding",
    pipeline: str = "all"  # "a", "b", or "all"
) -> dict:
    """
    Process all demo + onboarding transcripts.
    Pipeline A must complete before Pipeline B.

    Returns a summary report dict.
    """
    demo_dir = Path(demo_dir)
    onboarding_dir = Path(onboarding_dir)
    start_time = datetime.utcnow()

    results_a = []
    results_b = []
    errors = []

    # ── Pipeline A: all demo files ───────────────────────────────────────
    if pipeline in ("a", "all"):
        demo_files = sorted(demo_dir.glob("*.txt"))
        logger.info(f"╔══════════════════════════════════════╗")
        logger.info(f"║  PIPELINE A — {len(demo_files)} demo files           ║")
        logger.info(f"╚══════════════════════════════════════╝")

        if not demo_files:
            logger.warning(f"No .txt files found in {demo_dir}")

        for i, f in enumerate(demo_files, 1):
            logger.info(f"  [{i}/{len(demo_files)}] Processing: {f.name}")
            try:
                result = run_pipeline_a(str(f))
                result["source_file"] = f.name
                results_a.append(result)
                logger.info(f"  ✓ Success: {result['company_name']}")
            except Exception as e:
                error = {
                    "source_file": f.name,
                    "pipeline": "A",
                    "error": str(e),
                    "status": "failed"
                }
                errors.append(error)
                logger.error(f"  ✗ FAILED: {f.name} — {e}")

            # Small delay to respect Groq rate limits on free tier
            if i < len(demo_files):
                time.sleep(2)

    # ── Pipeline B: all onboarding files ────────────────────────────────
    if pipeline in ("b", "all"):
        onboarding_files = sorted(onboarding_dir.glob("*.txt"))
        logger.info(f"╔══════════════════════════════════════╗")
        logger.info(f"║  PIPELINE B — {len(onboarding_files)} onboarding files  ║")
        logger.info(f"╚══════════════════════════════════════╝")

        if not onboarding_files:
            logger.warning(f"No .txt files found in {onboarding_dir}")

        for i, f in enumerate(onboarding_files, 1):
            logger.info(f"  [{i}/{len(onboarding_files)}] Processing: {f.name}")
            try:
                result = run_pipeline_b(str(f))
                result["source_file"] = f.name
                results_b.append(result)
                logger.info(f"  ✓ Success: {result['company_name']} — "
                            f"{result['total_changes']} change(s)")
            except Exception as e:
                error = {
                    "source_file": f.name,
                    "pipeline": "B",
                    "error": str(e),
                    "status": "failed"
                }
                errors.append(error)
                logger.error(f"  ✗ FAILED: {f.name} — {e}")

            if i < len(onboarding_files):
                time.sleep(2)

    # ── Build summary ────────────────────────────────────────────────────
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    summary = {
        "batch_run_at": start_time.isoformat() + "Z",
        "completed_at": end_time.isoformat() + "Z",
        "duration_seconds": round(duration, 2),
        "total_files_processed": len(results_a) + len(results_b),
        "total_errors": len(errors),
        "pipeline_a": {
            "files_attempted": len(results_a) + len([e for e in errors if e["pipeline"] == "A"]),
            "succeeded": len(results_a),
            "failed": len([e for e in errors if e["pipeline"] == "A"]),
            "results": results_a
        },
        "pipeline_b": {
            "files_attempted": len(results_b) + len([e for e in errors if e["pipeline"] == "B"]),
            "succeeded": len(results_b),
            "failed": len([e for e in errors if e["pipeline"] == "B"]),
            "results": results_b
        },
        "errors": errors,
        "task_summary": get_task_summary()
    }

    # Save summary report
    summary_path = Path("outputs/batch_summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"\n✓ Batch summary saved → {summary_path}")

    # Print results table
    _print_summary_table(summary)

    return summary


def _print_summary_table(summary: dict) -> None:
    a = summary["pipeline_a"]
    b = summary["pipeline_b"]
    errs = summary["errors"]

    print("\n" + "═" * 55)
    print("  BATCH RUN COMPLETE")
    print("═" * 55)
    print(f"  Duration:          {summary['duration_seconds']}s")
    print(f"  Files processed:   {summary['total_files_processed']}")
    print(f"  Errors:            {summary['total_errors']}")
    print("─" * 55)
    print(f"  Pipeline A:  {a['succeeded']} succeeded / {a['failed']} failed")
    for r in a["results"]:
        print(f"    ✓ {r['account_id']} — {r.get('company_name', '')}")
    print(f"  Pipeline B:  {b['succeeded']} succeeded / {b['failed']} failed")
    for r in b["results"]:
        chg = r.get("total_changes", 0)
        print(f"    ✓ {r['account_id']} — {r.get('company_name', '')} ({chg} changes)")
    if errs:
        print("─" * 55)
        print("  ERRORS:")
        for e in errs:
            print(f"    ✗ {e['source_file']} (Pipeline {e['pipeline']}): {e['error']}")
    print("═" * 55)
    print(f"  Output directory: outputs/accounts/")
    print(f"  Task log:         outputs/tasks.json")
    print(f"  Full report:      outputs/batch_summary.json")
    print("═" * 55 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch runner: processes all demo + onboarding transcripts"
    )
    parser.add_argument(
        "--demo-dir", default="inputs/demo",
        help="Directory containing demo call transcripts"
    )
    parser.add_argument(
        "--onboarding-dir", default="inputs/onboarding",
        help="Directory containing onboarding call transcripts"
    )
    parser.add_argument(
        "--pipeline", choices=["a", "b", "all"], default="all",
        help="Which pipeline(s) to run"
    )
    args = parser.parse_args()

    try:
        run_batch(args.demo_dir, args.onboarding_dir, args.pipeline)
    except KeyboardInterrupt:
        logger.info("Batch run interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Batch run failed: {e}")
        sys.exit(1)
