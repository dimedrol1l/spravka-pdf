from __future__ import annotations

import re

LICENSE_NOISE = re.compile(r"(Л[0-9]{3}|A[0-9]{3}|[0-9]{2}/[0-9]{2}/[0-9]{2})")
NUMBER_MARKER = r"(?:№|N[°ºoо0eеЕg2]|No\.?|#)"


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\u00a0", " ").split())


def _cert_patterns(digits: int) -> list[re.Pattern[str]]:
    n = str(digits)
    return [
        re.compile(
            rf"(?:СПРАВКА|CПPABKA|CПРАВКА|СПPABKA)\s*{NUMBER_MARKER}\s*(?<![0-9])([0-9]{{{n}}})(?![0-9])",
            re.IGNORECASE,
        ),
        re.compile(
            rf"(?:СПРАВКА|CПPABKA|CПРАВКА|СПPABKA)\s*[\r\n ]+\s*{NUMBER_MARKER}\s*(?<![0-9])([0-9]{{{n}}})(?![0-9])",
            re.IGNORECASE,
        ),
        re.compile(
            rf"(?:СПРАВКА|CПPABKA|CПРАВКА|СПPABKA)\s+(?<![0-9])([0-9]{{{n}}})(?![0-9])",
            re.IGNORECASE,
        ),
    ]


def _marker_pattern(digits: int) -> re.Pattern[str]:
    n = str(digits)
    # OCR may distort the word СПРАВКА while preserving №/Ne and the number.
    # One-digit address markers such as "дом № 4" are intentionally excluded.
    return re.compile(
        rf"{NUMBER_MARKER}\s*(?<![0-9])([0-9]{{{n}}})(?![0-9])",
        re.IGNORECASE,
    )


def is_valid_certificate_number(value: str, digits: int = 5) -> bool:
    return bool(re.fullmatch(rf"[0-9]{{{digits}}}", value)) and set(value) != {"0"}


def _extract_for_digits(text: str, digits: int) -> tuple[str | None, float]:
    for i, pattern in enumerate(_cert_patterns(digits)):
        m = pattern.search(text)
        if not m:
            continue
        candidate = m.group(1)
        if is_valid_certificate_number(candidate, digits):
            return candidate, max(0.9 - i * 0.1, 0.7)
    return None, 0.0


def _extract_by_marker(text: str, digits: int) -> tuple[str | None, float]:
    match = _marker_pattern(digits).search(text)
    if not match:
        return None, 0.0
    candidate = match.group(1)
    if is_valid_certificate_number(candidate, digits):
        return candidate, 0.65
    return None, 0.0


def extract_certificate_number(
    text: str, digits: int | None = None
) -> tuple[str | None, float]:
    if not text.strip():
        return None, 0.0

    compact = normalize_text(text)
    if LICENSE_NOISE.search(compact[:220]):
        # still continue; this is just a weak hint
        pass

    if digits is not None:
        number, confidence = _extract_for_digits(compact, digits)
        if number:
            return number, confidence
        return _extract_by_marker(compact, digits)

    # Longer numbers first so 12345 is not taken as 123.
    for length in (6, 5, 4, 3, 2):
        number, confidence = _extract_for_digits(compact, length)
        if number:
            return number, confidence
    # Only after all context-aware patterns failed, tolerate a damaged word
    # СПРАВКА and rely on the number marker.
    for length in (6, 5, 4, 3, 2):
        number, confidence = _extract_by_marker(compact, length)
        if number:
            return number, confidence
    return None, 0.0
