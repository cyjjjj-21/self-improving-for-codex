#!/usr/bin/env python3
"""Conservative bridge-to-main memory sync for Codex self-improving loops."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from memory_utils import (
    MultiFileLock,
    append_audit_record,
    append_entries,
    maintenance_lock_path,
    parse_memory_document,
)


RAW_FILES = ("LEARNINGS.md", "ERRORS.md", "FEATURE_REQUESTS.md")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-memory-dir",
        default="/Users/chenyuanjie/.claude-to-im/codex-home/memories",
        help="Bridge or source memory directory",
    )
    parser.add_argument(
        "--dest-memory-dir",
        default="/Users/chenyuanjie/.codex/memories",
        help="Destination memory directory",
    )
    parser.add_argument(
        "--lock-dir",
        default=None,
        help="Optional shared directory for maintenance lock files",
    )
    parser.add_argument("--hours", type=int, default=24, help="Only consider entries newer than this window")
    parser.add_argument("--apply", action="store_true", help="Write synced entries into destination raw memories")
    return parser.parse_args()


def _recent_entries(document, cutoff: datetime):
    selected = []
    for entry in document.entries:
        logged_at = entry.logged_at()
        if logged_at is None or logged_at >= cutoff:
            selected.append(entry)
    return selected


def main() -> int:
    args = _parse_args()
    source_dir = Path(args.source_memory_dir)
    dest_dir = Path(args.dest_memory_dir)
    lock_dir = Path(args.lock_dir).expanduser() if args.lock_dir else None
    cutoff = datetime.now(tz=UTC) - timedelta(hours=args.hours)

    lock_paths = [
        maintenance_lock_path(source_dir.parent, lock_dir),
        maintenance_lock_path(dest_dir.parent, lock_dir),
    ]
    with MultiFileLock(lock_paths):
        summary: dict[str, dict] = {}
        copied_total = 0

        for file_name in RAW_FILES:
            source_doc = parse_memory_document(source_dir / file_name)
            dest_doc = parse_memory_document(dest_dir / file_name)
            candidates = _recent_entries(source_doc, cutoff)
            before_count = len(dest_doc.entries)
            copied = append_entries(dest_doc, candidates)
            after_count = before_count + copied
            summary[file_name] = {
                "source_recent_candidates": len(candidates),
                "destination_before": before_count,
                "copied": copied,
                "destination_after": after_count,
                "copied_entry_ids": [entry.entry_id for entry in candidates if entry.entry_id in {item.entry_id for item in dest_doc.entries[before_count:]}],
            }
            if args.apply and copied:
                dest_doc.entries.sort(key=lambda item: item.entry_id)
                from memory_utils import save_memory_document  # local import to avoid circular habits

                save_memory_document(dest_doc)
            copied_total += copied

        result = {
            "mode": "apply" if args.apply else "dry-run",
            "source_memory_dir": str(source_dir),
            "dest_memory_dir": str(dest_dir),
            "hours": args.hours,
            "copied_total": copied_total,
            "files": summary,
        }

        if args.apply:
            append_audit_record(
                source_dir,
                "memory_sync_source",
                {
                    "peer_memory_dir": str(dest_dir),
                    "copied_total": copied_total,
                    "files": summary,
                },
            )
            append_audit_record(
                dest_dir,
                "memory_sync_destination",
                {
                    "peer_memory_dir": str(source_dir),
                    "copied_total": copied_total,
                    "files": summary,
                },
            )

    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
