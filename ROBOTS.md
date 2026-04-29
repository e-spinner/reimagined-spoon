# ROBOT README

This document explains how the entire `reimagined-spoon` project currently works, including code structure, runtime flow, UI behavior, file parsing, and known limitations.

## 1) Project Purpose

The project is a local desktop app for grading homework submissions with:
- Math-focused and written-response workflows
- A GUI-first experience (no required terminal use for end users once packaged)
- PDF-centric document handling
- Review signaling for low-confidence outputs

The current implementation is a functional UI scaffold with several real input/parsing pieces and several grading/export pieces still stubbed.

## 2) Tech Stack

- Language: Python 3.14+
- UI framework: PySide6
- Spreadsheet parsing:
  - `openpyxl` for `.xlsx`/`.xlsm`
  - `odfpy` for `.ods`
- PDF parsing (currently used by code but not declared in `pyproject.toml`):
  - `pypdf` (optional runtime dependency for answer-key parsing)
- Computer vision / OCR:
  - `opencv-python` + `pymupdf` for PDF page rendering and answer-box detection
  - Ensemble wrappers for `tesseract`, `easyocr`, `paddleocr`, `trocr` (`transformers`/`torch`), and `docTR`

## 3) High-Level Structure

- `main.py`
  - Tiny repo-root launcher that calls package main and exits with its return code.
- `ai_final_project/__main__.py`
  - Package entrypoint wrapper around `ai_final_project.main:main`.
- `ai_final_project/main.py`
  - Creates `QApplication`, applies base font sizing, creates/shows `MainWindow`, enters event loop.
- `ai_final_project/ui/main_window.py`
  - Core application: theme system, all widgets/layouts, actions, handlers, parsing helpers.
- `ai_final_project/roster.py`
  - Roster file parsing and normalization for Excel/Calc files.
- `ai_final_project/grading_extract.py`
  - Math-mode extraction pipeline for:
    - bottom-right marker verification
    - answer-box crop OCR
    - numeric answer extraction from submission and answer-key PDFs
    - answer-key scoring parse (`expected_answer`, `max_points`, `wrong_points`)

## 4) App Startup Flow

1. User launches `main.py` (or installed `grader` script).
2. `ai_final_project.main.main()` creates `QApplication`.
3. App metadata is set:
   - Application name: `Homework Grader`
   - Organization name: `AI Final Project`
4. `MainWindow` is instantiated and shown.
5. Qt event loop begins with `app.exec()`.

## 5) Main Window Layout and UX Model

`MainWindow` uses a three-column dashboard design:

- Left sidebar:
  - Icon-only nav/actions
  - Menu button exposing common actions (`Set answer key`, `Export`, `Import roster`, `Run grading`, `Theme`, `Quit`)
- Center workspace:
  - Header with title and submissions search
  - Submissions list + graded outputs list + preview pane
  - Low-confidence review banner
- Right command column:
  - Roster controls
  - Selected-file display
  - Progress and status text
  - Main action buttons (answer key, export, run grading)

This UI is intentionally designed to remain usable for non-technical users.

## 6) Theme and Appearance System

The theme system in `main_window.py` includes:
- Fixed dark neutrals for global background/surfaces
- Accent palettes for interaction surfaces (buttons, borders, selection, etc.)
- Preset accent colors + custom color picker
- Persistence using `QSettings`

Theme flow:
1. Load saved accent (`theme/accent_preset` and optional `theme/accent_custom`)
2. Build stylesheet via `build_app_stylesheet(...)`
3. Apply stylesheet to the window
4. Save updates immediately when user changes accent

## 7) Grading Modes

There are three mutually exclusive mode buttons:
- Math grading
- Written grading
- Mixed (per question)

Mixed mode behavior:
- Shows a dedicated per-question section
- Seeds placeholder rows once with demo questions
- Each row includes:
  - Question label
  - Current type label (`Math` or `Written`)
  - Three-line menu (`☰`) that switches label between `Math` and `Written`

