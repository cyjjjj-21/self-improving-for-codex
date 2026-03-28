#!/usr/bin/env python3
"""Generate a concise night-memory summary from an isolated Codex home."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    home = Path.home()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-home", default=str(home / ".codex-summary-home"))
    parser.add_argument("--status-path", default=str(home / ".codex" / "runtime" / "night-memory-pipeline" / "last_run.json"))
    parser.add_argument("--memory-output", default=str(home / ".codex" / "automations" / "night-memory-pipeline" / "memory.md"))
    parser.add_argument("--runtime-dir", default=str(home / ".codex" / "runtime" / "night-memory-summary"))
    parser.add_argument("--pipeline-out-log", default=str(home / "Library" / "Logs" / "CodexNightMemory" / "night-memory-pipeline.out.log"))
    parser.add_argument("--pipeline-err-log", default=str(home / "Library" / "Logs" / "CodexNightMemory" / "night-memory-pipeline.err.log"))
    parser.add_argument("--audit-log", default=str(home / ".codex" / "memories" / "AUDIT_LOG.jsonl"))
    parser.add_argument("--run-id", default=None, help="Require this run_id before generating summary")
    return parser.parse_args()


SUMMARY_PROMPT_TEMPLATE = """只做只读检查，不要执行任何会写入 ~/.codex 或 ~/.claude-to-im 的脚本。
读取这些文件：
- {status_path}
- {pipeline_out_log}
- {pipeline_err_log}
- {audit_log}

