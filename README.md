# Homework Grader (AI Final Project)

Desktop app to help grade weekly homework: **math-style numeric answers** (with OCR and PDF markup) and **written short answers**, with a GUI to pick PDFs, an answer key, and an output folder (e.g. for upload to Canvas). When the grader is unsure, it flags items for human review.

## How the program works (high level)

At a high level, the app follows a repeatable grading pipeline:

1. You select class inputs in the GUI: roster, answer key PDF, student submission PDFs, and output folder.
2. The app loads rubric information from the answer key and prepares per-student grading tasks.
3. For numeric problems, it detects answer regions in each PDF page, runs OCR (optionally with multiple engines), and compares extracted values against the key.
4. For written responses, it extracts text, checks rubric keywords/criteria, and produces a rubric-aligned score.
5. It combines numeric and written scores into one result per student, including confidence/review hints.
6. It exports marked-up outputs and grading artifacts for instructor review and LMS upload.

When confidence is low or extraction is ambiguous, the app explicitly flags items for manual verification instead of silently auto-grading.

## Input format requirements

- Math grading currently works only with the engineering-paper submission format described in `Reference Material/ ENGINEERING PAPER.pdf`.
- Student submissions for numeric grading should follow the layout specified in `Reference Material/ ENGINEERING PAPER.pdf` so answer regions can be detected correctly.
- Answer keys should also be formatted according to `Reference Materials/Math Answer Key.pdf` or `Reference Materials/Writing Answer Key.pdf` so parsing and scoring behave as expected.

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

## Build for Windows or macOS (PyInstaller)

Windows and macOS users should build a native executable for their own operating system using PyInstaller.

Important notes:

- Build on the same OS you are targeting (build on Windows for Windows, build on macOS for macOS).
- Use a clean virtual environment and install the OCR extras so bundled grading features are available.
- The repo already includes a PyInstaller spec at `packaging/appimage/grader.spec` that collects required dependencies.

### 1) Install dependencies (from repo root)

```bash
uv sync --extra ocr-ensemble --group appimage
```

### 2) Build with PyInstaller

```bash
uv run pyinstaller --noconfirm packaging/appimage/grader.spec
```

### 3) Locate build output

- Main bundled folder: `dist/grader/`
- Executable inside that folder:
  - Windows: `dist/grader/grader.exe`
  - macOS: `dist/grader/grader`

### 4) Run the built app

- On Windows, double-click `grader.exe` (or run it from PowerShell).
- On macOS, run `dist/grader/grader` from Terminal. If Gatekeeper blocks first launch, open System Settings -> Privacy & Security and allow it, then run again.

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

## AI use acknowledgment and citation

This entire app was programmed using Cursor with agentic AI assistance.

Citation:

- Cursor IDE with agentic AI models (including OpenAI GPT, Anthropic Claude, and Google Gemini model families). Assistance used across application development and documentation, 2026.
