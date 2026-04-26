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

### Stub / Placeholder
- Actual OCR pipeline (math/written recognition)
- Student handwriting model training
- Real grading logic and confidence scoring
- Real PDF annotation (checkmarks/x marks/point overlays)
- Spreadsheet export implementation
- Canvas-ready final output pipeline

## 13) Dependency Notes

Declared in `pyproject.toml`:
- `pyside6`
- `openpyxl`
- `odfpy`

Used by code but currently missing from declared dependencies:
- `pypdf`

Recommended update:
- Add `pypdf` to `pyproject.toml` dependencies so answer-key parsing works in clean environments.

## 14) Current Execution/Packaging Model

Available entrypoints:
- Module/package path:
  - `python -m ai_final_project`
- Script entry point (after install):
  - `grader`
- Repo root launcher:
  - `python main.py`

Packaging for non-command-line end users is not fully configured yet (no final executable bundling config in this repository at this time).

## 15) Suggested Next Milestones

1. Add `pypdf` to declared dependencies.
2. Introduce a parser service layer (move parsing helpers out of UI module).
3. Add typed models for rubric/questions and parsed submission documents.
4. Implement local OCR stack (no paid APIs) with confidence outputs.
5. Connect mixed-mode per-question settings to grading route selection.
6. Implement graded PDF rendering and spreadsheet export.
7. Add unit tests for roster parsing, answer-key parsing heuristics, and submission-folder classification.

---

If you want, the next version of this document can be split into:
- `ARCHITECTURE.md` (system design),
- `USER_GUIDE.md` (how to use UI),
- `DEVELOPER_GUIDE.md` (how to run/extend/test).
