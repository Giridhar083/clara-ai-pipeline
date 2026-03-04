"""
task_tracker.py
---------------
Creates and manages task items for each processed account.
Default: stores tasks in a local tasks.json file.
Optional: creates Trello cards (free Trello API).

To enable Trello:
  Set TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_LIST_ID in .env
  Get free keys at: https://trello.com/app-key
"""

import os
import json
import logging
import requests
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

TASKS_FILE = Path(os.getenv("TASKS_FILE", "outputs/tasks.json"))

# Optional Trello config (free tier)
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY", "")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN", "")
TRELLO_LIST_ID = os.getenv("TRELLO_LIST_ID", "")
TRELLO_API_URL = "https://api.trello.com/1"


def create_task(account_id: str, company_name: str, pipeline: str,
                version: str, output_paths: dict, notes: str = "") -> dict:
    """
    Create a task item for a processed account.
    Saves to local JSON and optionally to Trello.

    Args:
        account_id: e.g. "account_001"
        company_name: e.g. "Arctic Air HVAC"
        pipeline: "A" or "B"
        version: "v1" or "v2"
        output_paths: dict of file paths that were created
        notes: any additional notes

    Returns:
        task dict
    """
    timestamp = datetime.utcnow().isoformat() + "Z"

    task = {
        "task_id": f"{account_id}_{pipeline}_{version}_{timestamp[:10]}",
        "account_id": account_id,
        "company_name": company_name,
        "pipeline": pipeline,
        "version": version,
        "status": "completed",
        "created_at": timestamp,
        "output_files": output_paths,
        "notes": notes,
        "trello_card_id": None
    }

    # Save to local tasks file
    _save_task_locally(task)

    # Optionally create Trello card
    if TRELLO_API_KEY and TRELLO_TOKEN and TRELLO_LIST_ID:
        trello_id = _create_trello_card(task)
        if trello_id:
            task["trello_card_id"] = trello_id
            _update_task_locally(task)

    logger.info(f"Task created: {task['task_id']}")
    return task


def get_all_tasks() -> list:
    """Return all tasks from local tasks file."""
    if not TASKS_FILE.exists():
        return []
    with open(TASKS_FILE) as f:
        return json.load(f)


def get_task_summary() -> dict:
    """Return a summary of all tasks."""
    tasks = get_all_tasks()
    return {
        "total_tasks": len(tasks),
        "pipeline_a": len([t for t in tasks if t["pipeline"] == "A"]),
        "pipeline_b": len([t for t in tasks if t["pipeline"] == "B"]),
        "accounts_processed": list({t["account_id"] for t in tasks}),
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _save_task_locally(task: dict) -> None:
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)

    tasks = []
    if TASKS_FILE.exists():
        with open(TASKS_FILE) as f:
            try:
                tasks = json.load(f)
            except json.JSONDecodeError:
                tasks = []

    # Idempotent: replace if same task_id exists
    tasks = [t for t in tasks if t.get("task_id") != task["task_id"]]
    tasks.append(task)

    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


def _update_task_locally(task: dict) -> None:
    """Update an existing task entry."""
    _save_task_locally(task)  # _save_task_locally already replaces by task_id


def _create_trello_card(task: dict) -> str | None:
    """Create a Trello card for the task. Returns card ID or None."""
    try:
        pipeline_label = "Demo → v1" if task["pipeline"] == "A" else "Onboarding → v2"
        name = f"[{task['account_id']}] {task['company_name']} — {pipeline_label}"

        desc_lines = [
            f"**Account ID:** {task['account_id']}",
            f"**Company:** {task['company_name']}",
            f"**Pipeline:** {task['pipeline']} ({pipeline_label})",
            f"**Version:** {task['version']}",
            f"**Processed at:** {task['created_at']}",
            "",
            "**Output Files:**"
        ]
        for label, path in task.get("output_files", {}).items():
            desc_lines.append(f"- {label}: `{path}`")

        if task.get("notes"):
            desc_lines += ["", f"**Notes:** {task['notes']}"]

        description = "\n".join(desc_lines)

        response = requests.post(
            f"{TRELLO_API_URL}/cards",
            params={
                "key": TRELLO_API_KEY,
                "token": TRELLO_TOKEN,
                "idList": TRELLO_LIST_ID,
                "name": name,
                "desc": description
            },
            timeout=30
        )
        response.raise_for_status()
        card_id = response.json()["id"]
        logger.info(f"Trello card created: {card_id}")
        return card_id

    except Exception as e:
        logger.warning(f"Trello card creation failed (non-fatal): {e}")
        return None
