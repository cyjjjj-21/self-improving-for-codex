#!/usr/bin/env python3
"""Run the night memory pipeline from a stable launchd environment."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    home = Path.home()
    base = home / ".codex"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pipeline-script", default=str(Path(__file__).resolve().parent / "run_night_memory_pipeline.py"))
    parser.add_argument("--summary-script", default=str(Path(__file__).resolve().parent / "launchd_night_memory_summary.py"))
    parser.add_argument("--status-dir", default=str(base / "runtime" / "night-memory-pipeline"))
    return parser.parse_args()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _stable_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    if "PATH" not in env:
        env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    return env


def _running_status(run_id: str, started_at: str, status_path: Path, inner_status_path: Path, stdout_log: Path, stderr_log: Path, summary_meta: Path, summary_text: Path) -> dict:
    return {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": None,
        "finished_at": None,
        "mode": "apply",
        "today": datetime.now().date().isoformat(),
        "status_path": str(status_path),
        "summary_status": "pending",
        "summary_ready": False,
        "summary_generated_at": None,
        "summary_meta_path": str(summary_meta),
        "summary_text_path": str(summary_text),
        "steps": [],
        "overall_status": "running",
        "wrapper": {
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "inner_status_path": str(inner_status_path),
        },
    }


def _fallback_status(run_id: str, started_at: str, finished_at: str, returncode: int, stdout: str, stderr: str, status_path: Path, inner_status_path: Path, stdout_log: Path, stderr_log: Path, summary_meta: Path, summary_text: Path) -> dict:
    return {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": finished_at,
        "finished_at": finished_at,
        "mode": "apply",
        "today": datetime.now().date().isoformat(),
        "status_path": str(status_path),
        "steps": [],
        "overall_status": "failed",
        "summary_status": "pending",
        "summary_ready": False,
        "summary_generated_at": None,
        "summary_meta_path": str(summary_meta),
        "summary_text_path": str(summary_text),
        "wrapper": {
            "returncode": returncode,
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "inner_status_path": str(inner_status_path),
            "stderr_excerpt": stderr[-4000:],
            "stdout_excerpt": stdout[-4000:],
        },
    }


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _finalize_status(base: dict, run_id: str, started_at: str, finished_at: str, returncode: int, status_path: Path, inner_status_path: Path, stdout_log: Path, stderr_log: Path, summary_meta: Path, summary_text: Path) -> dict:
    payload = dict(base)
    payload["run_id"] = run_id
    payload["started_at"] = started_at
    payload["completed_at"] = finished_at
    payload["finished_at"] = finished_at
    payload["status_path"] = str(status_path)
    payload["summary_status"] = "pending"
    payload["summary_ready"] = False
    payload["summary_generated_at"] = None
    payload["summary_meta_path"] = str(summary_meta)
    payload["summary_text_path"] = str(summary_text)
    wrapper = dict(payload.get("wrapper", {}))
    wrapper.update(
        {
            "returncode": returncode,
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "inner_status_path": str(inner_status_path),
        }
    )
    payload["wrapper"] = wrapper
    return payload


def main() -> int:
    args = _parse_args()
    status_dir = Path(args.status_dir).expanduser()
    status_path = status_dir / "last_run.json"
    inner_status_path = status_dir / "last_run.inner.json"
    stdout_log = status_dir / "last_stdout.log"
    stderr_log = status_dir / "last_stderr.log"
    summary_meta = status_dir.parent / "night-memory-summary" / "last_summary.json"
    summary_text = status_dir.parent / "night-memory-summary" / "last_summary.txt"

    status_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    run_id = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    _atomic_write(
        status_path,
        json.dumps(
            _running_status(run_id, started_at, status_path, inner_status_path, stdout_log, stderr_log, summary_meta, summary_text),
            ensure_ascii=True,
            indent=2,
        )
        + "\n",
    )
    inner_status_path.unlink(missing_ok=True)

    pipeline_completed = subprocess.run(
        [sys.executable, str(Path(args.pipeline_script).expanduser()), "--apply", "--status-path", str(inner_status_path)],
        capture_output=True,
        text=True,
        env=_stable_env(),
    )
    finished_at = datetime.now().astimezone().isoformat(timespec="seconds")

    _atomic_write(stdout_log, pipeline_completed.stdout)
    _atomic_write(stderr_log, pipeline_completed.stderr)

    inner_status = _load_json(inner_status_path)
    if inner_status:
        final_status = _finalize_status(
            inner_status,
            run_id,
            started_at,
            finished_at,
            pipeline_completed.returncode,
            status_path,
            inner_status_path,
            stdout_log,
            stderr_log,
            summary_meta,
            summary_text,
        )
    else:
        final_status = _fallback_status(
            run_id,
            started_at,
            finished_at,
            pipeline_completed.returncode,
            pipeline_completed.stdout,
            pipeline_completed.stderr,
            status_path,
            inner_status_path,
            stdout_log,
            stderr_log,
            summary_meta,
            summary_text,
        )
    _atomic_write(status_path, json.dumps(final_status, ensure_ascii=True, indent=2) + "\n")

    summary_completed = subprocess.run(
        [
            sys.executable,
            str(Path(args.summary_script).expanduser()),
            "--status-path",
            str(status_path),
            "--run-id",
            run_id,
        ],
        capture_output=True,
        text=True,
        env=_stable_env(),
    )
    summary_meta_payload = _load_json(summary_meta)
    final_status = _load_json(status_path)
    summary_matches_run = summary_meta_payload.get("run_id") == run_id
    final_status["summary_status"] = "ready" if summary_completed.returncode == 0 else "degraded"
    final_status["summary_ready"] = summary_text.exists() and summary_matches_run
    final_status["summary_generated_at"] = summary_meta_payload.get("generated_at")
    final_status["summary_mode"] = summary_meta_payload.get("mode")
    final_status["summary_issue"] = summary_meta_payload.get("issue")
    final_status["summary_returncode"] = summary_completed.returncode
    _atomic_write(status_path, json.dumps(final_status, ensure_ascii=True, indent=2) + "\n")

    if pipeline_completed.stdout:
        sys.stdout.write(pipeline_completed.stdout)
        if not pipeline_completed.stdout.endswith("\n"):
            sys.stdout.write("\n")
    if pipeline_completed.stderr:
        sys.stderr.write(pipeline_completed.stderr)
        if not pipeline_completed.stderr.endswith("\n"):
            sys.stderr.write("\n")
    if summary_completed.stderr:
        sys.stderr.write(summary_completed.stderr)
        if not summary_completed.stderr.endswith("\n"):
            sys.stderr.write("\n")
    return 1 if pipeline_completed.returncode != 0 or summary_completed.returncode != 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
