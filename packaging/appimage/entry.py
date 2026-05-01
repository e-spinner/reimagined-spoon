"""PyInstaller entry: run the Qt app (same as the installed `grader` console script)."""

from __future__ import annotations

from ai_final_project.main import main

if __name__ == "__main__":
    raise SystemExit(main())
