from pathlib import Path
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1] / "reimagined-spoon"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_final_project.ocr.ensemble import OCREnsemble
from ai_final_project.ocr.engines import OCREngine
from ai_final_project.ocr.types import OCRPrediction


class _FakeEngine(OCREngine):
    def __init__(self, *, name: str, typed: bool, handwriting: bool, text: str, confidence: float) -> None:
        super().__init__(name=name, supports_typed=typed, supports_handwriting=handwriting)
        self._text = text
        self._confidence = confidence
        self.calls: list[str] = []

    def predict(self, image: np.ndarray, task: str) -> OCRPrediction:
        self.calls.append(task)
        return OCRPrediction(
            engine=self.name,
            text=self._text,
            confidence=self._confidence,
            task=task,  # type: ignore[arg-type]
        )


class TestOCREnsemble(unittest.TestCase):
    def setUp(self) -> None:
        self.image = np.zeros((64, 200), dtype=np.uint8)

    def test_typed_profile_uses_typed_capable_engines(self) -> None:
        engines = {
            "typed_engine": _FakeEngine(
                name="typed_engine",
                typed=True,
                handwriting=False,
                text="Ohm's law",
                confidence=0.9,
            ),
            "hand_engine": _FakeEngine(
                name="hand_engine",
                typed=False,
                handwriting=True,
                text="Wrong",
                confidence=0.9,
            ),
        }
        ensemble = OCREnsemble(
            engines=engines,
            profile_engines={"typed": ("typed_engine", "hand_engine"), "handwriting": ("hand_engine",), "mixed": ("typed_engine", "hand_engine")},
            engine_weights={"typed_engine": 1.0, "hand_engine": 1.0},
        )
        result = ensemble.recognize(self.image, task="typed")
        self.assertEqual(result.text, "Ohm's law")
        self.assertEqual(engines["typed_engine"].calls, ["typed"])
        self.assertEqual(engines["hand_engine"].calls, [])

    def test_majority_vote_prefers_agreement(self) -> None:
        engines = {
            "a": _FakeEngine(name="a", typed=True, handwriting=True, text="newtons second law", confidence=0.85),
            "b": _FakeEngine(name="b", typed=True, handwriting=True, text="Newton's second law", confidence=0.82),
            "c": _FakeEngine(name="c", typed=True, handwriting=True, text="random text", confidence=0.95),
        }
        ensemble = OCREnsemble(
            engines=engines,
            profile_engines={"typed": ("a", "b", "c"), "handwriting": ("a", "b", "c"), "mixed": ("a", "b", "c")},
            engine_weights={"a": 1.0, "b": 1.0, "c": 1.0},
        )
        result = ensemble.recognize(self.image, task="typed")
        self.assertIn("second law", result.text.lower())
        self.assertFalse(result.needs_review)

    def test_low_confidence_or_disagreement_sets_review_flag(self) -> None:
        engines = {
            "a": _FakeEngine(name="a", typed=True, handwriting=True, text="alpha", confidence=0.4),
            "b": _FakeEngine(name="b", typed=True, handwriting=True, text="beta", confidence=0.35),
            "c": _FakeEngine(name="c", typed=True, handwriting=True, text="gamma", confidence=0.3),
        }
        ensemble = OCREnsemble(
            engines=engines,
            profile_engines={"typed": ("a", "b", "c"), "handwriting": ("a", "b", "c"), "mixed": ("a", "b", "c")},
            engine_weights={"a": 1.0, "b": 1.0, "c": 1.0},
        )
        result = ensemble.recognize(self.image, task="handwriting")
        self.assertTrue(result.needs_review)


if __name__ == "__main__":
    unittest.main()
