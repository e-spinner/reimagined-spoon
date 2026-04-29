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
