from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import fitz


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_final_project.written_response_grader import (
    WrittenAnswerKey,
    append_written_response_manual_review,
    compute_written_points,
    count_keyword_hits,
    extract_submission_text_pdf,
    grade_written_response_pdf,
    grade_written_response_text,
    half_keyword_threshold,
    keyword_present_in_submission,
    parse_written_answer_key_pdf,
)


class TestParseWrittenAnswerKeyPdf(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.writing_key = REPO_ROOT / "Reference Materials" / "Writing Anwer Key.pdf"

    def test_parses_points_and_keyword_count_from_reference_pdf(self) -> None:
        key = parse_written_answer_key_pdf(self.writing_key)
        self.assertAlmostEqual(key.max_points, 20.0, places=2)
        self.assertGreater(len(key.keywords), 30)
        self.assertIn("Carapace", key.keywords)
        self.assertIn("Straight Carapace Length", key.keywords)

    def test_raises_when_keyword_section_missing(self) -> None:
        import fitz

        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            path = Path(tmp) / "bad_key.pdf"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "10 points\nNo keyword list in this key.")
            doc.save(str(path))
            doc.close()
            with self.assertRaises(ValueError) as ctx:
                parse_written_answer_key_pdf(path)
            self.assertIn("No keywords", str(ctx.exception))


class TestKeywordMatching(unittest.TestCase):
    def test_case_insensitive_single_word(self) -> None:
        self.assertTrue(keyword_present_in_submission("The CARAPACE is hard.", "carapace"))

    def test_phrase_with_internal_whitespace_in_submission(self) -> None:
        self.assertTrue(
            keyword_present_in_submission("Salt\n\nGlands behind the eyes.", "Salt Glands")
        )

    def test_word_boundary_avoids_substring_false_positive(self) -> None:
        self.assertFalse(keyword_present_in_submission("CCL is curved length.", "SCL"))

    def test_hyphenated_phrase_treated_as_phrase_match(self) -> None:
        self.assertTrue(keyword_present_in_submission("See salt-glands here.", "salt-glands"))


class TestHalfThresholdAndScoring(unittest.TestCase):
    def test_half_keyword_threshold(self) -> None:
        self.assertEqual(half_keyword_threshold(1), 1)
        self.assertEqual(half_keyword_threshold(4), 2)
        self.assertEqual(half_keyword_threshold(5), 3)
        self.assertEqual(half_keyword_threshold(35), 18)

    def test_full_points_when_hits_reach_half(self) -> None:
        self.assertEqual(compute_written_points(18, 35, 20.0), 20.0)
        self.assertEqual(compute_written_points(35, 35, 20.0), 20.0)

    def test_partial_points_below_half(self) -> None:
        # 17/35 of max 20 → proportional
        self.assertAlmostEqual(compute_written_points(17, 35, 20.0), 20.0 * 17.0 / 35.0, places=6)

    def test_zero_hits_yields_zero_points(self) -> None:
        self.assertEqual(compute_written_points(0, 10, 5.0), 0.0)


class TestGradeWrittenResponseText(unittest.TestCase):
    def test_zero_keywords_triggers_manual_review(self) -> None:
        key = WrittenAnswerKey(max_points=10.0, keywords=("alpha", "beta", "gamma", "delta"))
        result = grade_written_response_text("No rubric terms in this answer.", key)
        self.assertEqual(result.keyword_hits, 0)
        self.assertTrue(result.requires_manual_review)
        self.assertEqual(result.points_awarded, 0.0)
        self.assertEqual(result.matched_keywords, ())

    def test_full_credit_at_exactly_half_for_even_count(self) -> None:
        key = WrittenAnswerKey(max_points=8.0, keywords=("a", "b", "c", "d"))
        text = "a and c only here"
        result = grade_written_response_text(text, key)
        self.assertEqual(result.keyword_hits, 2)
        self.assertFalse(result.requires_manual_review)
        self.assertAlmostEqual(result.points_awarded, 8.0, places=6)

    def test_partial_credit_when_below_half(self) -> None:
        key = WrittenAnswerKey(max_points=10.0, keywords=("a", "b", "c", "d"))
        text = "only a appears"
        result = grade_written_response_text(text, key)
        self.assertEqual(result.keyword_hits, 1)
        self.assertFalse(result.requires_manual_review)
        self.assertAlmostEqual(result.points_awarded, 10.0 * 0.25, places=6)

    def test_count_keyword_hits_order(self) -> None:
        key = WrittenAnswerKey(max_points=1.0, keywords=("zebra", "apple"))
        hits, matched = count_keyword_hits("apple then zebra", key.keywords)
        self.assertEqual(hits, 2)
        self.assertEqual(matched, ("zebra", "apple"))


