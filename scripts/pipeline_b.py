"""
pipeline_b.py
-------------
Pipeline B: Onboarding Call Transcript → v2 Memo + v2 Agent Spec + Changelog

Requires v1 outputs from Pipeline A to already exist.

Usage:
  python scripts/pipeline_b.py --file inputs/onboarding/account_001_onboarding.txt
  python scripts/pipeline_b.py --file inputs/onboarding/account_001_onboarding.txt --account-id account_001
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from extractor import apply_patch
from agent_spec_generator import generate_agent_spec
from changelog_generator import generate_changelog
from task_tracker import create_task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("pipeline_b")


def run_pipeline_b(transcript_path: str, account_id: str = None) -> dict:
    """
    Run Pipeline B for a single onboarding call transcript.

    Args:
        transcript_path: Path to the onboarding .txt transcript file
        account_id: Optional override. If not given, inferred from filename.

    Returns:
        dict with paths to generated files and status
    """
    transcript_path = Path(transcript_path)
    if not transcript_path.exists():
        raise FileNotFoundError(f"Onboarding transcript not found: {transcript_path}")

    # Infer account_id
    if not account_id:
        account_id = transcript_path.stem.replace("_onboarding", "")
    account_id = account_id.strip()

    logger.info(f"━━━ Pipeline B: {account_id} ━━━")
    logger.info(f"  Source: {transcript_path}")

    # ── Step 1: Load v1 memo ─────────────────────────────────────────────
    v1_memo_path = Path(f"outputs/accounts/{account_id}/v1/memo.json")
    if not v1_memo_path.exists():
        raise FileNotFoundError(
            f"v1 memo not found at {v1_memo_path}. "
            f"Run Pipeline A for {account_id} first."
        )

    with open(v1_memo_path) as f:
        v1_memo = json.load(f)
    logger.info(f"  [1/5] Loaded v1 memo for: {v1_memo.get('company_name', account_id)}")

    # ── Step 2: Read onboarding transcript ───────────────────────────────
    transcript = transcript_path.read_text(encoding="utf-8")
    logger.info("  [2/5] Onboarding transcript loaded")

    # ── Step 3: Apply patch to produce v2 memo ───────────────────────────
    logger.info("  [3/5] Applying onboarding updates via LLM...")
    v2_memo = apply_patch(v1_memo, transcript)
    logger.info("  ✓ v2 memo generated")

    # ── Step 4: Generate v2 Agent Spec ───────────────────────────────────
    logger.info("  [4/5] Generating v2 agent spec...")
    v2_agent_spec = generate_agent_spec(v2_memo, version="v2")
    logger.info("  ✓ v2 agent spec generated")

    # ── Step 5: Generate changelog ───────────────────────────────────────
    logger.info("  [5/5] Generating changelog...")
    changes_json, changes_md = generate_changelog(v1_memo, v2_memo)
    logger.info(f"  ✓ Changelog: {changes_json['total_changes']} change(s) detected")

    # ── Save all outputs ─────────────────────────────────────────────────
    v2_dir = Path(f"outputs/accounts/{account_id}/v2")
    v2_dir.mkdir(parents=True, exist_ok=True)

    changelog_dir = Path(f"changelog")
    changelog_dir.mkdir(parents=True, exist_ok=True)

    memo_path = v2_dir / "memo.json"
    spec_path = v2_dir / "agent_spec.json"
    changes_json_path = v2_dir / "changes.json"
    changes_md_path = changelog_dir / f"{account_id}_changes.md"

    with open(memo_path, "w") as f:
        json.dump(v2_memo, f, indent=2)

    with open(spec_path, "w") as f:
        json.dump(v2_agent_spec, f, indent=2)

    with open(changes_json_path, "w") as f:
        json.dump(changes_json, f, indent=2)

    with open(changes_md_path, "w", encoding="utf-8") as f:
        f.write(changes_md)

    logger.info(f"  ✓ Saved v2 memo      → {memo_path}")
    logger.info(f"  ✓ Saved v2 spec      → {spec_path}")
    logger.info(f"  ✓ Saved changes.json → {changes_json_path}")
    logger.info(f"  ✓ Saved changes.md   → {changes_md_path}")

    # ── Create task tracker item ─────────────────────────────────────────
    task = create_task(
        account_id=account_id,
        company_name=v2_memo.get("company_name", account_id),
        pipeline="B",
        version="v2",
        output_paths={
            "memo_v2": str(memo_path),
            "agent_spec_v2": str(spec_path),
            "changes_json": str(changes_json_path),
            "changes_md": str(changes_md_path)
        },
        notes=f"Updated from onboarding call: {transcript_path.name}. "
              f"{changes_json['total_changes']} field(s) changed."
    )
    logger.info(f"  ✓ Task created: {task['task_id']}")
    logger.info(f"━━━ Pipeline B complete: {account_id} ━━━\n")

    return {
        "status": "success",
        "account_id": account_id,
        "company_name": v2_memo.get("company_name"),
        "version": "v2",
        "total_changes": changes_json["total_changes"],
        "memo_path": str(memo_path),
        "agent_spec_path": str(spec_path),
        "changes_json_path": str(changes_json_path),
        "changes_md_path": str(changes_md_path),
        "task_id": task["task_id"]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline B: Onboarding Call → v2 Agent Config + Changelog"
    )
    parser.add_argument(
        "--file", required=True,
        help="Path to onboarding call transcript (.txt)"
    )
    parser.add_argument(
        "--account-id", default=None,
        help="Account ID override (optional, inferred from filename if not set)"
    )
    args = parser.parse_args()

    try:
        result = run_pipeline_b(args.file, args.account_id)
        print(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"Pipeline B failed: {e}")
        sys.exit(1)
