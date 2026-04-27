"""Task-aware OCR ensemble orchestration."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from ai_final_project.ocr.engines import OCREngine, OCREngineError, default_engines
from ai_final_project.ocr.types import ImageArray, OCRPrediction, OCRResult, OCRTask


DEFAULT_PROFILE_ENGINES: dict[OCRTask, tuple[str, ...]] = {
    "typed": ("paddleocr", "tesseract", "easyocr", "doctr"),
    "handwriting": ("trocr", "easyocr", "kraken", "calamari"),
    "mixed": ("paddleocr", "easyocr", "trocr", "tesseract", "doctr", "kraken", "calamari"),
}

DEFAULT_ENGINE_WEIGHTS: dict[str, float] = {
    "paddleocr": 1.15,
    "tesseract": 1.05,
    "easyocr": 1.0,
    "doctr": 1.0,
    "trocr": 1.2,
    "kraken": 1.0,
    "calamari": 1.0,
}


@dataclass(frozen=True)
class EnsembleConfig:
    low_confidence_threshold: float = 0.7
    min_agreement_count: int = 2


class OCREnsemble:
    def __init__(
        self,
        *,
        engines: dict[str, OCREngine] | None = None,
        profile_engines: dict[OCRTask, tuple[str, ...]] | None = None,
        engine_weights: dict[str, float] | None = None,
        config: EnsembleConfig | None = None,
    ) -> None:
        self._engines = engines or default_engines()
        self._profile_engines = profile_engines or DEFAULT_PROFILE_ENGINES
        self._engine_weights = engine_weights or DEFAULT_ENGINE_WEIGHTS
        self._config = config or EnsembleConfig()

    def recognize(self, image: ImageArray, *, task: OCRTask) -> OCRResult:
        predictions = self._run_profile(image, task=task)
        if not predictions:
            raise OCREngineError(f"No OCR predictions available for task={task}.")
        selected_text, selected_conf, agreement = self._aggregate(predictions)
        needs_review = (
            selected_conf < self._config.low_confidence_threshold
            or agreement < self._config.min_agreement_count
            or not selected_text.strip()
        )
        return OCRResult(
            text=selected_text,
            confidence=selected_conf,
            task=task,
            needs_review=needs_review,
            predictions=tuple(predictions),
        )

    def _run_profile(self, image: ImageArray, *, task: OCRTask) -> list[OCRPrediction]:
        predictions: list[OCRPrediction] = []
        for engine_name in self._profile_engines[task]:
            engine = self._engines.get(engine_name)
            if engine is None or not engine.supports_task(task):
                continue
            try:
                pred = engine.predict(image, task=task)
            except OCREngineError:
                continue
            if pred.text.strip():
                predictions.append(pred)
        return predictions

    def _aggregate(self, predictions: list[OCRPrediction]) -> tuple[str, float, int]:
        normalized_map: dict[str, list[OCRPrediction]] = defaultdict(list)
        for p in predictions:
            normalized_map[self._normalize_text(p.text)].append(p)

        majority_count = max(len(group) for group in normalized_map.values())
        majority_groups = [group for group in normalized_map.values() if len(group) == majority_count]

        if len(majority_groups) == 1:
            best_group = majority_groups[0]
        else:
            # Tie-break with weighted confidence.
            best_group = max(majority_groups, key=self._group_weighted_score)

        best_raw_text = Counter(p.text for p in best_group).most_common(1)[0][0]
        weighted_scores = [self._weighted_confidence(p) for p in best_group]
        aggregate_conf = sum(weighted_scores) / max(1, len(weighted_scores))
        return best_raw_text, max(0.0, min(1.0, aggregate_conf)), len(best_group)

    def _group_weighted_score(self, group: list[OCRPrediction]) -> float:
        return sum(self._weighted_confidence(p) for p in group)

    def _weighted_confidence(self, prediction: OCRPrediction) -> float:
        w = self._engine_weights.get(prediction.engine, 1.0)
        return prediction.confidence * w

    @staticmethod
    def _normalize_text(text: str) -> str:
        lowered = text.strip().lower()
        lowered = re.sub(r"\s+", " ", lowered)
        lowered = re.sub(r"[^\w\s]", "", lowered)
        return lowered.strip()