Important: mixed mode selection is currently UI-only and not connected to grading logic yet.

Current run behavior by mode:
- Math mode:
  - `Run grading` now executes a real local path for each submission PDF:
    1. Parse expected numeric answer from the selected answer-key PDF.
    2. Parse scoring values from answer key (`max_points`, `wrong_points`).
    2. Detect/check filled bottom-right marker box.
    3. Crop the associated answer box.
    4. OCR the crop (stability-first engine path).
    5. Compare extracted numeric value to answer-key value.
    6. Award points + compute percentage.
    7. Annotate graded PDF with check/X marker and top summary (`awarded/max (percent)`).
    8. Export grades spreadsheet (grade text in column B).
  - Graded list entries include extracted value, expected value, and pass/fail marker.
- Written mode:
  - Still stubbed (placeholder output generation).
- Mixed mode:
  - Still stubbed (placeholder output generation; per-question mapping UI remains non-binding).

## 8) Student Submission Input and Parsing

When user clicks **Load submissions folder**:

1. A folder picker opens.
2. Code calls `parse_submissions_folder(folder)`.
3. Files are split into:
   - Supported submissions (`.pdf` only, defined by `SUPPORTED_SUBMISSION_SUFFIXES`)
   - Unsupported files (all other extensions)
4. If unsupported files exist, app writes a local manifest:
   - `<selected_folder>/unsupported_files_for_review.txt`
5. Submissions list is populated with supported PDF names.
6. Status text reports number of PDFs and unsupported-file summary.

This matches the requirement that unsupported document types should be surfaced for professor review.

## 9) Answer Key Input and Parsing

When user clicks **Answer key (PDF)**:

1. A file picker opens for PDF.
2. Code calls `parse_answer_key_pdf(pdf_path)`.
3. Parsing steps:
   - Extract text from pages using `pypdf.PdfReader` (`_extract_pdf_text_local`)
   - Heuristically count question markers (`Question 1`, `Q2`, etc.)
   - Heuristically sum point patterns (`10 points`, `5 pts`, etc.)
   - Count pages
4. Parsed summary is stored in `self._answer_key_info` and shown in status text.
5. If parsing fails, app shows a warning dialog and leaves answer key unset.

Important implementation detail:
- If `pypdf` is not installed, parsing raises a runtime error with install guidance.

## 10) Roster Import Pipeline

Roster flow uses `read_student_names(path)` in `roster.py`:

- Supported input:
  - `.xlsx`, `.xlsm` via `openpyxl`
  - `.ods` via `odfpy`
- Explicit rejection:
  - `.xls` (legacy format)

Normalization behavior:
- Read first worksheet, first column only
- Trim whitespace, drop empty values
- Remove likely header row heuristically (e.g., `Name`, `Student Name`)
- Deduplicate exact matches while preserving original order

UI then compares imported count to expected count (`QSpinBox`) and shows mismatch guidance.

## 11) Search, Status, and Review UX

- Submission search filters list items in place (case-insensitive).
- Low-confidence banner visibility depends on:
  - `self._low_confidence_count > 0`
  - Alert toggle checkbox enabled
- Status label is used as primary live feedback channel for operation outcomes.

## 12) What Is Stubbed vs Implemented

### Implemented
- Full PySide6 desktop UI shell
- Theme presets + custom accent persistence
- Mode toggles with mixed-mode per-question menu UI
- Submissions folder parsing + unsupported-file manifest generation
- Answer key PDF ingestion + heuristic parsing
- Roster spreadsheet import and normalization
- CV answer-region detection pipeline:
  - detects filled lower-right marker box
  - locates matching bottom-right answer box
  - exports debug overlay/crops for human review
- Modular OCR ensemble scaffolding:
  - task-aware profiles (`typed`, `handwriting`, `mixed`)
  - pluggable engine adapters with per-engine confidence output
  - low-confidence/manual-review flagging in aggregation result
