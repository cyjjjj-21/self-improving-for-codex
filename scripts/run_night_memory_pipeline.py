#!/usr/bin/env python3
"""Run the night memory maintenance pipeline as a single orchestrated task."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import subprocess
import sys
from pathlib import Path

from memory_utils import atomic_write_text


DEFAULT_SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MAIN_MEMORY_DIR = Path.home() / ".codex" / "memories"
DEFAULT_BRIDGE_MEMORY_DIR = Path.home() / ".claude-to-im" / "codex-home" / "memories"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply changes instead of dry-run")
    parser.add_argument("--hours", type=int, default=24, help="Recent-window cutoff passed to subordinate scripts")
    parser.add_argument(
        "--lock-dir",
        default=None,
        help="Optional shared directory for maintenance lock files",
    )
    parser.add_argument("--script-dir", default=str(DEFAULT_SCRIPT_DIR), help="Directory containing maintenance scripts")
    parser.add_argument("--main-memory-dir", default=str(DEFAULT_MAIN_MEMORY_DIR), help="Main memory directory")
    parser.add_argument("--bridge-memory-dir", default=str(DEFAULT_BRIDGE_MEMORY_DIR), help="Bridge/source memory directory")
    parser.add_argument(
        "--today",
        default=None,
        help="Override local date in YYYY-MM-DD form for testing weekly behavior",
    )
    parser.add_argument(
        "--status-path",
        default=None,
        help="Optional JSON file that receives the final pipeline status payload.",
    )
    return parser.parse_args()


def _run_step(name: str, cmd: list[str]) -> dict:
    completed = subprocess.run(cmd, capture_output=True, text=True)
    payload = {
        "name": name,
        "command": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "status": "success" if completed.returncode == 0 else "failed",
    }
    return payload


def _write_status(path: Path, payload: dict) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=True, indent=2) + "\n")


def _skip_step(name: str, reason: str) -> dict:
    return {
        "name": name,
        "status": "skipped",
        "reason": reason,
    }


def main() -> int:
    args = _parse_args()
    script_dir = Path(args.script_dir)
    lock_dir = Path(args.lock_dir).expanduser() if args.lock_dir else None
    status_path = Path(args.status_path).expanduser() if args.status_path else None
    apply_flag = ["--apply"] if args.apply else []
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")

    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else datetime.now().date()
    is_sunday = today.weekday() == 6

    steps: list[dict] = []

    sync_cmd = [
        sys.executable,
        str(script_dir / "memory_sync.py"),
        "--source-memory-dir",
        str(Path(args.bridge_memory_dir)),
        "--dest-memory-dir",
        str(Path(args.main_memory_dir)),
        "--hours",
        str(args.hours),
        *apply_flag,
    ]
    if lock_dir is not None:
        sync_cmd.extend(["--lock-dir", str(lock_dir)])
    bridge_step = _run_step("bridge_sync", sync_cmd)
    steps.append(bridge_step)

    if bridge_step.get("status") == "failed":
        steps.append(_skip_step("nightly_refine", "blocked_by=bridge_sync_failure"))
        if is_sunday:
            steps.append(_skip_step("weekly_skill_index_refresh", "blocked_by=bridge_sync_failure"))
        else:
            steps.append(
                {
                    "name": "weekly_skill_index_refresh",
                    "status": "skipped",
                    "reason": f"today={today.isoformat()} is not Sunday",
                }
            )
    else:
        refine_cmd = [
            sys.executable,
            str(script_dir / "nightly_refine.py"),
            "--memory-dir",
            str(Path(args.main_memory_dir)),
            "--hours",
            str(args.hours),
            *apply_flag,
        ]
        if lock_dir is not None:
            refine_cmd.extend(["--lock-dir", str(lock_dir)])
        refine_step = _run_step("nightly_refine", refine_cmd)
        steps.append(refine_step)

        if refine_step.get("status") == "failed":
            if is_sunday:
                steps.append(_skip_step("weekly_skill_index_refresh", "blocked_by=nightly_refine_failure"))
            else:
                steps.append(
                    {
                        "name": "weekly_skill_index_refresh",
                        "status": "skipped",
                        "reason": f"today={today.isoformat()} is not Sunday",
                    }
                )
        elif is_sunday:
            index_cmd = [
                sys.executable,
                str(script_dir / "generate_local_skill_index.py"),
                *apply_flag,
            ]
            if lock_dir is not None:
                index_cmd.extend(["--lock-dir", str(lock_dir)])
            steps.append(_run_step("weekly_skill_index_refresh", index_cmd))
        else:
            steps.append(
                {
                    "name": "weekly_skill_index_refresh",
                    "status": "skipped",
                    "reason": f"today={today.isoformat()} is not Sunday",
                }
            )

    summary = {
        "started_at": started_at,
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": "apply" if args.apply else "dry-run",
        "today": today.isoformat(),
        "lock_dir": str(lock_dir) if lock_dir is not None else None,
        "status_path": str(status_path) if status_path is not None else None,
        "steps": steps,
    }
    summary["overall_status"] = "failed" if any(step.get("status") == "failed" for step in steps) else "success"
    if status_path is not None:
        _write_status(status_path, summary)
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 1 if summary["overall_status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
