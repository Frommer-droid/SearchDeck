"""Единая политика происхождения DLL для основной сборки и frozen smoke."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import PySide6
import shiboken6

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QT_ROOT = Path(PySide6.__file__).resolve().parent
RUNTIME_NAMES = (
    "concrt140.dll", "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll",
    "msvcp140_codecvt_ids.dll", "vcruntime140.dll", "vcruntime140_1.dll",
)


def trusted_roots() -> tuple[Path, ...]:
    return tuple(Path(p).resolve() for p in (
        PROJECT_ROOT, sys.prefix, sys.base_prefix, os.environ["SystemRoot"],
    ))


def validate_origin(source: str, roots: tuple[Path, ...] | None = None) -> Path:
    path = Path(source).resolve(strict=True)
    if not any(path.is_relative_to(root) for root in (roots or trusted_roots())):
        raise RuntimeError(f"Untrusted native binary origin: {path}")
    return path


def build_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(str(path) for path in (
        QT_ROOT, Path(shiboken6.__file__).resolve().parent,
        Path(sys.prefix) / "Scripts", Path(sys.base_prefix),
        Path(sys.base_prefix) / "DLLs", Path(os.environ["SystemRoot"]) / "System32",
    ))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def qt_runtime_binaries() -> list[tuple[str, str]]:
    files = [QT_ROOT / name for name in RUNTIME_NAMES]
    for path in files:
        validate_origin(str(path))
    versions = {file_version(path) for path in files}
    if len(versions) != 1:
        raise RuntimeError(f"Qt MSVC runtime version mismatch: {versions}")
    return [(str(path), ".") for path in files]


def enforce_binary_policy(binaries: list) -> list:
    # Проверить все источники до замены доверенного Python runtime на Qt.
    for _destination, source, _kind in binaries:
        validate_origin(source)
    qt_runtime_binaries()
    result = []
    for destination, source, kind in binaries:
        name = Path(destination).name.lower()
        if name in RUNTIME_NAMES:
            source = str(QT_ROOT / name)
        result.append((destination, source, kind))
    destinations = {destination.lower() for destination, _source, _kind in result}
    for name in RUNTIME_NAMES:
        if name not in destinations:
            result.append((name, str(QT_ROOT / name), "BINARY"))
    return result


def file_version(path: Path) -> tuple[int, int, int, int]:
    import pefile

    with pefile.PE(str(path), fast_load=True) as image:
        image.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
        info = image.VS_FIXEDFILEINFO[0]
        return (info.FileVersionMS >> 16, info.FileVersionMS & 65535,
                info.FileVersionLS >> 16, info.FileVersionLS & 65535)