- Math-mode grading integration (partial):
  - `Run grading` now calls real CV+OCR numeric extraction in Math mode
  - compares extracted numeric answer against answer-key numeric answer
  - updates review counts and status from real extraction outcomes
  - annotates graded PDFs (check/X + top score summary)
  - writes spreadsheet grades to second column
- Numeric extraction service:
  - robust parsing for OCR-formatted decimals (`3,45`, `3 . 45`, `3 45`)
  - strict answer-key parsing preference for explicit `Answer: <value>` lines
- Answer-key scoring parse:
  - extracts `max_points` from `N pts/points`
  - extracts `wrong_points` from `Wrong answer = Npts` patterns

### Stub / Placeholder
- Written/Mixed grading logic still stubbed
- Student handwriting model training
- Rubric-wide scoring logic and confidence policy beyond numeric answer checks
- Real PDF annotation (checkmarks/x marks/point overlays)
- Spreadsheet export implementation
- Canvas-ready final output pipeline

## 13) OCR Runtime Status (Current)

Option A is currently in use: continue without Kraken/Calamari and run the available local engines.

Validated as running in this project environment:
- `tesseract` (CLI installed) + `pytesseract` wrapper
- `easyocr`
- `trocr` (`transformers` + `torch`) after model cache/network setup
- `docTR` after model download into project cache

Installed but currently unavailable in the active Python runtime:
- `paddleocr` wrapper package is installed, but backend `paddlepaddle` cannot be installed on Python 3.14 due to missing `cp314` wheels.
  - Current practical resolution is to keep PaddleOCR disabled in this runtime, or run PaddleOCR in a separate Python 3.13 environment.

Deferred for now:
- `kraken`
- `calamari`

Caching behavior:
- OCR/model caches are configured to write under project-local cache paths to avoid home-directory permission issues during sandboxed/dev runs.

## 14) Dependency Notes

Declared in `pyproject.toml`:
- `pyside6`
- `openpyxl`
- `odfpy`
- `pypdf`
- `opencv-python`
- `pymupdf`

Optional OCR extras are declared for the active ensemble subset:
- `pytesseract`
- `easyocr`
- `paddleocr`
- `transformers`
- `torch`
- `pillow`
- `python-doctr`

Known compatibility note:
- `paddlepaddle` wheels are not currently available for Python 3.14 (`cp314`) in this setup, which blocks PaddleOCR runtime use on this interpreter.

## 15) Test Fixtures and Verification Artifacts

To keep tests deterministic even if reference files change, fixture copies are stored in:
- `Unit Tests/fixtures/`
  - `MichaelSmithHW1.pdf`
  - `Example Answer key.pdf`
  - `Example Name sheet.ods`

Annotation and spreadsheet tests write manual-review artifacts to:
- `Unit Tests/output/math_artifacts/`
  - `graded_sample_correct.pdf`
  - `graded_sample_wrong.pdf`
  - `grades_output.xlsx`
  - matching `*.summary.txt` files with expected score text

These files are intended for human verification of PDF annotation and spreadsheet export output.

## 16) Current Execution/Packaging Model

Available entrypoints:
- Module/package path:
  - `python -m ai_final_project`
- Script entry point (after install):
  - `grader`
- Repo root launcher:
  - `python main.py`

Packaging for non-command-line end users is not fully configured yet (no final executable bundling config in this repository at this time).

## 17) Suggested Next Milestones

1. Add runtime capability reporting so the app shows which OCR engines are available on startup (with reasons for disabled engines).
2. Extend real extraction path from Math mode into Written and Mixed flows.
3. Connect mixed-mode per-question settings to grading/OCR task selection.
4. Implement full rubric scoring + low-confidence review queue from OCR outputs.
5. Implement graded PDF rendering (marks, points, percentage placement) and spreadsheet export.
6. Add executable packaging workflow with first-run model cache/bootstrap checks.

---

If you want, the next version of this document can be split into:
- `ARCHITECTURE.md` (system design),
- `USER_GUIDE.md` (how to use UI),
- `DEVELOPER_GUIDE.md` (how to run/extend/test).
