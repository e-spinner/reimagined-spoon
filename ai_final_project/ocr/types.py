"""Shared OCR datatypes used by engine adapters and ensemble logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


OCRTask = Literal["typed", "handwriting", "mixed"]


@dataclass(frozen=True)
class OCRPrediction:
    engine: str
    text: str
    confidence: float
    task: OCRTask


@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float
    task: OCRTask
    needs_review: bool
    predictions: tuple[OCRPrediction, ...]


ImageArray = np.ndarray
