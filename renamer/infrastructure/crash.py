from __future__ import annotations

import sys
import traceback
from pathlib import Path


def crash_log_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "error.log"
    return Path.cwd() / "error.log"


def show_crash(exc: BaseException) -> None:
    text = traceback.format_exc()
    log = crash_log_path()
    try:
        log.write_text(text, encoding="utf-8")
    except OSError:
        pass
    message = f"{exc}\n\nПодробности: {log}"
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message[:1000], "Разделение PDF-справок", 0x10)
            return
        except Exception:
            pass
    print(text, file=sys.stderr)
