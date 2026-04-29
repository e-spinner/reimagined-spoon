"""Grade typed written-response submissions (PDF text) against keyword answer keys."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import fitz

from ai_final_project.grading_extract import _extract_pdf_text_local

_KEYWORD_LIST_PATTERN = re.compile(
    r"(?is)answer\s*keyword\s*list\s*:\s*(.*)",
)
_POINTS_PATTERN = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*(?:pts?|points?)\b", re.IGNORECASE)


@dataclass(frozen=True)
class WrittenAnswerKey:
    """Parsed written-response rubric from an answer-key PDF."""

    max_points: float
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class WrittenResponseGradeResult:
    max_points: float
    keyword_total: int
    keyword_hits: int
    matched_keywords: tuple[str, ...]
    points_awarded: float
    requires_manual_review: bool
    """True when zero keywords matched — submission should be listed for manual review."""

    hit_fraction: float


def parse_written_answer_key_pdf(pdf_path: Path | str) -> WrittenAnswerKey:
    """Parse max points and comma-separated keywords from a written answer-key PDF."""
    text = _extract_pdf_text_local(Path(pdf_path))
    max_points = _parse_max_points(text)
    keywords = _parse_keyword_list(text)
    if not keywords:
        raise ValueError("No keywords found after 'Answer keyword list:' in answer-key PDF.")
    return WrittenAnswerKey(max_points=max_points, keywords=keywords)


def extract_submission_text_pdf(pdf_path: Path | str) -> str:
    """Extract plain text from a typed submission PDF."""
    return _extract_pdf_text_local(Path(pdf_path))


def keyword_present_in_submission(submission_text: str, keyword: str) -> bool:
    """Return True if keyword appears in submission (case-insensitive, whitespace-tolerant)."""
    sub_norm = _normalize_for_match(submission_text)
    kw_norm = _normalize_for_match(keyword)
    if not kw_norm:
        return False
    if re.search(r"[\s\-]", kw_norm):
        return kw_norm in sub_norm
    return re.search(rf"(?<!\w){re.escape(kw_norm)}(?!\w)", sub_norm) is not None


def count_keyword_hits(submission_text: str, keywords: Sequence[str]) -> tuple[int, tuple[str, ...]]:
    """Count how many keywords match; return (hit_count, matched_keyword_strings in key order)."""
    matched: list[str] = []
    for kw in keywords:
        if keyword_present_in_submission(submission_text, kw):
            matched.append(kw)
    return len(matched), tuple(matched)


def _keyword_search_variants(keyword: str) -> tuple[str, ...]:
    """Strings to try with ``Page.search_for`` (PDF text may differ in case, spaces, hyphens)."""
    k = keyword.strip()
    if not k:
        return ()
    out: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    add(k)
    add(k.casefold())
    add(k.lower())
    add(k.upper())
    if k != k.title():
        add(k.title())
    collapsed = re.sub(r"\s+", " ", k)
    if collapsed != k:
        add(collapsed)
    if " " in k:
        add(k.replace(" ", "-"))
    if "-" in k:
        add(k.replace("-", " "))
    return tuple(out)


def rects_for_keyword_on_page(page: fitz.Page, keyword: str) -> list[fitz.Rect]:
    """Bounding boxes for a rubric keyword on one page (empty if not in the text layer)."""
    rects: list[fitz.Rect] = []
    seen: set[tuple[float, float, float, float]] = set()
    for variant in _keyword_search_variants(keyword):
        for r in page.search_for(variant, flags=fitz.TEXT_DEHYPHENATE):
            key = (round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2))
            if key not in seen:
                seen.add(key)
                rects.append(r)
    return rects


def apply_matched_keyword_highlights(
    doc: fitz.Document,
    matched_keywords: Sequence[str],
    *,
    max_per_keyword: int = 24,
) -> int:
    """
    Add PDF highlight annotations where each matched keyword appears (selectable text only).

    Returns the number of highlight annotations created.
    """
    total = 0
    for kw in matched_keywords:
        added = 0
        for pi in range(len(doc)):
            if added >= max_per_keyword:
                break
            page = doc[pi]
            for r in rects_for_keyword_on_page(page, kw):
                if added >= max_per_keyword:
                    break
                try:
                    annot = page.add_highlight_annot(r)
                    annot.update()
                    total += 1
                    added += 1
                except Exception:
                    continue
    return total


def half_keyword_threshold(total_keywords: int) -> int:
    """Smallest hit count that earns full credit (at least half of the list, rounded up)."""
    if total_keywords <= 0:
        return 0
    return (total_keywords + 1) // 2


def compute_written_points(
    hits: int,
    total_keywords: int,
    max_points: float,
) -> float:
    """
    Full max_points when hits >= ceil(total/2); otherwise proportional to hits/total.
    Caller should handle hits == 0 for manual review; points are still 0.0.
    """
    if total_keywords <= 0:
        return 0.0
    if hits >= half_keyword_threshold(total_keywords):
        return float(max_points)
    return float(max_points) * (hits / total_keywords)


def grade_written_response_pdf(
    submission_pdf_path: Path | str,
    answer_key: WrittenAnswerKey,
) -> WrittenResponseGradeResult:
    """Grade one submission PDF against a parsed written answer key."""
    submission_text = extract_submission_text_pdf(submission_pdf_path)
    return grade_written_response_text(submission_text, answer_key)


def grade_written_response_text(
    submission_text: str,
    answer_key: WrittenAnswerKey,
) -> WrittenResponseGradeResult:
    """Grade submission plain text against a parsed written answer key."""
    total = len(answer_key.keywords)
    hits, matched = count_keyword_hits(submission_text, answer_key.keywords)
    frac = hits / total if total else 0.0
    points = compute_written_points(hits, total, answer_key.max_points)
    manual = hits == 0
    return WrittenResponseGradeResult(
        max_points=answer_key.max_points,
        keyword_total=total,
        keyword_hits=hits,
        matched_keywords=matched,
        points_awarded=points,
        requires_manual_review=manual,
        hit_fraction=frac,
    )


def append_written_response_manual_review(
    manifest_path: Path | str,
    submission_path: Path | str,
    result: WrittenResponseGradeResult,
) -> Path:
    """
    Append a line for a zero-hit submission to a manual-review manifest.
    Creates the file with a header if it does not exist.
    """
    path = Path(manifest_path)
    sub = Path(submission_path)
    line = (
        f"- {sub.name}: 0/{result.keyword_total} keywords matched; "
        f"{result.points_awarded:.2f}/{result.max_points:.2f} pts (manual review required)\n"
    )
    header = (
        "Written-response submissions with zero keyword hits (manual review):\n\n"
    )
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        path.write_text(existing + line, encoding="utf-8")
    else:
        path.write_text(header + line, encoding="utf-8")
    return path


def _normalize_for_match(text: str) -> str:
    t = text.casefold()
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _parse_max_points(text: str) -> float:
    m = _POINTS_PATTERN.search(text)
    if not m:
        return 1.0
    return float(m.group(1).replace(",", "."))


def _parse_keyword_list(text: str) -> tuple[str, ...]:
    m = _KEYWORD_LIST_PATTERN.search(text)
    if not m:
        return ()
    body = m.group(1)
    parts = [p for p in (x.strip() for x in body.split(",")) if p]
    normalized = tuple(re.sub(r"\s+", " ", p).strip() for p in parts)
    return tuple(k for k in normalized if k)
