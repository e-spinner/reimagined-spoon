"""Verify math then written PDF overlays stack (mixed-mode PDF pipeline)."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import fitz
from PySide6.QtWidgets import QApplication

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_final_project.grading_extract import extract_submission_numeric_answer, parse_answer_key_scoring
from ai_final_project.written_response_grader import (
    grade_written_response_pdf,
    parse_written_answer_key_pdf,
)


class TestMathThenWrittenOverlayChain(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from ai_final_project.ui.main_window import MainWindow

        cls.window = MainWindow()
        cls.sub = REPO_ROOT / "Unit Tests" / "fixtures" / "MichaelSmithHW1.pdf"
        cls.math_key = REPO_ROOT / "Unit Tests" / "fixtures" / "Example Answer key.pdf"
        cls.wkey = REPO_ROOT / "Reference Materials" / "Writing example answer key.pdf"

    def test_math_tmp_then_written_contains_both_summaries(self) -> None:
        scoring = parse_answer_key_scoring(self.math_key)
        extracted = extract_submission_numeric_answer(self.sub)
        ok = abs(extracted.numeric_answer - scoring.expected_answer) < 1e-6
        m_aw = scoring.max_points if ok else scoring.wrong_points
        wkey = parse_written_answer_key_pdf(self.wkey)
        w_result = grade_written_response_pdf(self.sub, wkey)

        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmp_m = Path(tmp) / "m.pdf"
            out = Path(tmp) / "final.pdf"
            self.window._write_math_annotations(
                src_pdf=self.sub,
                dst_pdf=tmp_m,
                extracted=extracted,
                awarded_points=m_aw,
                max_points=scoring.max_points,
                percent=(m_aw / scoring.max_points * 100.0) if scoring.max_points > 0 else 0.0,
                is_correct=ok,
            )
            self.window._write_written_annotations(
                src_pdf=tmp_m,
                dst_pdf=out,
                result=w_result,
                y_offset=78.0,
            )
            with fitz.open(str(out)) as doc:
                text = (doc[0].get_text() or "") if len(doc) else ""

        self.assertIn(f"{m_aw:.2f}/{scoring.max_points:.2f}", text)
        self.assertIn(f"{w_result.points_awarded:.2f}/{w_result.max_points:.2f}", text)
        self.assertIn(f"Keywords {w_result.keyword_hits}/{w_result.keyword_total}", text)


if __name__ == "__main__":
    unittest.main()
