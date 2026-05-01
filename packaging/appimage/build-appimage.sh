#!/usr/bin/env bash
# Build Homework-Grader-<version>-<arch>.AppImage (PyInstaller + appimagetool).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORK="${SCRIPT_DIR}/work"
APPDIR="${SCRIPT_DIR}/AppDir"
PY_DIST="${WORK}/pyinstaller-dist"
PY_WORK="${WORK}/pyinstaller-work"

machine="$(uname -m)"
case "${machine}" in
  x86_64) APPIMAGE_ARCH=x86_64 ;;
  aarch64) APPIMAGE_ARCH=aarch64 ;;
  *) echo "Unsupported architecture: ${machine}" >&2; exit 1 ;;
esac

cd "${REPO_ROOT}"
uv sync --extra ocr-ensemble --group appimage

rm -rf "${APPDIR}" "${WORK}"
mkdir -p "${WORK}" "${APPDIR}/usr/bin"

uv run pyinstaller \
  --workpath "${PY_WORK}" \
  --distpath "${PY_DIST}" \
  --noconfirm \
  "${SCRIPT_DIR}/grader.spec"

cp -a "${PY_DIST}/grader/." "${APPDIR}/usr/bin/"

if [[ ! -x "${APPDIR}/usr/bin/grader" ]]; then
  echo "PyInstaller did not produce ${APPDIR}/usr/bin/grader" >&2
  ls -la "${APPDIR}/usr/bin/" >&2 || true
  exit 1
fi

uv run python "${SCRIPT_DIR}/write_icon.py"
mkdir -p "${APPDIR}/usr/share/applications" "${APPDIR}/usr/share/icons/hicolor/256x256/apps"
install -m 644 "${SCRIPT_DIR}/homework-grader.png" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/homework-grader.png"
install -m 644 "${SCRIPT_DIR}/homework-grader.desktop" "${APPDIR}/usr/share/applications/homework-grader.desktop"
cp "${SCRIPT_DIR}/homework-grader.png" "${APPDIR}/homework-grader.png"
ln -sf homework-grader.png "${APPDIR}/.DirIcon"
install -m 644 "${SCRIPT_DIR}/homework-grader.desktop" "${APPDIR}/homework-grader.desktop"

cat > "${APPDIR}/AppRun" <<'EOF'
#!/bin/bash
SELF=$(readlink -f "${0}")
HERE=$(dirname "${SELF}")
export PATH="${HERE}/usr/bin:${PATH}"
export AI_FINAL_PROJECT_CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/homework-grader"
mkdir -p "${AI_FINAL_PROJECT_CACHE_DIR}" 2>/dev/null || true
exec "${HERE}/usr/bin/grader" "$@"
EOF
chmod +x "${APPDIR}/AppRun"

APPIMAGETOOL="${WORK}/appimagetool-${APPIMAGE_ARCH}.AppImage"
if [[ ! -f "${APPIMAGETOOL}" ]]; then
  # `continuous` tracks the maintained appimagetool builds (incl. aarch64).
  curl -fsSL -o "${APPIMAGETOOL}" \
    "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${APPIMAGE_ARCH}.AppImage"
  chmod +x "${APPIMAGETOOL}"
fi

VERSION="$(uv run python -c "import importlib.metadata as m; print(m.version('ai-final-project'))")"
OUT="${SCRIPT_DIR}/Homework-Grader-${VERSION}-${APPIMAGE_ARCH}.AppImage"
rm -f "${OUT}"
ARCH="${APPIMAGE_ARCH}" "${APPIMAGETOOL}" "${APPDIR}" "${OUT}"

echo "Built: ${OUT}"
