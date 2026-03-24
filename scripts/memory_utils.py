#!/usr/bin/env python3
"""Utilities for the Codex self-improving memory loop."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import fcntl
import json
import os
import re
from pathlib import Path
import tempfile
from typing import Iterable


ENTRY_HEADING_RE = re.compile(r"^## \[(?P<entry_id>[^\]]+)\] (?P<title>.+)$", re.MULTILINE)
FIELD_RE = re.compile(r"^\*\*(?P<field>[^*]+)\*\*: (?P<value>.+)$", re.MULTILINE)
SECTION_RE = re.compile(r"^## (?P<title>[^\n]+)$", re.MULTILINE)
MAINTENANCE_LOCK_FILENAME = ".maintenance.lock"


@dataclass
class MemoryEntry:
    entry_id: str
    title: str
    raw: str
    fields: dict[str, str]
    summary: str

    def logged_at(self) -> datetime | None:
        raw_value = self.fields.get("Logged")
        if not raw_value:
            return None
        try:
            return datetime.strptime(raw_value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        except ValueError:
            return None

    def normalized_summary(self) -> str:
        return normalize_text(self.summary)


@dataclass
class MemoryDocument:
    path: Path
    preamble: str
    entries: list[MemoryEntry]


class FileLock:
    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        self._fh = None

    def __enter__(self) -> "FileLock":
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.lock_path.open("w", encoding="utf-8")
        fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        self._fh.write(str(os.getpid()))
        self._fh.flush()
        self._fh.seek(0)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fh is not None:
            self._fh.truncate(0)
            self._fh.flush()
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            self._fh.close()
            self._fh = None


class MultiFileLock:
    def __init__(self, lock_paths: Iterable[Path]) -> None:
        unique = sorted({path.resolve() for path in lock_paths}, key=lambda item: str(item))
        self._locks = [FileLock(path) for path in unique]

    def __enter__(self) -> "MultiFileLock":
        for lock in self._locks:
            lock.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        for lock in reversed(self._locks):
            lock.__exit__(exc_type, exc, tb)


def _slugify_lock_target(path: Path) -> str:
    text = str(path.resolve())
    slug = re.sub(r"[^A-Za-z0-9._-]+", "__", text).strip("._-")
    return slug or "root"


def maintenance_lock_path(codex_home: Path, lock_dir: Path | None = None) -> Path:
    if lock_dir is None:
        return codex_home / MAINTENANCE_LOCK_FILENAME
    return lock_dir / f"{_slugify_lock_target(codex_home)}{MAINTENANCE_LOCK_FILENAME}"


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding=encoding,
        dir=path.parent,
        prefix=f".{path.name}.tmp.",
        delete=False,
    ) as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        tmp_path = Path(handle.name)
    os.replace(tmp_path, path)


def atomic_append_line(path: Path, line: str, *, encoding: str = "utf-8") -> None:
    existing = path.read_text(encoding=encoding) if path.exists() else ""
    atomic_write_text(path, existing + line, encoding=encoding)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def extract_section_text(raw: str, heading: str) -> str:
    pattern = re.compile(
        rf"^### {re.escape(heading)}\n(?P<body>.*?)(?=^### |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(raw)
    if not match:
        return ""
    return match.group("body").strip()


def parse_memory_document(path: Path) -> MemoryDocument:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    matches = list(ENTRY_HEADING_RE.finditer(text))
    if not matches:
        return MemoryDocument(path=path, preamble=text.rstrip() + ("\n" if text else ""), entries=[])

    preamble = text[: matches[0].start()].rstrip() + "\n\n"
    entries: list[MemoryEntry] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        raw = text[start:end].rstrip() + "\n"
        fields = {item.group("field"): item.group("value").strip() for item in FIELD_RE.finditer(raw)}
        summary = extract_section_text(raw, "Summary")
        entries.append(
            MemoryEntry(
                entry_id=match.group("entry_id"),
                title=match.group("title").strip(),
                raw=raw,
                fields=fields,
                summary=summary,
            )
        )
    return MemoryDocument(path=path, preamble=preamble, entries=entries)


def save_memory_document(document: MemoryDocument) -> None:
    chunks = [document.preamble.rstrip()]
    if document.entries:
        chunks.append("")
        chunks.extend(entry.raw.rstrip() for entry in document.entries)
    text = "\n".join(chunks).rstrip() + "\n"
    atomic_write_text(document.path, text)


def append_entries(document: MemoryDocument, new_entries: Iterable[MemoryEntry]) -> int:
    existing_ids = {entry.entry_id for entry in document.entries}
    existing_fingerprints = {entry_fingerprint(entry) for entry in document.entries}
    count = 0
    for entry in new_entries:
        fingerprint = entry_fingerprint(entry)
        if entry.entry_id in existing_ids or fingerprint in existing_fingerprints:
            continue
        document.entries.append(entry)
        existing_ids.add(entry.entry_id)
        existing_fingerprints.add(fingerprint)
        count += 1
    return count


def entry_fingerprint(entry: MemoryEntry) -> str:
    basis = entry.summary or f"{entry.entry_id} {entry.title}"
    return normalize_text(basis)


def now_utc_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_local_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


@dataclass
class ActiveRule:
    rule_id: str
    statement: str
    source: str


@dataclass
class ActiveDocument:
    path: Path
    sections: dict[str, list[str]]

    def rules_for(self, section_name: str) -> list[ActiveRule]:
        lines = self.sections.get(section_name, [])
        rules: list[ActiveRule] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            if line.startswith("- ["):
                match = re.match(r"- \[(?P<rule_id>[^\]]+)\] (?P<statement>.+)", line)
                source = ""
                if match:
                    if index + 1 < len(lines) and lines[index + 1].startswith("  Source: "):
                        source = lines[index + 1].removeprefix("  Source: ").strip()
                        index += 1
                    rules.append(
                        ActiveRule(
                            rule_id=match.group("rule_id"),
                            statement=match.group("statement").strip(),
                            source=source,
                        )
                    )
            index += 1
        return rules


def parse_active_document(path: Path) -> ActiveDocument:
    text = path.read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(text))
    sections: dict[str, list[str]] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip("\n")
        sections[match.group("title")] = body.splitlines() if body else []
    return ActiveDocument(path=path, sections=sections)


def save_active_document(document: ActiveDocument) -> None:
    ordered_titles = [
        "Absolute Rules",
        "Default Preferences",
        "Maintenance Rules",
        "Last Reviewed",
    ]
    lines = ["# ACTIVE", ""]
    for title in ordered_titles:
        body = document.sections.get(title, [])
        lines.append(f"## {title}")
        lines.extend(body)
        lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    atomic_write_text(document.path, text)


def add_active_rule(document: ActiveDocument, section_name: str, statement: str, source: str) -> bool:
    existing = {normalize_text(rule.statement) for rule in document.rules_for(section_name)}
    if normalize_text(statement) in existing:
        return False

    prefix = "ABS" if section_name == "Absolute Rules" else "PREF"
    current_rules = document.rules_for(section_name)
    next_num = 1
    for rule in current_rules:
        match = re.match(rf"{prefix}-(\d+)", rule.rule_id)
        if match:
            next_num = max(next_num, int(match.group(1)) + 1)
    rule_id = f"{prefix}-{next_num:03d}"
    block = [f"- [{rule_id}] {statement}", f"  Source: {source}"]
    body = document.sections.setdefault(section_name, [])
    if body and body[-1].strip():
        body.append("")
    body.extend(block)
    return True


@dataclass
class ProfileDocument:
    path: Path
    sections: dict[str, list[str]]


def parse_profile_document(path: Path) -> ProfileDocument:
    text = path.read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(text))
    sections: dict[str, list[str]] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip("\n")
        sections[match.group("title")] = body.splitlines() if body else []
    return ProfileDocument(path=path, sections=sections)


def save_profile_document(document: ProfileDocument) -> None:
    ordered_titles = [
        "User Role",
        "Technical Level",
        "Communication Preferences",
        "Working Preferences",
        "Tooling and Customization Preferences",
        "Last Updated",
    ]
    lines = ["# PROFILE", ""]
    for title in ordered_titles:
        if title not in document.sections:
            continue
        lines.append(f"## {title}")
        lines.extend(document.sections[title])
        lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    atomic_write_text(document.path, text)


def add_profile_bullet(document: ProfileDocument, section_name: str, bullet_text: str) -> bool:
    body = document.sections.setdefault(section_name, [])
    normalized_existing = {normalize_text(line.removeprefix("- ").strip()) for line in body if line.startswith("- ")}
    normalized_candidate = normalize_text(bullet_text)
    if normalized_candidate in normalized_existing:
        return False
    if body and body[-1].strip() and not body[-1].startswith("- "):
        body.append("")
    body.append(f"- {bullet_text}")
    return True


def update_last_reviewed(active_path: Path, profile_path: Path | None = None) -> None:
    active_doc = parse_active_document(active_path)
    active_doc.sections["Last Reviewed"] = [f"- {today_local_date()}"]
    save_active_document(active_doc)
    if profile_path:
        profile_doc = parse_profile_document(profile_path)
        profile_doc.sections["Last Updated"] = [f"- {today_local_date()}"]
        save_profile_document(profile_doc)


def update_entry_field(raw: str, field_name: str, value: str) -> str:
    pattern = re.compile(rf"^\*\*{re.escape(field_name)}\*\*: .+$", re.MULTILINE)
    replacement = f"**{field_name}**: {value}"
    if pattern.search(raw):
        return pattern.sub(replacement, raw, count=1)
    lines = raw.splitlines()
    insert_at = 1
    while insert_at < len(lines) and lines[insert_at].startswith("**"):
        insert_at += 1
    lines.insert(insert_at, replacement)
    return "\n".join(lines).rstrip() + "\n"


def append_audit_record(memory_dir: Path, event_type: str, payload: dict) -> Path:
    memory_dir.mkdir(parents=True, exist_ok=True)
    path = memory_dir / "AUDIT_LOG.jsonl"
    record = {
        "timestamp": now_utc_iso(),
        "event_type": event_type,
        **payload,
    }
    atomic_append_line(path, json.dumps(record, ensure_ascii=True) + "\n")
    return path


def infer_profile_target(entry: MemoryEntry) -> tuple[str, str] | None:
    summary = entry.summary.strip()
    if not summary:
        return None
    lowered = summary.lower()
    if "prefers chinese" in lowered:
        return ("Communication Preferences", "Prefers Chinese by default")
    if "prefers concise" in lowered or "communication" in lowered:
        return ("Communication Preferences", summary.removeprefix("The user ").strip().capitalize())
    if "customization" in lowered or "codex" in lowered:
        return ("Tooling and Customization Preferences", summary.removeprefix("The user ").strip().capitalize())
    if "prefers" in lowered or "expects" in lowered or "likes" in lowered:
        return ("Working Preferences", summary.removeprefix("The user ").strip().capitalize())
    return None
