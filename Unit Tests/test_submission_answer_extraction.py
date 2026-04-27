from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1] / "reimagined-spoon"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_final_project.grading_extract import (
    extract_submission_numeric_answer,
    parse_answer_key_scoring,
    parse_numeric_answer_from_answer_key_pdf,
)


class TestSubmissionAnswerExtraction(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.submission_pdf = Path(__file__).resolve().parents[1] / "Unit Tests" / "fixtures" / "MichaelSmithHW1.pdf"
        cls.answer_key_pdf = Path(__file__).resolve().parents[1] / "Unit Tests" / "fixtures" / "Example Answer key.pdf"

    def test_submission_bottom_right_marker_then_answer_crop_then_ocr(self) -> None:
        extracted = extract_submission_numeric_answer(self.submission_pdf)
        # Ensure marker-check precondition is met before accepting OCR result.
        self.assertGreater(extracted.detection.marker_fill_ratio, 0.08)
        self.assertAlmostEqual(extracted.numeric_answer, 3.45, places=2)

    def test_answer_key_parses_expected_numeric_answer(self) -> None:
        expected = parse_numeric_answer_from_answer_key_pdf(self.answer_key_pdf)
        self.assertAlmostEqual(expected, 3.45, places=2)

    def test_submission_matches_answer_key_expected_value(self) -> None:
        expected = parse_numeric_answer_from_answer_key_pdf(self.answer_key_pdf)
        extracted = extract_submission_numeric_answer(self.submission_pdf)
        self.assertAlmostEqual(extracted.numeric_answer, expected, places=2)

    def test_answer_key_scoring_points_parse(self) -> None:
        scoring = parse_answer_key_scoring(self.answer_key_pdf)
        self.assertAlmostEqual(scoring.expected_answer, 3.45, places=2)
        self.assertAlmostEqual(scoring.max_points, 5.0, places=2)
        self.assertAlmostEqual(scoring.wrong_points, 3.0, places=2)


if __name__ == "__main__":
    unittest.main()
