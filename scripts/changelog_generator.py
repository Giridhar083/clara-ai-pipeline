"""
changelog_generator.py
-----------------------
Computes a structured diff between v1 and v2 Account Memos.
Produces both a machine-readable changes.json and a human-readable changes.md.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


def generate_changelog(v1_memo: dict, v2_memo: dict) -> tuple[dict, str]:
    """
    Compare v1 and v2 memos and produce:
      - changes_json: machine-readable dict of all changes
      - changes_md: human-readable markdown changelog

    Returns (changes_json, changes_md)
    """
    account_id = v1_memo.get("account_id", "unknown")
    company = v2_memo.get("company_name", account_id)
    timestamp = datetime.utcnow().isoformat() + "Z"

    changes = []
    _diff_dicts(v1_memo, v2_memo, path="", changes=changes)

    changes_json = {
        "account_id": account_id,
        "company_name": company,
        "version_from": "v1",
        "version_to": "v2",
        "generated_at": timestamp,
        "total_changes": len(changes),
        "changes": changes
    }

    changes_md = _build_markdown(changes_json, changes)

    return changes_json, changes_md


def _diff_dicts(v1: Any, v2: Any, path: str, changes: list) -> None:
    """Recursively diff two values and append change records."""

    # Both are dicts — recurse field by field
    if isinstance(v1, dict) and isinstance(v2, dict):
        all_keys = set(v1.keys()) | set(v2.keys())
        for key in sorted(all_keys):
            child_path = f"{path}.{key}" if path else key
            _diff_dicts(v1.get(key), v2.get(key), child_path, changes)
        return

    # Both are lists — compare as sets for simple values, recurse for complex
    if isinstance(v1, list) and isinstance(v2, list):
        # Try simple element comparison
        v1_simple = [x for x in v1 if not isinstance(x, (dict, list))]
        v2_simple = [x for x in v2 if not isinstance(x, (dict, list))]

        added = [x for x in v2_simple if x not in v1_simple]
        removed = [x for x in v1_simple if x not in v2_simple]

        if added:
            changes.append({
                "field": path,
                "change_type": "items_added",
                "added": added,
                "reason": "Added during onboarding update"
            })
        if removed:
            changes.append({
                "field": path,
                "change_type": "items_removed",
                "removed": removed,
                "reason": "Removed during onboarding update"
            })

        # Recurse into dicts within lists (by index)
        v1_dicts = [x for x in v1 if isinstance(x, dict)]
        v2_dicts = [x for x in v2 if isinstance(x, dict)]
        for i, (d1, d2) in enumerate(zip(v1_dicts, v2_dicts)):
            _diff_dicts(d1, d2, f"{path}[{i}]", changes)

        return

    # Leaf values — compare directly
    if v1 != v2:
        change_type = _classify_change(v1, v2)
        changes.append({
            "field": path,
            "change_type": change_type,
            "old_value": v1,
            "new_value": v2,
            "reason": "Updated during onboarding call"
        })


def _classify_change(old: Any, new: Any) -> str:
    if old is None and new is not None:
        return "field_added"
    if old is not None and new is None:
        return "field_cleared"
    return "value_updated"


def _build_markdown(meta: dict, changes: list) -> str:
    account_id = meta["account_id"]
    company = meta["company_name"]
    ts = meta["generated_at"]
    total = meta["total_changes"]

    lines = [
        f"# Changelog — {company}",
        f"**Account ID:** `{account_id}`  ",
        f"**Version:** v1 → v2  ",
        f"**Generated:** {ts}  ",
        f"**Total Changes:** {total}",
        "",
        "---",
        "",
        "## Changes",
        ""
    ]

    if not changes:
        lines.append("_No changes detected between v1 and v2._")
    else:
        for c in changes:
            field = c["field"]
            ctype = c["change_type"]
            reason = c.get("reason", "")

            if ctype == "value_updated":
                old = c.get("old_value", "")
                new = c.get("new_value", "")
                lines.append(f"### `{field}`")
                lines.append(f"- **Change type:** Updated")
                lines.append(f"- **Old value:** `{old}`")
                lines.append(f"- **New value:** `{new}`")
                lines.append(f"- **Reason:** {reason}")
                lines.append("")

            elif ctype == "field_added":
                new = c.get("new_value", "")
                lines.append(f"### `{field}`")
                lines.append(f"- **Change type:** New field added")
                lines.append(f"- **Value:** `{new}`")
                lines.append(f"- **Reason:** {reason}")
                lines.append("")

            elif ctype == "field_cleared":
                old = c.get("old_value", "")
                lines.append(f"### `{field}`")
                lines.append(f"- **Change type:** Field cleared / removed")
                lines.append(f"- **Previous value:** `{old}`")
                lines.append(f"- **Reason:** {reason}")
                lines.append("")

            elif ctype == "items_added":
                added = c.get("added", [])
                lines.append(f"### `{field}`")
                lines.append(f"- **Change type:** Items added to list")
                lines.append(f"- **Added:** {added}")
                lines.append(f"- **Reason:** {reason}")
                lines.append("")

            elif ctype == "items_removed":
                removed = c.get("removed", [])
                lines.append(f"### `{field}`")
                lines.append(f"- **Change type:** Items removed from list")
                lines.append(f"- **Removed:** {removed}")
                lines.append(f"- **Reason:** {reason}")
                lines.append("")

    lines += [
        "---",
        "",
        "## Summary",
        "",
        f"This changelog documents {total} change(s) applied during the onboarding call.",
        "The v2 agent configuration reflects all updates confirmed by the client.",
        ""
    ]

    return "\n".join(lines)
