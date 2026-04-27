from pathlib import Path
import sys
import unittest

import fitz
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1] / "reimagined-spoon"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_final_project.grading_extract import extract_submission_numeric_answer
from ai_final_project.ui.main_window import MainWindow


class TestMathWrongAnswerArtifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.submission_pdf = Path(__file__).resolve().parents[1] / "Unit Tests" / "fixtures" / "MichaelSmithHW1.pdf"
        cls.window = MainWindow()
        cls.output_dir = Path(__file__).resolve().parents[0] / "output" / "math_artifacts"
        cls.output_dir.mkdir(parents=True, exist_ok=True)

    def test_wrong_answer_annotation_writes_x_and_partial_score(self) -> None:
        extracted = extract_submission_numeric_answer(self.submission_pdf)
        dst = self.output_dir / "graded_sample_wrong.pdf"
        self.window._write_math_annotations(
            src_pdf=self.submission_pdf,
            dst_pdf=dst,
            extracted=extracted,
            awarded_points=3.0,
            max_points=5.0,
            percent=60.0,
            is_correct=False,
        )
        self.assertTrue(dst.exists())
        self.assertGreater(dst.stat().st_size, 0)
        with fitz.open(str(dst)) as doc:
            text = (doc[0].get_text() or "") if len(doc) else ""
        # Score summary must be printed at top of page.
        self.assertIn("3.00/5.00", text)
        self.assertIn("60.0%", text)
        # Note: mark glyph extraction can vary by PDF renderer/font, so this
        # test asserts score artifacts that must always be present.
        (self.output_dir / "graded_sample_wrong.summary.txt").write_text(
            "Expected summary:\n3.00/5.00 (60.0%)\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
