from __future__ import annotations

from pathlib import Path


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def make_unique_name(
    stem: str, used: dict[str, int], output_dir: Path | None = None
) -> str:
    """Choose a name that is unused in this run and, when supplied, on disk."""
    index = used.get(stem, 0)
    while True:
        index += 1
        candidate = stem if index == 1 else f"{stem}_{index}"
        exists_on_disk = output_dir is not None and (output_dir / f"{candidate}.pdf").exists()
        if not exists_on_disk:
            used[stem] = index
            return candidate


def reserve_unique_path(stem: str, used: dict[str, int], output_dir: Path) -> Path:
    """Atomically reserve a free output path so an existing PDF is never replaced."""
    index = used.get(stem, 0)
    while True:
        index += 1
        candidate = stem if index == 1 else f"{stem}_{index}"
        output_path = output_dir / f"{candidate}.pdf"
        try:
            with output_path.open("xb"):
                pass
        except FileExistsError:
            continue
        used[stem] = index
        return output_path
