"""Tests for MainWindow mixed-mode UI helpers (row kinds, written key label)."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

from PySide6.QtWidgets import QLabel, QApplication

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_final_project.ui import main_window as mw


class TestMixedRowKindWidgets(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from ai_final_project.ui.main_window import MainWindow

        cls.window = MainWindow()

    def setUp(self) -> None:
        self.window._mixed_question_list.clear()
        self.window._ensure_mixed_stub_items()

    def test_default_stub_order(self) -> None:
        kinds = self.window._collect_mixed_question_kinds()
        self.assertEqual(kinds, ["math", "written", "math", "written"])

    def test_apply_mixed_row_kind_updates_item_data(self) -> None:
        item = self.window._mixed_question_list.item(0)
        self.assertIsNotNone(item)
        row = self.window._mixed_question_list.itemWidget(item)
        self.assertIsNotNone(row)
        type_labels = [w for w in row.findChildren(QLabel) if w.objectName() == "CaptionMuted"]
        self.assertEqual(len(type_labels), 1)
        lbl = type_labels[0]
        self.window._apply_mixed_row_kind(item, lbl, "written")
        self.assertEqual(item.data(mw._MIXED_KIND_ROLE), "written")
        self.assertEqual(lbl.text(), "Written")
        self.window._apply_mixed_row_kind(item, lbl, "math")
        self.assertEqual(item.data(mw._MIXED_KIND_ROLE), "math")
        self.assertEqual(lbl.text(), "Math")

    def test_all_written_kinds_collection(self) -> None:
        for i in range(self.window._mixed_question_list.count()):
            item = self.window._mixed_question_list.item(i)
            row = self.window._mixed_question_list.itemWidget(item)
            assert item is not None and row is not None
            lbl = [w for w in row.findChildren(QLabel) if w.objectName() == "CaptionMuted"][0]
            self.window._apply_mixed_row_kind(item, lbl, "written")
        self.assertEqual(self.window._collect_mixed_question_kinds(), ["written"] * 4)


if __name__ == "__main__":
    unittest.main()
