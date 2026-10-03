"""Определение версии приложения из единого источника VERSION."""

from __future__ import annotations

import sys
from pathlib import Path


def _read_version() -> str:
    if getattr(sys, "frozen", False):
        try:
            version_file = Path(sys._MEIPASS) / "VERSION"  # type: ignore[attr-defined]
            if version_file.exists():
                return version_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
        return "0.0.0"

    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    if version_file.exists():
        value = version_file.read_text(encoding="utf-8").strip()
        if value:
            return value
    return "0.0.0"


__version__ = _read_version()
