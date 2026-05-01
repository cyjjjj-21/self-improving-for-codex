#!/usr/bin/env python3
"""Weekly maintenance for large memory files: archive older raw entries and refresh indexes."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path
import re

from memory_utils import (
    FileLock,
    MemoryDocument,
    MemoryEntry,
    append_audit_record,
    atomic_write_text,
    maintenance_lock_path,
    parse_memory_document,
    save_memory_document,
)


HEADING_STYLE_RE = re.compile(
    r"^## (?:(?:\[(?P<bracket_id>[^\]]+)\] (?P<bracket_title>.+))|(?P<plain_id>(?:LEARN|LRN|ERR|FEAT)-[A-Za-z0-9._-]+)(?: (?P<plain_title>.+))?)$",
    re.MULTILINE,
)
PLAIN_HEADING_RE = re.compile(
    r"^## (?P<entry_id>(?:LEARN|LRN|ERR|FEAT)-[A-Za-z0-9._-]+)(?: (?P<title>.+))?$",
    re.MULTILINE,
)
ENTRY_DATE_RE = re.compile(r"^(?:LEARN|LRN|ERR|FEAT)-(?P<year>\d{4})(?:-?)(?P<month>\d{2})(?:-?)(?P<day>\d{2})")

FILE_POLICIES = {
    "LEARNINGS.md": {
        "max_lines": 800,
        "max_entries": 60,
        "trigger_ratio": 0.95,
        "target_ratio": 0.82,
        "cutoff_days": 10,
        "min_remaining_entries": 24,
    },
    "ERRORS.md": {
        "max_lines": 1600,
        "max_entries": 100,
        "trigger_ratio": 0.95,
        "target_ratio": 0.78,
        "cutoff_days": 10,
        "min_remaining_entries": 32,
    },
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-dir", default=str(Path.home() / ".codex" / "memories"))
    parser.add_argument("--lock-dir", default=None, help="Optional shared directory for maintenance lock files")
    parser.add_argument("--today", default=None, help="Override local date in YYYY-MM-DD format")
    parser.add_argument("--apply", action="store_true", help="Write changes instead of printing summary only")
    return parser.parse_args()


def _today(args_today: str | None) -> datetime:
    if args_today:
        return datetime.strptime(args_today, "%Y-%m-%d").replace(tzinfo=UTC)
    return datetime.now(tz=UTC)


def _entry_date(entry: MemoryEntry) -> datetime | None:
    logged = entry.logged_at()
    if logged is not None:
        return logged.astimezone(UTC)
    match = ENTRY_DATE_RE.match(entry.entry_id)
    if not match:
        return None
    try:
        return datetime(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
            tzinfo=UTC,
        )
    except ValueError:
        return None


def _entry_line_count(entry: MemoryEntry) -> int:
    return entry.raw.count("\n")


def detect_heading_styles(path: Path) -> dict[str, int | str]:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    bracketed = 0
    plain = 0
    for line in text.splitlines():
        if not line.startswith("## "):
            continue
        body = line[3:]
        if body in {"Promotion Tagging Standard", "Entry Format Standard", "Severity Standard", "Maintenance Rules"}:
            continue
        match = HEADING_STYLE_RE.match(line)
        if not match:
            continue
        if match.group("bracket_id"):
            bracketed += 1
        elif match.group("plain_id"):
            plain += 1
    if bracketed and plain:
        mode = "mixed"
    elif bracketed:
        mode = "bracketed"
    elif plain:
        mode = "plain"
    else:
        mode = "none"
    return {"bracketed": bracketed, "plain": plain, "mode": mode}


def normalize_entry_headings(document: MemoryDocument) -> int:
    changed = 0
    for entry in document.entries:
        first_line, _, remainder = entry.raw.partition("\n")
        match = PLAIN_HEADING_RE.match(first_line)
        if not match or first_line.startswith("## ["):
            continue
        title = match.group("title") or entry.title or match.group("entry_id")
        new_first_line = f"## [{match.group('entry_id')}] {title}".rstrip()
        entry.raw = f"{new_first_line}\n{remainder}" if remainder else f"{new_first_line}\n"
        changed += 1
    return changed


def select_entries_to_archive(
    *,
    document: MemoryDocument,
    current_line_count: int,
    max_lines: int,
    max_entries: int,
    target_lines: int,
    target_entries: int,
    cutoff: datetime,
    min_remaining_entries: int,
) -> list[MemoryEntry]:
    if current_line_count <= max_lines and len(document.entries) <= max_entries:
        return []

    candidates: list[tuple[int, datetime, MemoryEntry]] = []
    for index, entry in enumerate(document.entries):
        entry_date = _entry_date(entry)
        if entry_date is None or entry_date >= cutoff:
            continue
        candidates.append((index, entry_date, entry))

    candidates.sort(key=lambda item: (item[1], item[0]))
    remaining_lines = current_line_count
    remaining_entries = len(document.entries)
    selected: list[MemoryEntry] = []

    for _, _, entry in candidates:
        if remaining_lines <= target_lines and remaining_entries <= target_entries:
            break
        if remaining_entries - 1 < min_remaining_entries:
            break
        selected.append(entry)
        remaining_lines -= _entry_line_count(entry)
        remaining_entries -= 1

    return selected


def _quarter_suffix(dt: datetime) -> str:
    quarter = ((dt.month - 1) // 3) + 1
    return f"{dt.year}_Q{quarter}"


def _archive_path(memory_dir: Path, raw_name: str, entry: MemoryEntry) -> Path:
    prefix = raw_name.removesuffix(".md")
    entry_date = _entry_date(entry) or datetime.now(tz=UTC)
    return memory_dir / "archive" / f"{prefix}_{_quarter_suffix(entry_date)}.md"


def _archive_preamble(raw_name: str, source_doc: MemoryDocument, today: datetime) -> str:
    note = f"Archived during weekly memory maintenance on {today.strftime('%Y-%m-%d')}."
    base = source_doc.preamble.rstrip()
    return f"{base}\n\n{note}\n\n"


def _append_to_archive(memory_dir: Path, raw_name: str, entries: list[MemoryEntry], source_doc: MemoryDocument, today: datetime) -> list[str]:
    grouped: dict[Path, list[MemoryEntry]] = {}
    for entry in entries:
        grouped.setdefault(_archive_path(memory_dir, raw_name, entry), []).append(entry)

    archive_names: list[str] = []
    for path, chunk in sorted(grouped.items(), key=lambda item: str(item[0])):
        archive_names.append(path.name)
        if path.exists():
            archive_doc = parse_memory_document(path)
        else:
            archive_doc = MemoryDocument(path=path, preamble=_archive_preamble(raw_name, source_doc, today), entries=[])
        archive_doc.entries.extend(chunk)
        save_memory_document(archive_doc)
    return archive_names


def _current_scope(entries: list[MemoryEntry]) -> str:
    dated = [_entry_date(entry) for entry in entries]
    dated = [item for item in dated if item is not None]
    if not dated:
        return "unknown"
    return f"{min(dated).date().isoformat()} through {max(dated).date().isoformat()}"


def _sample_ids(entries: list[MemoryEntry], count: int, *, tail: bool) -> list[str]:
    chosen = entries[-count:] if tail else entries[:count]
    return [entry.entry_id for entry in chosen]


def _render_index(memory_dir: Path, raw_name: str) -> str:
    path = memory_dir / raw_name
    document = parse_memory_document(path)
    line_count = path.read_text(encoding="utf-8").count("\n") + 1 if path.exists() else 0
    styles = detect_heading_styles(path)
    archive_paths = sorted((memory_dir / "archive").glob(f"{raw_name.removesuffix('.md')}_*.md"))
    heading = raw_name.removesuffix(".md")

    lines = [
        f"# {heading} INDEX",
        "",
        "## How To Use",
        "",
        f"- Default startup does not read raw {heading.lower()}.",
        "- Read [`ACTIVE.md`](/Users/chenyuanjie/.codex/memories/ACTIVE.md) first.",
        "- Use this Tier 1 index to decide whether to open the Tier 2 working set or a Tier 3 archive file.",
        "",
        "## Current Layout",
        "",
        f"- Tier 2 current working set: [`{raw_name}`](/Users/chenyuanjie/.codex/memories/{raw_name})",
        f"  Scope: {_current_scope(document.entries)}, {len(document.entries)} entries, about {line_count} lines.",
        f"  Heading styles: {styles['mode']} (bracketed={styles['bracketed']}, plain={styles['plain']}).",
    ]
    if archive_paths:
        first_archive = archive_paths[0].name
        archive_list = ", ".join(f"`{path.name}`" for path in archive_paths)
        lines.extend(
            [
                f"- Tier 3 historical archive: [`{first_archive}`](/Users/chenyuanjie/.codex/memories/archive/{first_archive}) and peers",
                f"  Archive files: {archive_list}",
            ]
        )
    else:
        lines.append("- Tier 3 historical archive: none yet")

    lines.extend(
        [
            "",
            "## Current Working Set Snapshot",
            "",
            f"- Oldest active IDs: {', '.join(f'`{item}`' for item in _sample_ids(document.entries, 6, tail=False)) or 'none'}",
            f"- Newest active IDs: {', '.join(f'`{item}`' for item in _sample_ids(document.entries, 8, tail=True)) or 'none'}",
            "",
            "## Maintenance Note",
            "",
            f"- New raw {heading.lower()} should continue to land in [`{raw_name}`](/Users/chenyuanjie/.codex/memories/{raw_name}).",
            "- Weekly maintenance should refresh this index whenever Tier 2 scope changes materially.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_archive_readme(memory_dir: Path) -> str:
    archive_paths = sorted((memory_dir / "archive").glob("*.md"))
    lines = [
        "# Memory Archive",
        "",
        "This directory stores historical raw memory that should not be read at session startup.",
        "",
        "Read order:",
        "",
        "1. Tier 0: [`PROFILE.md`](/Users/chenyuanjie/.codex/memories/PROFILE.md) and [`ACTIVE.md`](/Users/chenyuanjie/.codex/memories/ACTIVE.md)",
        "2. Tier 1: [`LEARNINGS_INDEX.md`](/Users/chenyuanjie/.codex/memories/LEARNINGS_INDEX.md) or [`ERRORS_INDEX.md`](/Users/chenyuanjie/.codex/memories/ERRORS_INDEX.md) if deeper lookup is needed",
        "3. Tier 2: current raw files",
        "4. Tier 3: archive files only when current raw files are insufficient",
        "",
        "Current archive files:",
        "",
    ]
    if archive_paths:
        for path in archive_paths:
            lines.append(f"- [`{path.name}`](/Users/chenyuanjie/.codex/memories/archive/{path.name})")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _maybe_archive_file(memory_dir: Path, raw_name: str, today: datetime, apply: bool) -> dict:
    policy = FILE_POLICIES[raw_name]
    path = memory_dir / raw_name
    document = parse_memory_document(path)
    normalized_heading_count = normalize_entry_headings(document)
    current_line_count = path.read_text(encoding="utf-8").count("\n") + 1 if path.exists() else 0
    trigger_lines = int(policy["max_lines"] * policy["trigger_ratio"])
    trigger_entries = int(policy["max_entries"] * policy["trigger_ratio"])
    target_lines = int(policy["max_lines"] * policy["target_ratio"])
    target_entries = int(policy["max_entries"] * policy["target_ratio"])
    cutoff = today - timedelta(days=policy["cutoff_days"])

    selected = select_entries_to_archive(
        document=document,
        current_line_count=current_line_count,
        max_lines=trigger_lines,
        max_entries=trigger_entries,
        target_lines=target_lines,
        target_entries=target_entries,
        cutoff=cutoff,
        min_remaining_entries=policy["min_remaining_entries"],
    )
    if not selected:
        if apply and normalized_heading_count:
            save_memory_document(document)
        return {
            "raw_file": raw_name,
            "moved_count": 0,
            "archive_files": [],
            "normalized_heading_count": normalized_heading_count,
            "reason": "under_threshold_or_no_old_candidates",
        }

    moved_ids = {entry.entry_id for entry in selected}
    remaining = [entry for entry in document.entries if entry.entry_id not in moved_ids]
    archive_files: list[str] = []
    if apply:
        archive_files = _append_to_archive(memory_dir, raw_name, selected, document, today)
        document.entries = remaining
        save_memory_document(document)
    else:
        archive_files = sorted({_archive_path(memory_dir, raw_name, entry).name for entry in selected})

    return {
        "raw_file": raw_name,
        "moved_count": len(selected),
        "moved_entry_ids": [entry.entry_id for entry in selected],
        "archive_files": archive_files,
        "normalized_heading_count": normalized_heading_count,
        "trigger_lines": trigger_lines,
        "trigger_entries": trigger_entries,
        "target_lines": target_lines,
        "target_entries": target_entries,
        "cutoff_before": cutoff.date().isoformat(),
    }


def main() -> int:
    args = _parse_args()
    memory_dir = Path(args.memory_dir)
    lock_dir = Path(args.lock_dir).expanduser() if args.lock_dir else None
    today = _today(args.today)

    lock_path = maintenance_lock_path(memory_dir.parent, lock_dir)
    with FileLock(lock_path):
        results = [
            _maybe_archive_file(memory_dir, raw_name, today, args.apply)
            for raw_name in ("LEARNINGS.md", "ERRORS.md")
        ]

        rendered_files = {
            "LEARNINGS_INDEX.md": _render_index(memory_dir, "LEARNINGS.md"),
            "ERRORS_INDEX.md": _render_index(memory_dir, "ERRORS.md"),
            "archive/README.md": _render_archive_readme(memory_dir),
        }
        if args.apply:
            for relative_path, text in rendered_files.items():
                atomic_write_text(memory_dir / relative_path, text)
            append_audit_record(
                memory_dir,
                "weekly_memory_maintenance",
                {
                    "mode": "apply",
                    "maintenance_results": results,
                    "refreshed_files": sorted(rendered_files.keys()),
                },
            )

    summary = {
        "mode": "apply" if args.apply else "dry-run",
        "memory_dir": str(memory_dir),
        "today": today.date().isoformat(),
        "maintenance_results": results,
        "refreshed_files": sorted(rendered_files.keys()),
    }
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
