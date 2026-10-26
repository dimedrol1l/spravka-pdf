from __future__ import annotations

from pathlib import Path
from typing import Callable

from renamer.domain.models import CertificateNumber, FileProcessResult, PageExtractionResult
from renamer.domain.rules import extract_certificate_number
from renamer.infrastructure.ocr import ocr_top_region_with_tesseract
from renamer.infrastructure.pdf_reader import PdfReader
from renamer.infrastructure.storage import (
    ensure_dir,
    make_unique_name,
    reserve_unique_path,
)


def process_pdf(
    input_pdf: Path,
    output_dir: Path,
    use_ocr_fallback: bool,
    dry_run: bool,
    number_digits: int | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[FileProcessResult]:
    reader = PdfReader(input_pdf)
    used_names: dict[str, int] = {}
    results: list[FileProcessResult] = []

    try:
        if not dry_run:
            ensure_dir(output_dir)
        for page_index in range(len(reader)):
            text = reader.extract_text(page_index)
            number, confidence = extract_certificate_number(text, digits=number_digits)
            source = "native_text"
            raw_text = text

            if not number and use_ocr_fallback:
                ocr_text = ocr_top_region_with_tesseract(input_pdf, page_index)
                ocr_number, ocr_conf = extract_certificate_number(
                    ocr_text, digits=number_digits
                )
                if ocr_number:
                    number = ocr_number
                    confidence = ocr_conf
                    source = "ocr_fallback"
                    raw_text = ocr_text

            extraction = PageExtractionResult(
                page_index=page_index,
                certificate_number=CertificateNumber(number) if number else None,
                confidence=confidence,
                source=source,
                raw_text=raw_text,
            )

            if extraction.certificate_number:
                stem = extraction.certificate_number.value
                manual_review = extraction.confidence < 0.75
            else:
                stem = f"page_{page_index + 1:03d}_NO_NUMBER"
                manual_review = True

            if dry_run:
                final_stem = make_unique_name(stem, used_names, output_dir)
                output_path = output_dir / f"{final_stem}.pdf"
            else:
                output_path = reserve_unique_path(stem, used_names, output_dir)
                try:
                    reader.save_single_page(page_index, output_path)
                except Exception:
                    output_path.unlink(missing_ok=True)
                    raise

            results.append(
                FileProcessResult(
                    page_index=page_index,
                    output_path=output_path,
                    certificate_number=number,
                    source=source,
                    confidence=confidence,
                    manual_review=manual_review,
                )
            )
            if progress_callback:
                progress_callback(page_index + 1, len(reader))
    finally:
        reader.close()

    return results
