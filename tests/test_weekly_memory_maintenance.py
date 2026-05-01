import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from memory_utils import MemoryDocument, parse_memory_document  # noqa: E402
from weekly_memory_maintenance import detect_heading_styles, normalize_entry_headings, select_entries_to_archive  # noqa: E402


def _entry(entry_id: str, logged: str, summary: str) -> str:
    return f"""## [{entry_id}] sample title
**Logged**: {logged}
**Promote To ACTIVE**: none
**Promotion Confidence**: low
**Promotion Notes**: test

### Summary
{summary}
"""


class WeeklyMemoryMaintenanceTests(unittest.TestCase):
    def _parse_doc(self, text: str) -> MemoryDocument:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "MEMORY.md"
            path.write_text(text, encoding="utf-8")
            return parse_memory_document(path)

    def test_select_entries_to_archive_only_when_over_threshold(self) -> None:
        doc = self._parse_doc(
            "# TEST\n\n"
            + _entry("ERR-2026-04-01-a", "2026-04-01T00:00:00Z", "A")
            + "\n"
            + _entry("ERR-2026-04-02-b", "2026-04-02T00:00:00Z", "B")
            + "\n"
            + _entry("ERR-2026-04-20-c", "2026-04-20T00:00:00Z", "C")
            + "\n"
            + _entry("ERR-2026-04-29-d", "2026-04-29T00:00:00Z", "D")
        )
        selected = select_entries_to_archive(
            document=doc,
            current_line_count=200,
            max_lines=150,
            max_entries=3,
            target_lines=120,
            target_entries=2,
            cutoff=datetime(2026, 4, 25, tzinfo=UTC),
            min_remaining_entries=2,
        )
        self.assertEqual(
            [entry.entry_id for entry in selected],
            ["ERR-2026-04-01-a", "ERR-2026-04-02-b"],
        )

    def test_select_entries_to_archive_respects_threshold_and_recent_window(self) -> None:
        doc = self._parse_doc(
            "# TEST\n\n"
            + _entry("LRN-2026-04-28-a", "2026-04-28T00:00:00Z", "A")
            + "\n"
            + _entry("LRN-2026-04-29-b", "2026-04-29T00:00:00Z", "B")
            + "\n"
            + _entry("LRN-2026-04-30-c", "2026-04-30T00:00:00Z", "C")
        )
        selected = select_entries_to_archive(
            document=doc,
            current_line_count=90,
            max_lines=150,
            max_entries=5,
            target_lines=120,
            target_entries=4,
            cutoff=datetime(2026, 4, 25, tzinfo=UTC),
            min_remaining_entries=2,
        )
        self.assertEqual(selected, [])

    def test_detect_heading_styles_reports_mixed(self) -> None:
        text = (
            "# TEST\n\n"
            "## [LRN-2026-04-01-a] bracket title\n"
            "**Logged**: 2026-04-01T00:00:00Z\n\n"
            "### Summary\nA\n\n"
            "## ERR-2026-04-02-b plain title\n"
            "**Logged**: 2026-04-02T00:00:00Z\n\n"
            "### Summary\nB\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "MEMORY.md"
            path.write_text(text, encoding="utf-8")
            styles = detect_heading_styles(path)
        self.assertEqual(styles["bracketed"], 1)
        self.assertEqual(styles["plain"], 1)
        self.assertEqual(styles["mode"], "mixed")

    def test_normalize_entry_headings_rewrites_plain_form(self) -> None:
        doc = self._parse_doc(
            "# TEST\n\n"
            "## ERR-2026-04-02-b plain title\n"
            "**Logged**: 2026-04-02T00:00:00Z\n\n"
            "### Summary\nB\n"
        )
        changed = normalize_entry_headings(doc)
        self.assertEqual(changed, 1)
        self.assertIn("## [ERR-2026-04-02-b] plain title\n", doc.entries[0].raw)


if __name__ == "__main__":
    unittest.main()
