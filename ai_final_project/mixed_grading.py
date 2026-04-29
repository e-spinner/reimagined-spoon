"""Pure mixed (math + written) scoring for one submission — used by the UI and unit tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ai_final_project.grading_extract import AnswerKeyScoring, SubmissionExtraction, extract_submission_numeric_answer
from ai_final_project.written_response_grader import (
    WrittenAnswerKey,
    WrittenResponseGradeResult,
    grade_written_response_pdf,
)


@dataclass(frozen=True)
class MixedScoreParts:
    """Scores and messages from one mixed grading pass (no PDF side effects)."""

    m_aw: float
    m_max: float
    w_aw: float
    w_max: float
    extracted: SubmissionExtraction | None
    written_result: WrittenResponseGradeResult | None
    item_parts: tuple[str, ...]
    """Human-readable fragments for the graded-items list."""
    review_delta: int
    """Count toward review banner: wrong math, math failure, written manual, written failure."""


def mixed_needs_from_kinds(kinds: Sequence[str]) -> tuple[bool, bool]:
    """Return (need_math, need_written) from per-question kind strings."""
    s = set(kinds)
    return ("math" in s), ("written" in s)


def combined_total_points(m_aw: float, m_max: float, w_aw: float, w_max: float) -> tuple[float, float, float]:
    """Return (total_awarded, total_max, percent_of_total_max)."""
    total_aw = m_aw + w_aw
    total_max = m_max + w_max
    pct = (total_aw / total_max * 100.0) if total_max > 0 else 0.0
    return total_aw, total_max, pct


def compute_mixed_scores(
    submission_path: Path,
    *,
    need_math: bool,
    need_written: bool,
    scoring: AnswerKeyScoring | None,
    written_key: WrittenAnswerKey | None,
) -> MixedScoreParts:
    """
    Run math and/or written graders independently (failures in one do not block the other).

    Caller is responsible for PDF overlays and written manual-review file append when
    ``written_result.requires_manual_review``.
    """
    m_aw = m_max = 0.0
    w_aw = w_max = 0.0
    extracted: SubmissionExtraction | None = None
    w_result: WrittenResponseGradeResult | None = None
    parts: list[str] = []
    review_delta = 0

    if need_math and scoring is not None:
        try:
            extracted = extract_submission_numeric_answer(submission_path)
            got = extracted.numeric_answer
            ok = abs(got - scoring.expected_answer) < 1e-6
            m_aw = scoring.max_points if ok else scoring.wrong_points
            m_max = scoring.max_points
            pct_m = (m_aw / m_max * 100.0) if m_max > 0 else 0.0
            if not ok:
                review_delta += 1
            parts.append(
                f"M: {got:.2f} vs {scoring.expected_answer:.2f} → {m_aw:.2f}/{m_max:.2f} ({pct_m:.1f}%)"
            )
        except Exception as me:
            m_max = scoring.max_points
            m_aw = 0.0
            parts.append(f"M: ⚠ {me}")
            review_delta += 1

    if need_written and written_key is not None:
        try:
            w_result = grade_written_response_pdf(submission_path, written_key)
            w_aw = w_result.points_awarded
            w_max = w_result.max_points
            pct_w = (w_aw / w_max * 100.0) if w_max > 0 else 0.0
            parts.append(
                f"W: keywords {w_result.keyword_hits}/{w_result.keyword_total} "
                f"→ {w_aw:.2f}/{w_max:.2f} ({pct_w:.1f}%)"
            )
            if w_result.requires_manual_review:
                review_delta += 1
        except Exception as we:
            w_max = written_key.max_points
            w_aw = 0.0
            w_result = None
            parts.append(f"W: ⚠ {we}")
            review_delta += 1

    return MixedScoreParts(
        m_aw=m_aw,
        m_max=m_max,
        w_aw=w_aw,
        w_max=w_max,
        extracted=extracted,
        written_result=w_result,
        item_parts=tuple(parts),
        review_delta=review_delta,
    )
