#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ARCH="$(uname -m)"
RELEASE="$ROOT/releases/RazdelenieSpravok-macos-$ARCH.zip"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "Build this package on macOS."
    exit 1
fi
if [ -e "$RELEASE" ]; then
    echo "Refusing to overwrite existing release: $RELEASE"
    exit 1
fi
if ! command -v tesseract >/dev/null 2>&1; then
    echo "Tesseract is required for scanned PDFs. Install it before building."
    exit 1
fi
LANGUAGES="$(tesseract --list-langs 2>/dev/null)"
printf '%s\n' "$LANGUAGES" | grep -qx 'rus' || {
    echo "Tesseract Russian language data (rus) is required."
    exit 1
}
printf '%s\n' "$LANGUAGES" | grep -qx 'eng' || {
    echo "Tesseract English language data (eng) is required."
    exit 1
}

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || {
    echo "Python 3.11 or newer is required."
    exit 1
}
"$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' || {
    echo "Python 3.11 or newer is required."
    exit 1
}

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/spravki-macos-build.XXXXXX")"
cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

# Keep PyInstaller's cache inside this build's temporary workspace; --clean
# must not remove a cache belonging to another project or user environment.
export PYINSTALLER_CONFIG_DIR="$TMP_DIR/pyinstaller-config"

"$PYTHON" -m venv "$TMP_DIR/venv"
"$TMP_DIR/venv/bin/python" -m pip install \
    -r "$ROOT/requirements.txt" \
    -r "$ROOT/requirements-build.txt"
"$TMP_DIR/venv/bin/python" "$ROOT/packaging/self_test.py"
"$TMP_DIR/venv/bin/pyinstaller" \
    --noconfirm --clean --windowed \
    --name RazdelenieSpravok \
    --distpath "$TMP_DIR/dist" \
    --workpath "$TMP_DIR/work" \
    --specpath "$TMP_DIR/spec" \
    "$ROOT/app_gui.py"

mkdir -p "$ROOT/releases" "$TMP_DIR/package"
cp -R "$TMP_DIR/dist/RazdelenieSpravok.app" "$TMP_DIR/package/"
cp "$ROOT/HOW_TO_USE.txt" "$TMP_DIR/package/"
cp "$ROOT/LICENSE" "$TMP_DIR/package/"
ditto -c -k --sequesterRsrc --keepParent "$TMP_DIR/package" "$TMP_DIR/release.zip"
if [ -e "$RELEASE" ]; then
    echo "Refusing to overwrite existing release: $RELEASE"
    exit 1
fi
mv "$TMP_DIR/release.zip" "$RELEASE"
echo "Created: $RELEASE"
