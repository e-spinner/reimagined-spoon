"""Modular OCR ensemble interfaces and default engine adapters."""

from ai_final_project.ocr.ensemble import EnsembleConfig, OCREnsemble
from ai_final_project.ocr.engines import OCREngine, OCREngineError, default_engines
from ai_final_project.ocr.types import OCRPrediction, OCRResult, OCRTask

__all__ = [
    "EnsembleConfig",
    "OCREnsemble",
    "OCREngine",
    "OCREngineError",
    "OCRPrediction",
    "OCRResult",
    "OCRTask",
    "default_engines",
]
