"""OCR engine adapters with lazy optional imports."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from ai_final_project.ocr.types import ImageArray, OCRPrediction, OCRTask


class OCREngineError(RuntimeError):
    """Raised when an OCR backend is unavailable or fails."""


@dataclass(frozen=True)
class OCREngine:
    name: str
    supports_typed: bool
    supports_handwriting: bool

    def supports_task(self, task: OCRTask) -> bool:
        if task == "typed":
            return self.supports_typed
        if task == "handwriting":
            return self.supports_handwriting
        return self.supports_typed or self.supports_handwriting

    def predict(self, image: ImageArray, task: OCRTask) -> OCRPrediction:
        raise NotImplementedError


def _ensure_grayscale(image: ImageArray) -> ImageArray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _normalize_confidence(value: float | None) -> float:
    if value is None:
        return 0.5
    return max(0.0, min(1.0, float(value)))


def _project_cache_dir() -> Path:
    # Default to a writable cache inside the repo so sandboxed runs don't
    # attempt to write into the user's home directory.
    raw = os.environ.get("AI_FINAL_PROJECT_CACHE_DIR")
    if raw and raw.strip():
        out = Path(raw).expanduser()
    else:
        # .../reimagined-spoon/ai_final_project/ocr/engines.py -> parents[2] = repo root
        out = Path(__file__).resolve().parents[2] / ".cache"
    # If a relative cache dir was provided, resolve it relative to repo root.
    if not out.is_absolute():
        out = (Path(__file__).resolve().parents[2] / out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    return out


def _set_default_cache_env() -> None:
    cache = _project_cache_dir()
    def _set_if_unset_or_relative(name: str, value: str) -> None:
        cur = os.environ.get(name)
        if not cur:
            os.environ[name] = value
            return
        # If something set it to a relative path, upgrade to our absolute cache dir.
        if not Path(cur).expanduser().is_absolute():
            os.environ[name] = value

    _set_if_unset_or_relative("EASYOCR_MODULE_PATH", str(cache / "easyocr"))
    _set_if_unset_or_relative("DOCTR_CACHE_DIR", str(cache / "doctr"))
    _set_if_unset_or_relative("HF_HOME", str(cache / "hf"))
    _set_if_unset_or_relative("TRANSFORMERS_CACHE", str(cache / "hf" / "transformers"))
    # ModelScope (used by PaddleX as a fallback model hoster) defaults to ~/.cache/modelscope
    _set_if_unset_or_relative("MODELSCOPE_CACHE", str(cache / "modelscope"))
    _set_if_unset_or_relative("MODELSCOPE_CACHE_DIR", str(cache / "modelscope"))
    # PaddleX/PaddleOCR uses this for its cache (defaults to ~/.paddlex).
    _set_if_unset_or_relative("PADDLE_PDX_CACHE_HOME", str(cache / "paddlex"))
    _set_if_unset_or_relative("PADDLE_HOME", str(cache / "paddle"))
    # Avoid hard-failing when hoster connectivity checks are blocked.
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


class TesseractEngine(OCREngine):
    def __init__(self) -> None:
        super().__init__(name="tesseract", supports_typed=True, supports_handwriting=False)

    def predict(self, image: ImageArray, task: OCRTask) -> OCRPrediction:
        try:
            import pytesseract
        except ImportError as exc:
            raise OCREngineError("pytesseract is not installed.") from exc

        gray = _ensure_grayscale(image)
        config = "--psm 6"
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT, config=config)
        text = " ".join(token for token in data.get("text", []) if token and token.strip())
        confidences = [
            float(c) / 100.0
            for c in data.get("conf", [])
            if isinstance(c, (str, int, float)) and str(c) not in {"-1", ""}
        ]
        conf = sum(confidences) / len(confidences) if confidences else 0.5
        return OCRPrediction(engine=self.name, text=text.strip(), confidence=_normalize_confidence(conf), task=task)


class EasyOCREngine(OCREngine):
    def __init__(self) -> None:
        super().__init__(name="easyocr", supports_typed=True, supports_handwriting=True)

    def predict(self, image: ImageArray, task: OCRTask) -> OCRPrediction:
        _set_default_cache_env()
        try:
            import easyocr
        except ImportError as exc:
            raise OCREngineError("easyocr is not installed.") from exc

        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        entries = reader.readtext(image)
        text = " ".join(entry[1] for entry in entries if len(entry) >= 2 and entry[1].strip())
        confs = [float(entry[2]) for entry in entries if len(entry) >= 3]
        conf = sum(confs) / len(confs) if confs else 0.5
        return OCRPrediction(engine=self.name, text=text.strip(), confidence=_normalize_confidence(conf), task=task)


class PaddleOCREngine(OCREngine):
    def __init__(self) -> None:
        super().__init__(name="paddleocr", supports_typed=True, supports_handwriting=False)

    def predict(self, image: ImageArray, task: OCRTask) -> OCRPrediction:
        _set_default_cache_env()
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise OCREngineError("paddleocr is not installed.") from exc

        # PaddleOCR has API differences across versions. Avoid non-portable kwargs
        # like `show_log` (some builds reject it as unknown).
        try:
            ocr = PaddleOCR(lang="en")
        except Exception as exc:
            raise OCREngineError(
                "PaddleOCR failed to initialize (often due to blocked model downloads or cache permissions). "
                "If running offline, pre-download models into the configured cache directory."
            ) from exc
        results = ocr.ocr(image, cls=True)
        lines = results[0] if results and results[0] else []
        text_parts: list[str] = []
        confs: list[float] = []
        for line in lines:
            if len(line) < 2:
                continue
            txt = str(line[1][0]).strip()
            if txt:
                text_parts.append(txt)
            confs.append(float(line[1][1]))
        conf = sum(confs) / len(confs) if confs else 0.5
        return OCRPrediction(
            engine=self.name,
            text=" ".join(text_parts).strip(),
            confidence=_normalize_confidence(conf),
            task=task,
        )


class TrOCREngine(OCREngine):
    def __init__(self) -> None:
        super().__init__(name="trocr", supports_typed=False, supports_handwriting=True)

    def predict(self, image: ImageArray, task: OCRTask) -> OCRPrediction:
        _set_default_cache_env()
        try:
            import torch
            from PIL import Image
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        except ImportError as exc:
            raise OCREngineError("transformers/torch/Pillow are not installed for TrOCR.") from exc

        model_name = os.environ.get("TROCR_MODEL_NAME", "microsoft/trocr-base-handwritten")
        try:
            processor = TrOCRProcessor.from_pretrained(model_name)
            model = VisionEncoderDecoderModel.from_pretrained(model_name)
        except Exception as exc:
            raise OCREngineError(
                "TrOCR model could not be loaded. This typically means the model download is blocked "
                "or you're offline without a cached model. Set TROCR_MODEL_NAME to a local path to a "
                "pre-downloaded model directory."
            ) from exc

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        pil = Image.fromarray(rgb)
        pixel_values = processor(images=pil, return_tensors="pt").pixel_values
        with torch.no_grad():
            generated_ids = model.generate(pixel_values)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
        return OCRPrediction(engine=self.name, text=text, confidence=0.75, task=task)


class DoctREngine(OCREngine):
    def __init__(self) -> None:
        super().__init__(name="doctr", supports_typed=True, supports_handwriting=False)

    def predict(self, image: ImageArray, task: OCRTask) -> OCRPrediction:
        _set_default_cache_env()
        try:
            from doctr.models import ocr_predictor
        except ImportError as exc:
            raise OCREngineError("python-doctr is not installed.") from exc

        try:
            predictor = ocr_predictor(pretrained=True)
        except Exception as exc:
            raise OCREngineError(
                "docTR pretrained models could not be loaded. This typically means the model download "
                "is blocked or you're offline without a cached model. Set DOCTR_CACHE_DIR to a writable "
                "path with pre-downloaded models."
            ) from exc
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        result = predictor([rgb])
        page = result.pages[0]
        text_parts: list[str] = []
        confs: list[float] = []
        for block in page.blocks:
            for line in block.lines:
                for word in line.words:
                    text_parts.append(word.value)
                    confs.append(float(word.confidence))
        conf = sum(confs) / len(confs) if confs else 0.5
        return OCRPrediction(
            engine=self.name,
            text=" ".join(text_parts).strip(),
            confidence=_normalize_confidence(conf),
            task=task,
        )


class CalamariEngine(OCREngine):
    def __init__(self) -> None:
        super().__init__(name="calamari", supports_typed=False, supports_handwriting=True)

    def predict(self, image: ImageArray, task: OCRTask) -> OCRPrediction:
        with tempfile.TemporaryDirectory(prefix="calamari_") as td:
            tmp = Path(td)
            input_img = tmp / "line.png"
            output_txt = tmp / "prediction.txt"
            cv2.imwrite(str(input_img), _ensure_grayscale(image))
            cmd = ["calamari-predict", "--files", str(input_img), "--checkpoint", "antiqua_modern"]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            except FileNotFoundError as exc:
                raise OCREngineError("calamari-predict command not found.") from exc
            if proc.returncode != 0:
                raise OCREngineError(f"Calamari failed: {proc.stderr.strip() or proc.stdout.strip()}")
            # Calamari writes `*.pred.txt` beside file by default.
            pred_file = input_img.with_suffix(".pred.txt")
            if not pred_file.exists():
                # Fallback: if custom config writes to another name.
                pred_file = output_txt if output_txt.exists() else pred_file
            text = pred_file.read_text(encoding="utf-8").strip() if pred_file.exists() else ""
        return OCRPrediction(engine=self.name, text=text, confidence=0.7, task=task)


class KrakenEngine(OCREngine):
    def __init__(self) -> None:
        super().__init__(name="kraken", supports_typed=False, supports_handwriting=True)

    def predict(self, image: ImageArray, task: OCRTask) -> OCRPrediction:
        with tempfile.TemporaryDirectory(prefix="kraken_") as td:
            tmp = Path(td)
            input_img = tmp / "line.png"
            output_txt = tmp / "prediction.txt"
            cv2.imwrite(str(input_img), _ensure_grayscale(image))
            cmd = ["kraken", "-i", str(input_img), str(output_txt), "ocr", "-m", "en_best.mlmodel"]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            except FileNotFoundError as exc:
                raise OCREngineError("kraken command not found.") from exc
            if proc.returncode != 0:
                raise OCREngineError(f"Kraken failed: {proc.stderr.strip() or proc.stdout.strip()}")
            text = output_txt.read_text(encoding="utf-8").strip() if output_txt.exists() else ""
        return OCRPrediction(engine=self.name, text=text, confidence=0.7, task=task)


def default_engines() -> dict[str, OCREngine]:
    return {
        "tesseract": TesseractEngine(),
        "easyocr": EasyOCREngine(),
        "paddleocr": PaddleOCREngine(),
        "trocr": TrOCREngine(),
        "doctr": DoctREngine(),
        "calamari": CalamariEngine(),
        "kraken": KrakenEngine(),
    }
