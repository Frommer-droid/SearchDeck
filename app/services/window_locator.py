from __future__ import annotations

import ctypes
import json
import locale
import subprocess
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

from app.models.browser import BrowserWindowMatch, LocateWindowResult, ProcessInfo, WindowInfo


EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

EnumWindows = ctypes.windll.user32.EnumWindows
IsWindowVisible = ctypes.windll.user32.IsWindowVisible
IsIconic = ctypes.windll.user32.IsIconic
GetWindowTextLengthW = ctypes.windll.user32.GetWindowTextLengthW
GetWindowTextW = ctypes.windll.user32.GetWindowTextW
GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
ShowWindow = ctypes.windll.user32.ShowWindow
SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
BringWindowToTop = ctypes.windll.user32.BringWindowToTop

SW_RESTORE = 9


@dataclass(slots=True, frozen=True)
class ProfileIdentity:
    directory_name: str
    markers: tuple[str, ...]


class Win32WindowEnumerator:
    """Возвращает top-level окна в текущем z-order."""

    def enumerate_windows(self) -> list[WindowInfo]:
        windows: list[WindowInfo] = []

        @EnumWindowsProc
        def _callback(hwnd: int, _: int) -> bool:
            visible = bool(IsWindowVisible(hwnd))
            title_length = GetWindowTextLengthW(hwnd)
            title_buffer = ctypes.create_unicode_buffer(title_length + 1)
            GetWindowTextW(hwnd, title_buffer, title_length + 1)
            process_id = wintypes.DWORD()
            GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            windows.append(
                WindowInfo(
                    hwnd=hwnd,
                    pid=process_id.value,
                    title=title_buffer.value,
                    visible=visible,
                )
            )
            return True

        EnumWindows(_callback, 0)
        return windows


class PowerShellProcessInfoProvider:
    """Читает имя процесса, путь и command line через CIM."""

    def get_processes(self, process_name: str) -> dict[int, ProcessInfo]:
        escaped_name = process_name.replace("'", "''")
        command = (
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            "$OutputEncoding = [Console]::OutputEncoding; "
            "Get-CimInstance Win32_Process "
            f"-Filter \"Name = '{escaped_name}'\" | "
            "Select-Object ProcessId, Name, ExecutablePath, CommandLine | "
            "ConvertTo-Json -Compress"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            **self._powershell_run_kwargs(),
        )
        raw_output = self._decode_output(completed.stdout).strip()
        if not raw_output:
            return {}
        try:
            payload = json.loads(raw_output)
        except json.JSONDecodeError:
            return {}

        items = payload if isinstance(payload, list) else [payload]
        results: dict[int, ProcessInfo] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            pid = int(item.get("ProcessId", 0))
            results[pid] = ProcessInfo(
                pid=pid,
                name=str(item.get("Name") or ""),
                executable_path=str(item.get("ExecutablePath") or ""),
                command_line=str(item.get("CommandLine") or ""),
            )
        return results

    @staticmethod
    def _powershell_run_kwargs() -> dict[str, object]:
        kwargs: dict[str, object] = {
            "check": False,
            "capture_output": True,
        }
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if creationflags:
            kwargs["creationflags"] = creationflags

        startupinfo_factory = getattr(subprocess, "STARTUPINFO", None)
        use_show_window = getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        hide_window = getattr(subprocess, "SW_HIDE", 0)
        if startupinfo_factory and use_show_window:
            startupinfo = startupinfo_factory()
            startupinfo.dwFlags |= use_show_window
            startupinfo.wShowWindow = hide_window
            kwargs["startupinfo"] = startupinfo
        return kwargs

    @staticmethod
    def _decode_output(raw_output: object) -> str:
        if raw_output is None:
            return ""
        if isinstance(raw_output, str):
            return raw_output
        if not isinstance(raw_output, bytes):
            return str(raw_output)

        encodings = PowerShellProcessInfoProvider._candidate_encodings()
        for encoding in encodings:
            try:
                return raw_output.decode(encoding)
            except UnicodeDecodeError:
                continue
        return ""

    @staticmethod
    def _candidate_encodings() -> tuple[str, ...]:
        encodings: list[str] = ["utf-8-sig", "utf-8", "cp866", "cp1251", "cp850"]
        preferred = locale.getpreferredencoding(False)
        if preferred:
            encodings.append(preferred)

        normalized: list[str] = []
        seen: set[str] = set()
        for encoding in encodings:
            folded = encoding.casefold()
            if folded in seen:
                continue
            seen.add(folded)
            normalized.append(encoding)
        return tuple(normalized)


class WindowActivator:
    """Активирует окно браузера."""

    def activate(self, hwnd: int) -> bool:
        if IsIconic(hwnd):
            ShowWindow(hwnd, SW_RESTORE)
        BringWindowToTop(hwnd)
        return bool(SetForegroundWindow(hwnd))


