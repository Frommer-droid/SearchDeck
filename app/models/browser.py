from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class WindowInfo:
    hwnd: int
    pid: int
    title: str
    visible: bool


@dataclass(slots=True, frozen=True)
class ProcessInfo:
    pid: int
    name: str
    executable_path: str
    command_line: str


@dataclass(slots=True, frozen=True)
class BrowserWindowMatch:
    hwnd: int
    pid: int
    title: str
    score: int


@dataclass(slots=True, frozen=True)
class LocateWindowResult:
    success: bool
    message: str
    match: BrowserWindowMatch | None = None
