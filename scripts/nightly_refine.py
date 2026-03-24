#!/usr/bin/env python3
"""Refine raw memory files and conservatively promote high-confidence rules."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from memory_utils import (
    FileLock,
    add_active_rule,
    add_profile_bullet,
    append_audit_record,
    infer_profile_target,
    maintenance_lock_path,
    parse_active_document,
    parse_memory_document,
    parse_profile_document,
    save_active_document,
    save_memory_document,
    save_profile_document,
    update_entry_field,
    update_last_reviewed,
)


RAW_FILES = ("LEARNINGS.md", "ERRORS.md", "FEATURE_REQUESTS.md")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--memory-dir",
        default="/Users/chenyuanjie/.codex/memories",
        help="Memory directory to refine",
    )
    parser.add_argument(
        "--lock-dir",
        default=None,
        help="Optional shared directory for maintenance lock files",
    )
    parser.add_argument("--hours", type=int, default=24, help="Review entries in this recent window")
    parser.add_argument("--apply", action="store_true", help="Apply promotions and status updates")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    memory_dir = Path(args.memory_dir)
    lock_dir = Path(args.lock_dir).expanduser() if args.lock_dir else None
    cutoff = datetime.now(tz=UTC) - timedelta(hours=args.hours)

    lock_path = maintenance_lock_path(memory_dir.parent, lock_dir)
    with FileLock(lock_path):
        active_doc = parse_active_document(memory_dir / "ACTIVE.md")
        profile_doc = parse_profile_document(memory_dir / "PROFILE.md")

        summary = {
            "mode": "apply" if args.apply else "dry-run",
            "memory_dir": str(memory_dir),
            "hours": args.hours,
            "read_files": [str(memory_dir / name) for name in ("PROFILE.md", "ACTIVE.md", *RAW_FILES)],
            "promoted_to_active": [],
            "promoted_to_profile": [],
            "left_raw": [],
            "updated_raw_entries": [],
        }

        touched_active = False
        touched_profile = False
        touched_raw: dict[str, bool] = {}

        for raw_name in RAW_FILES:
            document = parse_memory_document(memory_dir / raw_name)
            touched_raw[raw_name] = False
            for index, entry in enumerate(document.entries):
                logged_at = entry.logged_at()
                if logged_at is not None and logged_at < cutoff:
                    continue

                promote_to = entry.fields.get("Promote To ACTIVE", "none").strip()
                confidence = entry.fields.get("Promotion Confidence", "low").strip()
                status = entry.fields.get("Status", "").strip()

                if status == "promoted":
                    summary["left_raw"].append(
                        {
                            "entry_id": entry.entry_id,
                            "raw_file": raw_name,
                            "reason": "already promoted",
                        }
                    )
                    continue

                if promote_to not in {"ABS", "PREF"} or confidence != "high":
                    summary["left_raw"].append(
                        {
                            "entry_id": entry.entry_id,
                            "raw_file": raw_name,
                            "reason": f"promote_to={promote_to}, confidence={confidence}",
                        }
                    )
                    continue

                target_section = "Absolute Rules" if promote_to == "ABS" else "Default Preferences"
                added = add_active_rule(
                    active_doc,
                    target_section,
                    entry.summary or entry.title,
                    f"Promoted from {entry.entry_id} during nightly refine",
                )
                if added:
                    touched_active = True
                    summary["promoted_to_active"].append(
                        {
                            "entry_id": entry.entry_id,
                            "raw_file": raw_name,
                            "section": target_section,
                        }
                    )
                else:
                    summary["left_raw"].append(
                        {
                            "entry_id": entry.entry_id,
                            "raw_file": raw_name,
                            "reason": "matching active rule already present",
                        }
                    )

                profile_target = infer_profile_target(entry)
                if profile_target:
                    section_name, bullet_text = profile_target
                    if add_profile_bullet(profile_doc, section_name, bullet_text):
                        touched_profile = True
                        summary["promoted_to_profile"].append(
                            {
                                "entry_id": entry.entry_id,
                                "section": section_name,
                                "bullet": bullet_text,
                            }
                        )

                if added and status != "promoted":
                    updated_raw = update_entry_field(entry.raw, "Status", "promoted")
                    document.entries[index].raw = updated_raw
                    document.entries[index].fields["Status"] = "promoted"
                    touched_raw[raw_name] = True
                    summary["updated_raw_entries"].append(
                        {
                            "entry_id": entry.entry_id,
                            "raw_file": raw_name,
                            "field": "Status",
                            "value": "promoted",
                        }
                    )

            if args.apply and touched_raw[raw_name]:
                save_memory_document(document)

        if args.apply:
            if touched_active:
                save_active_document(active_doc)
            if touched_profile:
                save_profile_document(profile_doc)
            if touched_active or touched_profile:
                update_last_reviewed(memory_dir / "ACTIVE.md", memory_dir / "PROFILE.md")
            append_audit_record(
                memory_dir,
                "nightly_refine",
                {
                    "hours": args.hours,
                    "promoted_to_active": summary["promoted_to_active"],
                    "promoted_to_profile": summary["promoted_to_profile"],
                    "updated_raw_entries": summary["updated_raw_entries"],
                },
            )

    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