输出一段简洁中文总结，要求：
1. 直接给结果，不要描述你的检查过程，不要提技能、规则、记忆加载。
2. 明确写出第 1 步 bridge raw memory 同步是否成功，第 2 步主记忆精炼是否成功，第 3 步周日 skill index 是否执行或跳过。
3. 明确写出改了哪些文件、是否写入审计日志、如果失败失败原因是什么、是否需要人工干预。
4. 用 4-8 行短句或短项目符号即可。
"""


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _stable_env(summary_home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["CODEX_HOME"] = str(summary_home)
    if "PATH" not in env:
        env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    return env


def _filtered_stderr(text: str) -> str:
    filtered = []
    for line in text.splitlines():
        if "plugins::manager: ignoring remote plugin missing from local marketplace" in line:
            continue
        if "shell_snapshot: Failed to delete shell snapshot" in line:
            continue
        if "ephemeral threads do not support includeTurns" in line:
            continue
        if " WARN " not in line and " ERROR " not in line:
            continue
        filtered.append(line)
    return "\n".join(filtered).strip()


def _extract_changed_files(status_payload: dict) -> list[str]:
    changed: list[str] = []
    for step in status_payload.get("steps", []):
        stdout = step.get("stdout", "")
        if not stdout:
            continue
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            continue
        if step.get("name") == "bridge_sync":
            files = parsed.get("files", {})
            for name, details in files.items():
                if details.get("copied", 0):
                    changed.append(name)
        if step.get("name") == "nightly_refine":
            changed.append("AUDIT_LOG.jsonl")
    return sorted(dict.fromkeys(changed))


def _fallback_summary(status_payload: dict, issue: str) -> str:
    steps = {step.get("name"): step for step in status_payload.get("steps", [])}
    changed = _extract_changed_files(status_payload)
    bridge = steps.get("bridge_sync", {})
    refine = steps.get("nightly_refine", {})
    weekly = steps.get("weekly_skill_index_refresh", {})
    lines = [
        f"- 最近一次摘要时间：{datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"- 运行标识：{status_payload.get('run_id', 'unknown')}",
        f"- 第 1 步 bridge raw memory 同步：{bridge.get('status', 'unknown')}",
        f"- 第 2 步主记忆精炼：{refine.get('status', 'unknown')}",
        f"- 第 3 步周日 skill index：{weekly.get('status', 'unknown')}{'，原因：' + weekly.get('reason', '') if weekly.get('reason') else ''}",
        f"- 改动文件：{', '.join(changed) if changed else '无新增业务文件，仅审计/状态可能刷新'}",
        f"- 摘要状态：degraded，原因：{issue}",
    ]
    return "\n".join(lines)


def _render_memory(summary_text: str, mode: str, status_payload: dict | None, codex_returncode: int, degraded: bool) -> str:
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    pipeline_status = status_payload.get("overall_status") if status_payload else "unknown"
    return (
        "# Night Memory Pipeline Memory\n\n"
        f"- Last Summary Run: {generated_at}\n"
        f"- Summary Mode: `{mode}`\n"
        f"- Pipeline Overall Status: `{pipeline_status}`\n"
        f"- Summary Exit Code: `{codex_returncode}`\n"
        f"- Summary Degraded: `{str(degraded).lower()}`\n\n"
        "## Summary\n\n"
        f"{summary_text.strip()}\n"
    )


def _load_status(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _status_issue(status_payload: dict, expected_run_id: str | None) -> str | None:
    if not status_payload:
        return "missing pipeline status"
    if expected_run_id and status_payload.get("run_id") != expected_run_id:
        return f"run_id mismatch: expected {expected_run_id}, got {status_payload.get('run_id', 'missing')}"
    if status_payload.get("overall_status") == "running":
        return "pipeline still running"
    if not status_payload.get("completed_at"):
        return "pipeline completion timestamp missing"
    return None


def main() -> int:
    args = _parse_args()
    summary_home = Path(args.summary_home).expanduser()
    status_path = Path(args.status_path).expanduser()
    memory_output = Path(args.memory_output).expanduser()
    runtime_dir = Path(args.runtime_dir).expanduser()
    pipeline_out_log = Path(args.pipeline_out_log).expanduser()
    pipeline_err_log = Path(args.pipeline_err_log).expanduser()
    audit_log = Path(args.audit_log).expanduser()
    summary_text_path = runtime_dir / "last_summary.txt"
    summary_meta_path = runtime_dir / "last_summary.json"
    raw_stdout_path = runtime_dir / "last_codex_stdout.raw.log"
    raw_stderr_path = runtime_dir / "last_codex_stderr.raw.log"
    filtered_stderr_path = runtime_dir / "last_stderr.log"

    memory_output.parent.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    status_payload = _load_status(status_path)
    issue = _status_issue(status_payload, args.run_id)
    summary_text = ""
    mode = "codex"
    degraded = False
    codex_returncode = 0

    if issue is None:
        codex = shutil.which("codex")
        if not codex:
            issue = "codex binary not found in PATH"
        else:
            prompt = SUMMARY_PROMPT_TEMPLATE.format(
                status_path=status_path,
                pipeline_out_log=pipeline_out_log,
                pipeline_err_log=pipeline_err_log,
                audit_log=audit_log,
            )
            with tempfile.NamedTemporaryFile("w+", encoding="utf-8", prefix="night-memory-summary.", suffix=".txt", delete=False) as output_file:
                output_path = Path(output_file.name)
            completed = subprocess.run(
                [codex, "exec", "--skip-git-repo-check", "--ephemeral", "--output-last-message", str(output_path), prompt],
                capture_output=True,
                text=True,
                env=_stable_env(summary_home),
                cwd=str(Path.home()),
            )
            codex_returncode = completed.returncode
            summary_text = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
            output_path.unlink(missing_ok=True)
            _atomic_write(raw_stdout_path, completed.stdout)
            _atomic_write(raw_stderr_path, completed.stderr)
            filtered_stderr = _filtered_stderr(completed.stderr)
            _atomic_write(filtered_stderr_path, filtered_stderr + ("\n" if filtered_stderr else ""))
            if completed.returncode != 0 or not summary_text:
                issue = f"codex summary generation failed (returncode={completed.returncode}, output_present={'yes' if summary_text else 'no'})"

    if issue is not None:
        degraded = True
        mode = "fallback"
        summary_text = _fallback_summary(status_payload, issue)
        if not raw_stdout_path.exists():
            _atomic_write(raw_stdout_path, "")
        if not raw_stderr_path.exists():
            _atomic_write(raw_stderr_path, "")
        if not filtered_stderr_path.exists():
            _atomic_write(filtered_stderr_path, "")
        codex_returncode = 1

    _atomic_write(summary_text_path, summary_text + "\n")
    _atomic_write(
        summary_meta_path,
        json.dumps(
            {
                "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "mode": mode,
                "degraded": degraded,
                "codex_returncode": codex_returncode,
                "status_path": str(status_path),
                "run_id": status_payload.get("run_id"),
                "summary_text_path": str(summary_text_path),
                "raw_stdout_log": str(raw_stdout_path),
                "raw_stderr_log": str(raw_stderr_path),
                "filtered_stderr_log": str(filtered_stderr_path),
                "issue": issue,
            },
            ensure_ascii=True,
            indent=2,
        )
        + "\n",
    )
    _atomic_write(memory_output, _render_memory(summary_text, mode, status_payload, codex_returncode, degraded))
    return 1 if degraded else 0


if __name__ == "__main__":
    raise SystemExit(main())
