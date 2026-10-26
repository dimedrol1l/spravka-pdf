from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CertificateNumber:
    value: str


@dataclass(frozen=True)
class PageExtractionResult:
    page_index: int
    certificate_number: CertificateNumber | None
    confidence: float
    source: str
    raw_text: str


@dataclass(frozen=True)
class FileProcessResult:
    page_index: int
    output_path: Path
    certificate_number: str | None
    source: str
    confidence: float
    manual_review: bool
