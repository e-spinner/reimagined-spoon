"""Unit tests for mixed math+written scoring helpers (`ai_final_project.mixed_grading`)."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import fitz

REPO_ROOT = Path(__file__).resolve().parents[1]
REF = REPO_ROOT / "Reference Materials"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_final_project.grading_extract import AnswerKeyScoring, parse_answer_key_scoring
from ai_final_project.written_response_grader import parse_written_answer_key_pdf
from ai_final_project.mixed_grading import (
    combined_total_points,
    compute_mixed_scores,
    mixed_needs_from_kinds,
)


class TestMixedNeedsFromKinds(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(mixed_needs_from_kinds([]), (False, False))

    def test_math_only(self) -> None:
        self.assertEqual(mixed_needs_from_kinds(["math", "math"]), (True, False))

    def test_written_only(self) -> None:
        self.assertEqual(mixed_needs_from_kinds(["written"]), (False, True))

    def test_both(self) -> None:
        self.assertEqual(
            mixed_needs_from_kinds(["math", "written", "math"]), (True, True)
        )


class TestCombinedTotalPoints(unittest.TestCase):
    def test_both_components(self) -> None:
        aw, mx, pct = combined_total_points(5.0, 10.0, 12.0, 20.0)
        self.assertAlmostEqual(aw, 17.0)
        self.assertAlmostEqual(mx, 30.0)
        self.assertAlmostEqual(pct, 100.0 * 17.0 / 30.0)

    def test_math_only(self) -> None:
        aw, mx, pct = combined_total_points(3.0, 5.0, 0.0, 0.0)
        self.assertAlmostEqual(aw, 3.0)
        self.assertAlmostEqual(mx, 5.0)
        self.assertAlmostEqual(pct, 60.0)

    def test_zero_max_returns_zero_percent(self) -> None:
        aw, mx, pct = combined_total_points(0.0, 0.0, 0.0, 0.0)
        self.assertAlmostEqual(aw, 0.0)
        self.assertAlmostEqual(mx, 0.0)
        self.assertAlmostEqual(pct, 0.0)


class TestComputeMixedScoresMathOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sub = REF / "Math Submissions" / "MichaelSmithHW1.pdf"
        cls.math_key = REF / "Math Answer Key.pdf"

    def test_correct_numeric_match(self) -> None:
        scoring = parse_answer_key_scoring(self.math_key)
        parts = compute_mixed_scores(
            self.sub,
            need_math=True,
            need_written=False,
            scoring=scoring,
            written_key=None,
        )
        self.assertIsNotNone(parts.extracted)
        assert parts.extracted is not None
        self.assertAlmostEqual(parts.extracted.numeric_answer, 3.45, places=2)
        self.assertAlmostEqual(parts.m_aw, scoring.max_points)
        self.assertAlmostEqual(parts.m_max, scoring.max_points)
        self.assertEqual(parts.w_max, 0.0)
        self.assertIsNone(parts.written_result)
        self.assertEqual(parts.review_delta, 0)
        self.assertEqual(len(parts.item_parts), 1)
        self.assertIn("M:", parts.item_parts[0])

    def test_wrong_answer_uses_wrong_points(self) -> None:
        scoring = AnswerKeyScoring(
            expected_answer=99.0, max_points=10.0, wrong_points=4.0
        )
        parts = compute_mixed_scores(
            self.sub,
            need_math=True,
            need_written=False,
            scoring=scoring,
            written_key=None,
        )
        self.assertAlmostEqual(parts.m_aw, 4.0)
        self.assertAlmostEqual(parts.m_max, 10.0)
        self.assertEqual(parts.review_delta, 1)
        self.assertIn("99.00", parts.item_parts[0])

    def test_math_extraction_failure_counts_review(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            bad = Path(tmp) / "no_marker.pdf"
            doc = fitz.open()
            doc.new_page()
            doc.save(str(bad))
            doc.close()
            scoring = parse_answer_key_scoring(self.math_key)
            parts = compute_mixed_scores(
                bad,
                need_math=True,
                need_written=False,
                scoring=scoring,
                written_key=None,
            )
        self.assertIsNone(parts.extracted)
        self.assertAlmostEqual(parts.m_aw, 0.0)
        self.assertAlmostEqual(parts.m_max, scoring.max_points)
        self.assertEqual(parts.review_delta, 1)
        self.assertTrue(parts.item_parts[0].startswith("M: ⚠"))


class TestComputeMixedScoresEdgeCases(unittest.TestCase):
    def test_need_written_without_key_produces_no_written_lines(self) -> None:
        sub = REF / "Writing Submissions" / "William_john.pdf"
        parts = compute_mixed_scores(
            sub,
            need_math=False,
            need_written=True,
            scoring=None,
            written_key=None,
        )
        self.assertEqual(parts.item_parts, ())
        self.assertIsNone(parts.written_result)
        self.assertEqual(parts.review_delta, 0)


class TestComputeMixedScoresWrittenOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sub = REF / "Writing Submissions" / "William_john.pdf"
        cls.wkey = REF / "Writing Anwer Key.pdf"

    def test_partial_keyword_score(self) -> None:
        key = parse_written_answer_key_pdf(self.wkey)
        parts = compute_mixed_scores(
            self.sub,
            need_math=False,
            need_written=True,
            scoring=None,
            written_key=key,
        )
        self.assertIsNone(parts.extracted)
        self.assertIsNotNone(parts.written_result)
        assert parts.written_result is not None
        self.assertGreater(parts.written_result.keyword_hits, 0)
        self.assertFalse(parts.written_result.requires_manual_review)
        self.assertGreater(parts.w_aw, 0.0)
        self.assertEqual(parts.review_delta, 0)
        self.assertIn("W:", parts.item_parts[0])


class TestComputeMixedScoresWrittenManualReview(unittest.TestCase):
    """Zero keyword hits increment review_delta (caller still appends manifest)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wkey = REF / "Writing Anwer Key.pdf"

    def test_empty_body_yields_review_delta(self) -> None:
        key = parse_written_answer_key_pdf(self.wkey)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            sub = Path(tmp) / "blankish.pdf"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Hello world unrelated text.")
            doc.save(str(sub))
            doc.close()
            parts = compute_mixed_scores(
                sub,
                need_math=False,
                need_written=True,
                scoring=None,
                written_key=key,
            )
        self.assertIsNotNone(parts.written_result)
        assert parts.written_result is not None
        self.assertTrue(parts.written_result.requires_manual_review)
        self.assertEqual(parts.written_result.keyword_hits, 0)
        self.assertGreaterEqual(parts.review_delta, 1)


class TestComputeMixedScoresBothComponents(unittest.TestCase):
    """One submission PDF: math marker path + body text for written."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.sub = REF / "Math Submissions" / "MichaelSmithHW1.pdf"
        cls.math_key = REF / "Math Answer Key.pdf"
        cls.wkey = REF / "Writing Anwer Key.pdf"

    def test_math_succeeds_and_written_runs_on_same_file(self) -> None:
        scoring = parse_answer_key_scoring(self.math_key)
        wkey = parse_written_answer_key_pdf(self.wkey)
        parts = compute_mixed_scores(
            self.sub,
            need_math=True,
            need_written=True,
            scoring=scoring,
            written_key=wkey,
        )
        self.assertIsNotNone(parts.extracted)
        self.assertIsNotNone(parts.written_result)
        total_aw, total_max, pct = combined_total_points(
            parts.m_aw, parts.m_max, parts.w_aw, parts.w_max
        )
        self.assertGreater(total_max, 0.0)
        self.assertGreaterEqual(total_aw, 0.0)
        self.assertGreaterEqual(pct, 0.0)
        self.assertEqual(len(parts.item_parts), 2)


if __name__ == "__main__":
    unittest.main()
