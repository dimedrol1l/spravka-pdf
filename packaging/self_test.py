from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from renamer.application.pipeline import process_pdf
from renamer.infrastructure.ocr import _bundled_tesseract_path


EXPECTED = ["12345", "67890"]


def create_sample(path: Path) -> None:
    document = fitz.open()
    for number in EXPECTED:
        canvas = fitz.open()
        page = canvas.new_page()
        # Keep this synthetic OCR sample free of real certificate data and
        # embed it as an image so the native PDF text layer stays empty.
        page.insert_text((330, 105), f"No. {number}", fontsize=22)
        image = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
        canvas.close()
        image_page = document.new_page()
        image_page.insert_image(image_page.rect, stream=image)
    document.save(path)
    document.close()


def main() -> int:
    tesseract = _bundled_tesseract_path()
    print(f"OCR: {'available' if tesseract else 'not found'}", flush=True)
    if tesseract is None:
        print("SELF TEST FAILED: Tesseract not found", flush=True)
        return 1

    with tempfile.TemporaryDirectory(prefix="spravki-self-test-") as directory:
        root = Path(directory)
        sample = root / "synthetic.pdf"
        output = root / "output"
        create_sample(sample)
        results = process_pdf(
            input_pdf=sample,
            output_dir=output,
            use_ocr_fallback=True,
            dry_run=False,
            number_digits=None,
            progress_callback=lambda current, total: print(
                f"  page {current}/{total}", flush=True
            ),
        )
        actual = [item.certificate_number for item in results]
        print(f"Expected: {EXPECTED}", flush=True)
        print(f"Actual:   {actual}", flush=True)
        if actual != EXPECTED:
            print("SELF TEST FAILED: OCR result mismatch", flush=True)
            return 1
        if any(not item.output_path.is_file() for item in results):
            print("SELF TEST FAILED: output PDF missing", flush=True)
            return 1
        if any(item.source != "ocr_fallback" for item in results):
            print("SELF TEST FAILED: OCR fallback was not used", flush=True)
            return 1
        print("SELF TEST PASSED", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