class LocalStateProfileInfoProvider:
    """Читает маркеры профиля из Local State браузера."""

    def get_profile_identity(self, profile_path: str) -> ProfileIdentity:
        profile_directory = Path(profile_path).name
        user_data_path = Path(profile_path).parent
        local_state_path = user_data_path / "Local State"
        markers: list[str] = [profile_directory]
        if not local_state_path.exists():
            return ProfileIdentity(profile_directory, tuple(self._normalize_markers(markers)))

        try:
            payload = json.loads(local_state_path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            return ProfileIdentity(profile_directory, tuple(self._normalize_markers(markers)))

        info_cache = (
            payload.get("profile", {})
            .get("info_cache", {})
        )
        profile_info = info_cache.get(profile_directory, {})
        if isinstance(profile_info, dict):
            markers.extend(self._extract_markers(profile_info))
        return ProfileIdentity(profile_directory, tuple(self._normalize_markers(markers)))

    @staticmethod
    def _extract_markers(profile_info: dict[str, object]) -> list[str]:
        candidates: list[str] = []
        for key in ("name", "shortcut_name", "gaia_name", "gaia_given_name", "user_name"):
            value = profile_info.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())

        signin_info = profile_info.get("profile_last_signin_info", {})
        if isinstance(signin_info, dict):
            for key in ("gaia_name", "gaia_given_name", "user_name"):
                value = signin_info.get(key)
                if isinstance(value, str) and value.strip():
                    candidates.append(value.strip())
        return candidates

    @staticmethod
    def _normalize_markers(markers: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for marker in markers:
            compact = marker.strip()
            folded = compact.casefold()
            if not compact or folded in seen:
                continue
            seen.add(folded)
            normalized.append(compact)
        return normalized


class BrowserWindowLocator:
    """Ищет окно браузера нужного профиля."""

    def __init__(
        self,
        process_name: str,
        profile_path: str,
        enumerator: Win32WindowEnumerator | None = None,
        process_provider: PowerShellProcessInfoProvider | None = None,
        profile_info_provider: LocalStateProfileInfoProvider | None = None,
    ) -> None:
        self._process_name = process_name.casefold()
        self._enumerator = enumerator or Win32WindowEnumerator()
        self._process_provider = process_provider or PowerShellProcessInfoProvider()
        self._profile_info_provider = profile_info_provider or LocalStateProfileInfoProvider()
        self._profile_path = ""
        self._profile_identity = ProfileIdentity("", tuple())
        self._profile_name = ""
        self.set_profile_path(profile_path)

    def set_profile_path(self, profile_path: str) -> None:
        self._profile_path = profile_path
        self._profile_identity = self._profile_info_provider.get_profile_identity(profile_path)
        self._profile_name = self._profile_identity.directory_name.casefold()

    def locate(self) -> LocateWindowResult:
        processes = self._process_provider.get_processes(self._process_name)
        if not processes:
            return LocateWindowResult(False, "Процесс браузера не найден.")

        matches: list[BrowserWindowMatch] = []
        saw_browser_window = False
        for window in self._enumerator.enumerate_windows():
            process = processes.get(window.pid)
            if process is None or not window.visible:
                continue
            if process.name.casefold() != self._process_name:
                continue
            saw_browser_window = True
            score = self._score_match(window.title, process)
            if score <= 0:
                continue
            matches.append(
                BrowserWindowMatch(
                    hwnd=window.hwnd,
                    pid=window.pid,
                    title=window.title,
                    score=score,
                )
            )

        if not matches and saw_browser_window:
            return LocateWindowResult(
                False,
                f"Окно процесса {self._process_name} найдено, но профиль {self._profile_name} не совпал.",
            )
        if not matches:
            return LocateWindowResult(False, "Не найдено видимое окно браузера.")

        best_match = max(matches, key=lambda item: item.score)
        return LocateWindowResult(True, "Окно браузера найдено.", best_match)

    def _score_match(self, title: str, process: ProcessInfo) -> int:
        title_haystack = title.casefold()
        for marker in self._profile_identity.markers:
            folded_marker = marker.casefold()
            if folded_marker and f"профиль {folded_marker}" in title_haystack:
                return 130
            if folded_marker and folded_marker in title_haystack:
                return 110

        process_haystack = " ".join(
            [
                process.command_line.casefold(),
                process.executable_path.casefold(),
            ]
        )
        full_profile = self._profile_path.casefold()
        markers = {
            full_profile: 100,
            self._profile_name: 50,
            f"--profile-directory={self._profile_name}": 75,
            f'--profile-directory="{self._profile_name}"': 75,
        }
        for marker, score in markers.items():
            if marker and marker in process_haystack:
                return score
        return 0
