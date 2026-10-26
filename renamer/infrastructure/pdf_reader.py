from __future__ import annotations

from pathlib import Path

import pymupdf as fitz


class PdfReader:
    def __init__(self, pdf_path: Path) -> None:
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)

    def __len__(self) -> int:
        return len(self.doc)

    def extract_text(self, page_index: int) -> str:
        return self.doc[page_index].get_text("text")

    def save_single_page(self, page_index: int, output_path: Path) -> None:
        single = fitz.open()
        try:
            single.insert_pdf(self.doc, from_page=page_index, to_page=page_index)
            single.save(output_path)
        finally:
            single.close()

    def close(self) -> None:
        self.doc.close()
