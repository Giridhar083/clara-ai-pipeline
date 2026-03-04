"""
pipeline_a.py
-------------
Pipeline A: Demo Call Transcript → v1 Account Memo + v1 Agent Spec

Usage:
  python scripts/pipeline_a.py --file inputs/demo/account_001_demo.txt
  python scripts/pipeline_a.py --file inputs/demo/account_001_demo.txt --account-id account_001
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Ensure scripts/ is on path when run from project root
sys.path.insert(0, str(Path(__file__).parent))

from extractor import extract_from_transcript
from agent_spec_generator import generate_agent_spec
from task_tracker import create_task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("pipeline_a")


def run_pipeline_a(transcript_path: str, account_id: str = None) -> dict:
    """
    Run Pipeline A for a single demo call transcript.

    Args:
        transcript_path: Path to the .txt transcript file
        account_id: Optional override. If not given, inferred from filename.

    Returns:
        dict with paths to generated files and status
    """
    transcript_path = Path(transcript_path)
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    # Infer account_id from filename if not given
    if not account_id:
        account_id = transcript_path.stem.replace("_demo", "")
    account_id = account_id.strip()

    logger.info(f"━━━ Pipeline A: {account_id} ━━━")
    logger.info(f"  Source: {transcript_path}")

    # ── Step 1: Read transcript ──────────────────────────────────────────
    transcript = transcript_path.read_text(encoding="utf-8")
    logger.info("  [1/4] Transcript loaded")

    # ── Step 2: Extract Account Memo via LLM ────────────────────────────
    logger.info("  [2/4] Extracting structured data via LLM...")
    memo = extract_from_transcript(transcript, account_id)
    logger.info(f"  ✓ Extracted memo for: {memo.get('company_name', account_id)}")

    # ── Step 3: Generate Agent Spec ──────────────────────────────────────
    logger.info("  [3/4] Generating Retell agent spec...")
    agent_spec = generate_agent_spec(memo, version="v1")
    logger.info("  ✓ Agent spec generated")

    # ── Step 4: Save outputs ─────────────────────────────────────────────
    output_dir = Path(f"outputs/accounts/{account_id}/v1")
    output_dir.mkdir(parents=True, exist_ok=True)

    memo_path = output_dir / "memo.json"
    spec_path = output_dir / "agent_spec.json"

    with open(memo_path, "w") as f:
        json.dump(memo, f, indent=2)

    with open(spec_path, "w") as f:
        json.dump(agent_spec, f, indent=2)

    logger.info(f"  ✓ Saved memo    → {memo_path}")
    logger.info(f"  ✓ Saved spec    → {spec_path}")

    # ── Step 5: Create task tracker item ─────────────────────────────────
    logger.info("  [4/4] Creating task tracker item...")
    task = create_task(
        account_id=account_id,
        company_name=memo.get("company_name", account_id),
        pipeline="A",
        version="v1",
        output_paths={
            "memo": str(memo_path),
            "agent_spec": str(spec_path)
        },
        notes=f"Generated from demo call: {transcript_path.name}"
    )
    logger.info(f"  ✓ Task created: {task['task_id']}")
    logger.info(f"━━━ Pipeline A complete: {account_id} ━━━\n")

    return {
        "status": "success",
        "account_id": account_id,
        "company_name": memo.get("company_name"),
        "version": "v1",
        "memo_path": str(memo_path),
        "agent_spec_path": str(spec_path),
        "task_id": task["task_id"]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline A: Demo Call → v1 Agent Config"
    )
    parser.add_argument(
        "--file", required=True,
        help="Path to demo call transcript (.txt)"
    )
    parser.add_argument(
        "--account-id", default=None,
        help="Account ID override (optional, inferred from filename if not set)"
    )
    args = parser.parse_args()

    try:
        result = run_pipeline_a(args.file, args.account_id)
        print(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"Pipeline A failed: {e}")
        sys.exit(1)