class TestAppendManualReview(unittest.TestCase):
    def test_creates_file_with_header_and_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "written_response_manual_review.txt"
            key = WrittenAnswerKey(max_points=5.0, keywords=("x",))
            result = grade_written_response_text("", key)
            append_written_response_manual_review(manifest, Path(tmp) / "s1.pdf", result)
            self.assertTrue(manifest.exists())
            body = manifest.read_text(encoding="utf-8")
            self.assertIn("zero keyword hits", body)
            self.assertIn("s1.pdf", body)
            self.assertIn("0/1 keywords", body)

    def test_appends_second_line_without_duplicating_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "review.txt"
            key = WrittenAnswerKey(max_points=5.0, keywords=("x",))
            r1 = grade_written_response_text("", key)
            append_written_response_manual_review(manifest, Path(tmp) / "a.pdf", r1)
            append_written_response_manual_review(manifest, Path(tmp) / "b.pdf", r1)
            lines = [ln for ln in manifest.read_text(encoding="utf-8").splitlines() if ln.startswith("- ")]
            self.assertEqual(len(lines), 2)
            self.assertEqual(manifest.read_text(encoding="utf-8").count("zero keyword hits"), 1)


class TestMainWindowWrittenAnnotations(unittest.TestCase):
    """Smoke-test PDF overlay used by the Written grading UI path."""

    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication

        from ai_final_project.ui.main_window import MainWindow

        cls.app = QApplication.instance() or QApplication([])
        cls.window = MainWindow()
        ref = REPO_ROOT / "Reference Materials"
        cls.key_path = ref / "Writing Anwer Key.pdf"
        cls.sub_path = ref / "Writing Submissions" / "William_john.pdf"

    def test_write_written_annotations_embeds_score_lines(self) -> None:
        key = parse_written_answer_key_pdf(self.key_path)
        result = grade_written_response_pdf(self.sub_path, key)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            out = Path(tmp) / "graded_written_ui.pdf"
            self.window._write_written_annotations(
                src_pdf=self.sub_path, dst_pdf=out, result=result
            )
            with fitz.open(str(out)) as doc:
                text = (doc[0].get_text() or "") if len(doc) else ""
        self.assertIn(f"{result.points_awarded:.2f}/{result.max_points:.2f}", text)
        self.assertIn(f"Keywords {result.keyword_hits}/{result.keyword_total}", text)


class TestReferenceMaterialsIntegration(unittest.TestCase):
    """End-to-end on PDFs under Reference Materials/."""

    @classmethod
    def setUpClass(cls) -> None:
        ref = REPO_ROOT / "Reference Materials"
        cls.key_path = ref / "Writing Anwer Key.pdf"
        cls.sub_path = ref / "Writing Submissions" / "William_john.pdf"

    def test_submission_pdf_text_non_empty(self) -> None:
        text = extract_submission_text_pdf(self.sub_path)
        self.assertIn("carapace", text.lower())

    def test_william_john_partial_credit_not_manual_review(self) -> None:
        key = parse_written_answer_key_pdf(self.key_path)
        result = grade_written_response_pdf(self.sub_path, key)
        self.assertGreater(result.keyword_hits, 0)
        self.assertFalse(result.requires_manual_review)
        self.assertLess(result.points_awarded, result.max_points)
        self.assertLess(result.keyword_hits, half_keyword_threshold(result.keyword_total))


if __name__ == "__main__":
    unittest.main()
