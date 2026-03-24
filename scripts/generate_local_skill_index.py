#!/usr/bin/env python3
"""Generate LOCAL_SKILL_INDEX.md from installed local skills."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

from memory_utils import FileLock, atomic_write_text, maintenance_lock_path


CATEGORY_MAP = {
    ".system": "System Skills",
    "claude-to-im": "Communication And Workflow",
    "self-improving-for-codex": "Communication And Workflow",
    "project-prompt-architecture": "Communication And Workflow",
    "repo-session-handoff": "Communication And Workflow",
    "playwright": "Browser And UI",
    "playwright-interactive": "Browser And UI",
    "figma": "Browser And UI",
    "screenshot": "Browser And UI",
    "doc": "Documents And Media",
    "pdf": "Documents And Media",
    "slides": "Documents And Media",
    "imagegen": "Documents And Media",
    "sora": "Documents And Media",
    "develop-web-game": "Coding And Project Iteration",
    "jupyter-notebook": "Coding And Project Iteration",
}

CATEGORY_ORDER = [
    "System Skills",
    "Communication And Workflow",
    "Browser And UI",
    "Documents And Media",
    "Coding And Project Iteration",
    "Backups And Non-Primary Entries",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", default="/Users/chenyuanjie/.codex/skills")
    parser.add_argument("--output", default="/Users/chenyuanjie/.codex/skills/LOCAL_SKILL_INDEX.md")
    parser.add_argument(
        "--lock-dir",
        default=None,
        help="Optional shared directory for maintenance lock files",
    )
    parser.add_argument("--apply", action="store_true", help="Write the file instead of printing")
    return parser.parse_args()


def _extract_frontmatter(skill_md: Path) -> tuple[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"---\n(?P<body>.*?)\n---\n", text, re.DOTALL)
    name = skill_md.parent.name
    description = ""
    if not match:
        return name, description
    body = match.group("body").splitlines()
    collecting_description = False
    desc_lines: list[str] = []
    for line in body:
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("description:"):
            after = line.split(":", 1)[1].strip()
            if after == "|":
                collecting_description = True
                continue
            description = after.strip('"')
        elif collecting_description:
            if line.startswith("  "):
                desc_lines.append(line.strip())
            else:
                collecting_description = False
    if desc_lines and not description:
        description = " ".join(desc_lines)
    return name, description


def _trigger_hints(name: str) -> str:
    hints = {
        "skill-creator": '"做一个 skill", "创建新 skill", "update this skill"',
        "skill-installer": '"安装 skill", "找一个 GitHub skill", "list skills"',
        "claude-to-im": '"飞书桥接", "claude-to-im", "消息推送", "桥接诊断"',
        "self-improving-for-codex": '"self-improving", "记忆体系", "夜间精炼", "memory loop"',
        "project-prompt-architecture": '"prompt 架构", "初始化 repo 规则", "AGENTS 分层"',
        "repo-session-handoff": '"继续这个仓库", "接上次的活", "做个 handoff"',
        "playwright": '"打开网页检查", "浏览器自动化", "抓取页面", "UI flow 调试"',
        "playwright-interactive": '"持续调浏览器", "interactive Playwright", "保持浏览器会话"',
        "figma": '"Figma 链接", "设计稿还原", "node id", "design-to-code"',
        "screenshot": '"截个图", "桌面截图", "窗口截图"',
        "doc": '"改 docx", "生成 Word 文档", "文档排版"',
        "pdf": '"处理 PDF", "抽取 PDF", "生成 PDF"',
        "slides": '"做 PPT", "改 slides", "presentation deck"',
        "imagegen": '"生成图片", "改图", "去背景", "透明底"',
        "sora": '"生成视频", "Sora", "延长视频", "下载视频"',
        "develop-web-game": '"web game", "小游戏调试", "用 Playwright 验证游戏"',
        "jupyter-notebook": '"建 notebook", "实验 notebook", "教程 notebook"',
    }
    return hints.get(name, '"直接调用该 skill 名称", "相关任务描述"')


def _render_entry(skill_dir: Path, display_name: str, description: str) -> list[str]:
    if ".partial-" in skill_dir.name:
        return [
            f"### `{skill_dir.name}`",
            f"- Path: `{skill_dir}`",
            "- Status: backup from an incomplete or intermediate install",
            "- Default behavior: ignore unless the user explicitly asks about installation history or cleanup",
            "",
        ]
    return [
        f"### `{display_name}`",
        f"- Path: `{skill_dir}`",
        f"- Use for: {description or 'See the skill description in SKILL.md'}",
        f"- Typical triggers: {_trigger_hints(display_name)}",
        "",
    ]


def generate_index(skills_dir: Path) -> str:
    groups: dict[str, list[list[str]]] = {name: [] for name in CATEGORY_ORDER}
    skill_paths = sorted(skills_dir.glob("*/SKILL.md"))
    system_skills = sorted((skills_dir / ".system").glob("*/SKILL.md"))

    for skill_md in [*system_skills, *skill_paths]:
        skill_dir = skill_md.parent
        if skill_dir.name.startswith("."):
            continue
        display_name, description = _extract_frontmatter(skill_md)
        if skill_dir.parent.name == ".system":
            category = "System Skills"
        else:
            category = CATEGORY_MAP.get(skill_dir.name, "Backups And Non-Primary Entries")
        groups.setdefault(category, []).append(_render_entry(skill_dir, display_name, description))

    lines = [
        "# Local Skill Index",
        "",
        f"This is the local skill registry for `{skills_dir}`.",
        "",
        "Use it when you need to answer:",
        "",
        "- which skills are already installed",
        "- which skill should be triggered for a task",
        "- whether a workflow should reuse an existing skill before creating a new one",
        "",
        "Ignore backup or partial directories unless the user explicitly asks about them.",
        "",
    ]
    for category in CATEGORY_ORDER:
        if not groups.get(category):
            continue
        lines.append(f"## {category}")
        lines.append("")
        for block in groups[category]:
            lines.extend(block)
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = _parse_args()
    skills_dir = Path(args.skills_dir)
    output_path = Path(args.output)
    lock_dir = Path(args.lock_dir).expanduser() if args.lock_dir else None
    lock_path = maintenance_lock_path(skills_dir.parent, lock_dir)
    with FileLock(lock_path):
        text = generate_index(skills_dir)
        if args.apply:
            atomic_write_text(output_path, text)
        else:
            print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
