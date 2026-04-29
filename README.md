# Homework Grader (AI Final Project)

Desktop app to help grade weekly homework: **math-style numeric answers** (with OCR and PDF markup) and **written short answers**, with a GUI to pick PDFs, an answer key, and an output folder (e.g. for upload to Canvas). When the grader is unsure, it flags items for human review.

## Requirements

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or another PEP 517 installer


## Project setup (Linux and Windows)

From the repository root:

```bash
# Install the app + OCR-related Python packages (EasyOCR, docTR, etc.)
uv sync --extra ocr-ensemble

# Optional: include dev tools (pytest) to run the test suite
uv sync --extra ocr-ensemble --group dev
```

If you use a venv without `uv`, install the same extras your environment supports (e.g. `pip install -e ".[ocr-ensemble]"`).

## Run the application

```bash
uv run grader
```

(On Windows, run the same command from PowerShell or cmd in the project directory.)

## Run tests

```bash
uv run tests
```

The full suite expects the **`ocr-ensemble`** extra, because tests exercise OCR and PDF pipelines.

## Troubleshooting

- **First run is slow / large downloads**  
  OCR backends may download model weights on first use. The project can use a repo-local cache via `AI_FINAL_PROJECT_CACHE_DIR`; see `ai_final_project/ocr/engines.py` for related environment variables.

- **GPU / CUDA warnings**  
  OCR stacks may warn if CUDA is unavailable; CPU mode is normal for this project.

## `ai_final_project` package layout

The Python package under `ai_final_project/` is organized by responsibility: entrypoints and GUI at the top level, grading pipelines beside them, and OCR behind a small subpackage.

| Location | Purpose |
|----------|---------|
| `__init__.py` | Package metadata (`__version__`). |
| `__main__.py` | `python -m ai_final_project` delegates to `main.main()`. |
| `main.py` | Starts the Qt application and shows `MainWindow`. |
| `roster.py` | Reads student names from roster spreadsheets (`.xlsx` / `.ods`, first column). |
| `cv_boxes.py` | OpenCV + PyMuPDF helpers to find answer regions on rendered PDF pages (boxes, crops, PDF coordinate mapping). |
| `grading_extract.py` | Numeric-answer pipeline: answer-key parsing, submission crops, OCR-backed number extraction and scoring structs. |
| `written_response_grader.py` | Written answers: parse keyword rubrics from answer-key PDFs, extract submission text, score by keyword overlap, flag manual review. |
| `mixed_grading.py` | Combines math (numeric) and written grading for one submission; shared logic for the UI and tests. |
| `ocr/types.py` | Shared OCR datatypes (`OCRTask`, `OCRPrediction`, `OCRResult`). |
| `ocr/engines.py` | Pluggable OCR backends (EasyOCR, docTR, PaddleOCR, etc.) with lazy imports and env/cache hooks. |
| `ocr/ensemble.py` | Runs multiple engines per task, merges predictions, and surfaces confidence / review hints. |
| `ocr/__init__.py` | Public OCR API re-exports (`OCREnsemble`, `default_engines`, errors, types). |
| `ui/__init__.py` | UI subpackage marker. |
| `ui/main_window.py` | PySide6 main window: file picking, grading runs, progress, PDF markup export, and review workflow. |
