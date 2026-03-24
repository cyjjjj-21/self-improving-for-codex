#!/usr/bin/env python3
"""Run the night memory maintenance pipeline as a single orchestrated task."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_SCRIPT_DIR = Path("/Users/chenyuanjie/.codex/skills/self-improving-for-codex/scripts")
DEFAULT_MAIN_MEMORY_DIR = Path("/Users/chenyuanjie/.codex/memories")
DEFAULT_BRIDGE_MEMORY_DIR = Path("/Users/chenyuanjie/.claude-to-im/codex-home/memories")


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


def main() -> int:
    args = _parse_args()
    script_dir = Path(args.script_dir)
    lock_dir = Path(args.lock_dir).expanduser() if args.lock_dir else None
    apply_flag = ["--apply"] if args.apply else []

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
    steps.append(_run_step("bridge_sync", sync_cmd))

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
    steps.append(_run_step("nightly_refine", refine_cmd))

    if is_sunday:
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
        "mode": "apply" if args.apply else "dry-run",
        "today": today.isoformat(),
        "lock_dir": str(lock_dir) if lock_dir is not None else None,
        "steps": steps,
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
