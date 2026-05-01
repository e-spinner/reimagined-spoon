# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for bundling the Homework Grader GUI + OCR stack (Linux AppImage)."""

from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata

_spec_dir = Path(SPECPATH)
repo_root = _spec_dir.parent.parent
entry = _spec_dir / "entry.py"

datas: list = []
binaries: list = []
hiddenimports: list = []

# Packages with data files or lazy imports that PyInstaller often misses.
_collect_names = (
    "PySide6",
    "shiboken6",
    "cv2",
    "numpy",
    "pymupdf",
    "PIL",
    "torch",
    "torchvision",
    "transformers",
    "easyocr",
    "paddleocr",
    "paddle",
    "paddlex",
    "doctr",
    "sklearn",
    "scipy",
    "sympy",
    "pypdf",
    "openpyxl",
    "odf",
)

for name in _collect_names:
    try:
        d, b, h = collect_all(name)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

for pkg in (
    "torch",
    "transformers",
    "easyocr",
    "paddleocr",
    "python-doctr",
    "pymupdf",
    "pyside6",
):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

a = Analysis(
    [str(entry)],
    pathex=[str(repo_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="grader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_tracker=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="grader",
)
