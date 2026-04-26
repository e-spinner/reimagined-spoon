"""OpenCV-based detection for assignment answer boxes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import fitz
import numpy as np


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class AnswerBoxDetection:
    marker_box: Rect
    answer_box: Rect
    marker_fill_ratio: float
    answer_crop: np.ndarray


@dataclass(frozen=True)
class DebugImagePaths:
    overlay_path: Path
    marker_crop_path: Path
    answer_crop_path: Path


def detect_answer_region_from_pdf(
    pdf_path: Path | str,
    *,
    page_index: int = 0,
    dpi: int = 220,
) -> AnswerBoxDetection:
    image = _render_pdf_page_to_bgr(pdf_path, page_index=page_index, dpi=dpi)
    return detect_answer_region_from_image(image)


def export_detection_debug_images(
    pdf_path: Path | str,
    output_dir: Path | str,
    *,
    page_index: int = 0,
    dpi: int = 220,
    prefix: str = "detection",
) -> DebugImagePaths:
    """Write visual debug artifacts so humans can review detected boxes."""
    image = _render_pdf_page_to_bgr(pdf_path, page_index=page_index, dpi=dpi)
    detection = detect_answer_region_from_image(image)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    overlay = image.copy()
    m = detection.marker_box
    a = detection.answer_box
    cv2.rectangle(overlay, (m.x, m.y), (m.x + m.w, m.y + m.h), (0, 0, 255), 3)
    cv2.rectangle(overlay, (a.x, a.y), (a.x + a.w, a.y + a.h), (0, 200, 0), 3)
    cv2.putText(
        overlay,
        f"marker fill={detection.marker_fill_ratio:.3f}",
        (max(0, m.x - 20), max(25, m.y - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (30, 30, 220),
        2,
        cv2.LINE_AA,
    )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    marker_crop = _crop_with_padding(gray, m, pad=4)

    overlay_path = out_dir / f"{prefix}_overlay.png"
    marker_crop_path = out_dir / f"{prefix}_marker_crop.png"
    answer_crop_path = out_dir / f"{prefix}_answer_crop.png"

    cv2.imwrite(str(overlay_path), overlay)
    cv2.imwrite(str(marker_crop_path), marker_crop)
    cv2.imwrite(str(answer_crop_path), detection.answer_crop)

    return DebugImagePaths(
        overlay_path=overlay_path,
        marker_crop_path=marker_crop_path,
        answer_crop_path=answer_crop_path,
    )


def detect_answer_region_from_image(image_bgr: np.ndarray) -> AnswerBoxDetection:
    if image_bgr is None or image_bgr.size == 0:
        raise ValueError("Input image is empty.")

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        21,
        9,
    )

    boxes = _extract_rectangular_boxes(bw)
    if not boxes:
        raise ValueError("No rectangle-like boxes detected on page.")

    marker_box, marker_fill = _find_filled_lower_right_marker(gray, bw, boxes)
    answer_box = _find_answer_box_near_marker(boxes, marker_box)
    answer_crop = _crop_with_padding(gray, answer_box, pad=4)
    return AnswerBoxDetection(
        marker_box=marker_box,
        answer_box=answer_box,
        marker_fill_ratio=marker_fill,
        answer_crop=answer_crop,
    )


def _render_pdf_page_to_bgr(pdf_path: Path | str, *, page_index: int, dpi: int) -> np.ndarray:
    doc = fitz.open(str(pdf_path))
    try:
        if page_index < 0 or page_index >= len(doc):
            raise ValueError(f"page_index {page_index} is out of bounds for PDF length {len(doc)}.")
        page = doc[page_index]
        zoom = dpi / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    finally:
        doc.close()


def _extract_rectangular_boxes(binary_inv: np.ndarray) -> list[Rect]:
    contours, _ = cv2.findContours(binary_inv, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    height, width = binary_inv.shape[:2]
    page_area = height * width
    out: list[Rect] = []

    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.03 * peri, True)
        if len(approx) != 4:
            continue
        x, y, w, h = cv2.boundingRect(approx)
        area = w * h
        if area < 160 or area > page_area * 0.2:
            continue
        aspect = w / max(1, h)
        if not (0.5 <= aspect <= 12.0):
            continue
        if w <= 8 or h <= 8:
            continue
        out.append(Rect(x=x, y=y, w=w, h=h))

    return _dedupe_nearby_boxes(out)


def _dedupe_nearby_boxes(boxes: list[Rect]) -> list[Rect]:
    if not boxes:
        return []
    ordered = sorted(boxes, key=lambda b: (b.x, b.y, b.w * b.h))
    deduped: list[Rect] = []
    for box in ordered:
        keep = True
        for existing in deduped:
            if (
                abs(box.x - existing.x) <= 3
                and abs(box.y - existing.y) <= 3
                and abs(box.w - existing.w) <= 4
                and abs(box.h - existing.h) <= 4
            ):
                keep = False
                break
        if keep:
            deduped.append(box)
    return deduped


def _find_filled_lower_right_marker(
    gray: np.ndarray,
    binary_inv: np.ndarray,
    boxes: list[Rect],
) -> tuple[Rect, float]:
    height, width = gray.shape[:2]
    candidates: list[tuple[float, Rect, float]] = []

    for box in boxes:
        area = box.w * box.h
        if area < 160 or area > 6000:
            continue
        if box.x < width * 0.45 or box.y < height * 0.45:
            continue
        aspect = box.w / max(1, box.h)
        if not (0.65 <= aspect <= 1.35):
            continue

        roi = binary_inv[box.y : box.y + box.h, box.x : box.x + box.w]
        if roi.size == 0:
            continue
        fill_ratio = float(np.count_nonzero(roi)) / float(roi.size)

        corner_bias = (box.x / width) + (box.y / height)
        score = fill_ratio * 3.0 + corner_bias
        if fill_ratio < 0.08:
            continue
        candidates.append((score, box, fill_ratio))

    if not candidates:
        raise ValueError("Could not find a filled lower-right marker box.")

    candidates.sort(key=lambda item: item[0], reverse=True)
    _score, best_box, best_fill = candidates[0]
    return best_box, best_fill


def _find_answer_box_near_marker(boxes: list[Rect], marker_box: Rect) -> Rect:
    marker_center_y = marker_box.y + marker_box.h / 2.0
    candidates: list[tuple[float, Rect]] = []

    for box in boxes:
        if box.x >= marker_box.x:
            continue
        if box.w <= marker_box.w * 2.0:
            continue
        if box.h <= marker_box.h * 1.2:
            continue

        center_y = box.y + box.h / 2.0
        y_penalty = abs(center_y - marker_center_y)
        # Reject boxes too far vertically from the marker; these are usually
        # unrelated page regions (headers or other sections).
        if y_penalty > 420:
            continue
        x_distance = marker_box.x - (box.x + box.w)
        if x_distance < -6:
            continue
        x_penalty = max(0.0, x_distance)
        # The answer box should be reasonably close to the marker horizontally.
        if x_penalty > 320:
            continue

        area_bonus = box.w * box.h
        # Favor local proximity over raw area so huge distant rectangles do not win.
        score = area_bonus - (y_penalty * 220.0) - (x_penalty * 35.0)
        candidates.append((score, box))

    if not candidates:
        raise ValueError("Could not locate answer box associated with marker box.")

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _crop_with_padding(gray: np.ndarray, box: Rect, *, pad: int) -> np.ndarray:
    h, w = gray.shape[:2]
    x0 = max(0, box.x - pad)
    y0 = max(0, box.y - pad)
    x1 = min(w, box.x + box.w + pad)
    y1 = min(h, box.y + box.h + pad)
    return gray[y0:y1, x0:x1].copy()
