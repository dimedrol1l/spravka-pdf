from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import pymupdf as fitz

from renamer.application.pipeline import process_pdf
from renamer.domain.rules import extract_certificate_number


def make_text_pdf(path: Path) -> None:
    document = fitz.open()
    for text in ("No. 12345", "No. 12345", "No number on this page"):
        page = document.new_page()
        page.insert_text((72, 100), text)
    document.save(path)
    document.close()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CertificateNumberTests(unittest.TestCase):
    def test_extracts_number_from_marker(self):
        self.assertEqual(extract_certificate_number("No. 12345"), ("12345", 0.65))

    def test_rejects_all_zero_number(self):
        self.assertEqual(extract_certificate_number("No. 00000"), (None, 0.0))


class PdfPipelineTests(unittest.TestCase):
    def test_splits_pages_names_duplicates_and_flags_missing_number(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.pdf"
            output = root / "output"
            make_text_pdf(source)
            original_hash = sha256(source)

            results = process_pdf(
                source,
                output,
                use_ocr_fallback=False,
                dry_run=False,
            )

            self.assertEqual(
                [item.output_path.name for item in results],
                ["12345.pdf", "12345_2.pdf", "page_003_NO_NUMBER.pdf"],
            )
            self.assertEqual([item.certificate_number for item in results], ["12345", "12345", None])
            self.assertEqual([item.manual_review for item in results], [True, True, True])
            self.assertTrue(all(item.output_path.is_file() for item in results))
            self.assertEqual(sha256(source), original_hash)
            for result in results:
                with fitz.open(result.output_path) as page_document:
                    self.assertEqual(len(page_document), 1)

    def test_existing_output_is_preserved_and_new_name_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.pdf"
            output = root / "output"
            output.mkdir()
            make_text_pdf(source)
            existing = output / "12345.pdf"
            existing.write_bytes(b"keep this file")

            results = process_pdf(
                source,
                output,
                use_ocr_fallback=False,
                dry_run=False,
            )

            self.assertEqual(existing.read_bytes(), b"keep this file")
            self.assertEqual(
                [item.output_path.name for item in results],
                ["12345_2.pdf", "12345_3.pdf", "page_003_NO_NUMBER.pdf"],
            )

    def test_dry_run_does_not_create_output_directory_or_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.pdf"
            output = root / "not-created"
            make_text_pdf(source)

            results = process_pdf(
                source,
                output,
                use_ocr_fallback=False,
                dry_run=True,
            )

            self.assertEqual(len(results), 3)
            self.assertFalse(output.exists())
            self.assertTrue(all(not item.output_path.exists() for item in results))


if __name__ == "__main__":
    unittest.main()
