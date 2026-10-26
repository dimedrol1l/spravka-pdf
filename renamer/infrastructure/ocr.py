from __future__ import annotations

import io
import os
import platform
import shutil
from pathlib import Path

import pymupdf as fitz

from renamer.infrastructure.paths import app_dir, bundle_dir


def _tesseract_candidates() -> list[Path]:
    is_windows = platform.system() == "Windows"
    names = ("tesseract.exe",) if is_windows else ("tesseract",)
    dirs = []
    configured_dir = os.environ.get("TESSERACT_HOME")
    if configured_dir:
        dirs.append(Path(configured_dir))
    if is_windows:
        dirs.extend(
            [
                bundle_dir() / "tesseract",
                app_dir() / "tesseract",
                Path(__file__).resolve().parents[2] / "vendor" / "tesseract",
                Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
                / "Tesseract-OCR",
                Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
                / "Tesseract-OCR",
            ]
        )
    else:
        dirs.extend(
            [
                Path("/opt/homebrew/bin"),
                Path("/usr/local/bin"),
            ]
        )
    found: list[Path] = []
    seen: set[str] = set()
    for folder in dirs:
        for name in names:
            candidate = folder / name
            key = str(candidate).lower()
            if candidate.exists() and key not in seen:
                seen.add(key)
                found.append(candidate)
    which = shutil.which("tesseract")
    if which:
        path = Path(which)
        key = str(path).lower()
        if key not in seen:
            found.append(path)
    return found


def _bundled_tesseract_path() -> Path | None:
    candidates = _tesseract_candidates()
    return candidates[0] if candidates else None


def is_tesseract_available() -> bool:
    return _bundled_tesseract_path() is not None


def _configure_tesseract_cmd(pytesseract_module) -> None:
    bundled = _bundled_tesseract_path()
    if bundled is None:
        return
    pytesseract_module.pytesseract.tesseract_cmd = str(bundled)
    tessdata = bundled.parent / "tessdata"
    if tessdata.exists():
        # Tesseract 5 expects the directory containing *.traineddata itself.
        # Pointing to its parent makes the languages appear as tessdata/rus,
        # so requesting lang="rus+eng" fails on Windows.
        os.environ["TESSDATA_PREFIX"] = str(tessdata)


def install_ocr_windows(status=None) -> str:
    existing = _bundled_tesseract_path()
    if existing is not None:
        if status:
            status("OCR уже внутри программы")
        return f"OCR уже готов: {existing}"
    raise RuntimeError(
        "OCR не найден в папке программы. "
        "Пересоберите через build.bat (нужна папка vendor\\tesseract)."
    )


def ocr_top_region_with_tesseract(
    pdf_path: Path, page_index: int, *, raise_on_error: bool = False
) -> str:
    try:
        import pytesseract
        from PIL import Image, ImageOps
    except Exception:
        if raise_on_error:
            raise
        return ""
    _configure_tesseract_cmd(pytesseract)

    doc = fitz.open(pdf_path)
    try:
        page = doc[page_index]
        rect = page.rect
        clip = fitz.Rect(rect.width * 0.35, 0, rect.width, rect.height * 0.45)
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=clip, alpha=False)
    finally:
        doc.close()

    img = Image.open(io.BytesIO(pix.tobytes("png")))
    img = ImageOps.grayscale(img)
    try:
        return pytesseract.image_to_string(img, lang="rus+eng", config="--oem 3 --psm 6")
    except Exception:
        if raise_on_error:
            raise
        return ""
