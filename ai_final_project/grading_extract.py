"""End-to-end extraction helpers for answer-key and submission numeric answers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from ai_final_project.cv_boxes import AnswerBoxDetection, detect_answer_region_from_pdf
from ai_final_project.ocr.engines import (
    DoctREngine,
    EasyOCREngine,
    OCREngine,
    OCREngineError,
    TesseractEngine,
)

_NUMERIC_PATTERN = re.compile(r"(?<!\d)(\d{1,3}(?:[.,]\d{1,4})?)(?!\d)")


@dataclass(frozen=True)
class CandidateNumber:
    value_text: str
    value: float
    confidence: float
    source: str


@dataclass(frozen=True)
class SubmissionExtraction:
    detection: AnswerBoxDetection
    numeric_answer: float
    numeric_answer_text: str
    best_candidate: CandidateNumber
    candidates: tuple[CandidateNumber, ...]


@dataclass(frozen=True)
class AnswerKeyScoring:
    expected_answer: float
    max_points: float
    wrong_points: float


def parse_numeric_answer_from_answer_key_pdf(pdf_path: Path | str) -> float:
    """Extract the primary numeric answer from an answer-key PDF."""
    text = _extract_pdf_text_local(Path(pdf_path))
    # Prefer explicit answer lines over phrases like "wrong answer = 3pts".
    strict_line_matches = re.findall(
        r"(?im)^\s*answer\s*[:=-]\s*([0-9]+(?:[.,][0-9]+)?)\s*$",
        text,
    )
    if strict_line_matches:
        return _to_float(strict_line_matches[0])

    # Secondary fallback: any "answer: <num>" token.
    labeled_matches = re.findall(r"\banswer\s*[:=-]\s*([0-9]+(?:[.,][0-9]+)?)", text, flags=re.IGNORECASE)
    if labeled_matches:
        # Prefer a decimal answer if present.
        decimal_first = [m for m in labeled_matches if "." in m or "," in m]
        return _to_float((decimal_first or labeled_matches)[0])

    # Fallback: first decimal-like token.
    values = list(_scan_numbers(text))
    if not values:
        raise ValueError("No numeric answer found in answer-key PDF text.")
    return values[0]


def parse_answer_key_scoring(pdf_path: Path | str) -> AnswerKeyScoring:
    text = _extract_pdf_text_local(Path(pdf_path))
    expected = parse_numeric_answer_from_answer_key_pdf(pdf_path)
    max_points = _extract_max_points(text)
    wrong_points = _extract_wrong_points(text)
    return AnswerKeyScoring(
        expected_answer=expected,
        max_points=max_points,
        wrong_points=wrong_points,
    )


def extract_submission_numeric_answer(
    submission_pdf_path: Path | str,
    *,
    page_index: int = 0,
) -> SubmissionExtraction:
    detection = detect_answer_region_from_pdf(Path(submission_pdf_path), page_index=page_index)
    if detection.marker_fill_ratio < 0.08:
        raise ValueError("Bottom-right marker box was not confidently detected as filled.")

    candidates = _collect_numeric_candidates(detection.answer_crop)
    if not candidates:
        raise ValueError("No numeric OCR candidates found in submission answer crop.")
    # Prefer decimal values for answer extraction, then confidence.
    best = max(candidates, key=lambda c: (_is_decimal_text(c.value_text), c.confidence))
    return SubmissionExtraction(
        detection=detection,
        numeric_answer=best.value,
        numeric_answer_text=best.value_text,
        best_candidate=best,
        candidates=tuple(sorted(candidates, key=lambda c: c.confidence, reverse=True)),
    )


def _collect_numeric_candidates(crop_gray: np.ndarray) -> list[CandidateNumber]:
    variants = _ocr_variants(crop_gray)
    # Keep runtime stable on lower-end machines by using the known-working local
    # engines in a fixed sequential order (no heavy all-profile ensemble loop).
    engines: list[tuple[OCREngine, str]] = [
        (EasyOCREngine(), "typed"),
        (TesseractEngine(), "typed"),
        (DoctREngine(), "typed"),
    ]
    candidates: list[CandidateNumber] = []
    for variant_name, image in variants:
        for engine, task in engines:
            try:
                pred = engine.predict(image, task=task)
            except OCREngineError:
                continue
            nums = [_to_float_text(n) for n in _extract_numeric_tokens(pred.text)]
            for text_val, num_val in nums:
                candidates.append(
                    CandidateNumber(
                        value_text=text_val,
                        value=num_val,
                        confidence=pred.confidence,
                        source=f"{variant_name}:{engine.name}",
                    )
                )
    return _dedupe_candidates(candidates)


def _ocr_variants(crop_gray: np.ndarray) -> list[tuple[str, np.ndarray]]:
    base = crop_gray if crop_gray.ndim == 2 else cv2.cvtColor(crop_gray, cv2.COLOR_BGR2GRAY)
    otsu = cv2.threshold(base, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    up2 = cv2.resize(base, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    # Keep a minimal set of variants to reduce memory/runtime spikes.
    return [
        ("base", base),
        ("otsu", otsu),
        ("up2", up2),
    ]


def _dedupe_candidates(items: Iterable[CandidateNumber]) -> list[CandidateNumber]:
    best_by_value: dict[float, CandidateNumber] = {}
    for item in items:
        prev = best_by_value.get(item.value)
        if prev is None or item.confidence > prev.confidence:
            best_by_value[item.value] = item
    return list(best_by_value.values())


def _scan_numbers(text: str) -> Iterable[float]:
    for token in _extract_numeric_tokens(text):
        yield _to_float(token)


def _extract_numeric_tokens(text: str) -> list[str]:
    # Normalize common OCR spacing around decimal separators: "3 . 45" -> "3.45"
    normalized = re.sub(r"(\d)\s*[.,]\s*(\d)", r"\1.\2", text)
    # Also handle OCR outputs that split a decimal into space-separated groups
    # for this assignment style, e.g. "3 45" -> "3.45".
    normalized = re.sub(r"\b(\d)\s+(\d{2})\b", r"\1.\2", normalized)
    return _NUMERIC_PATTERN.findall(normalized)


def _to_float_text(token: str) -> tuple[str, float]:
    normalized = token.replace(",", ".")
    return normalized, float(normalized)


def _to_float(token: str) -> float:
    return float(token.replace(",", "."))


def _is_decimal_text(text: str) -> bool:
    return "." in text or "," in text


def _extract_max_points(text: str) -> float:
    # Prefer early "N pts/points" mention for this single-question workflow.
    matches = re.findall(r"\b(\d+(?:[.,]\d+)?)\s*(?:pts?|points?)\b", text, flags=re.IGNORECASE)
    if not matches:
        return 1.0
    return _to_float(matches[0])


def _extract_wrong_points(text: str) -> float:
    # Allow phrases like "Wrong answer = 3pts" / "wrong answer: 3 points".
    match = re.search(
        r"wrong\s+answer\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*(?:pts?|points?)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return _to_float(match.group(1))
    return 0.0


def _extract_pdf_text_local(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception as e:
        raise RuntimeError(
            "PDF parsing requires local package 'pypdf'. Install with: pip install pypdf"
        ) from e

    reader = PdfReader(str(pdf_path))
    chunks: list[str] = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            chunks.append("")
    return "\n".join(chunks)
