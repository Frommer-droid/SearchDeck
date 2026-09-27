from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Protocol

from app.models.browser import BrowserWindowMatch, LocateWindowResult


CTRL_F = "ctrl_f"
CTRL_L = "ctrl_l"
CTRL_V = "ctrl_v"
ALT_ENTER = "alt_enter"
ENTER = "enter"
ESCAPE = "escape"


class ClipboardProtocol(Protocol):
    def capture(self) -> object: ...

    def set_text(self, text: str) -> None: ...

    def restore(self, snapshot: object) -> None: ...


class KeyboardProtocol(Protocol):
    def send_shortcut(self, shortcut: str) -> None: ...

    def send_key(self, key_name: str) -> None: ...


class WindowLocatorProtocol(Protocol):
    def locate(self) -> LocateWindowResult: ...


class WindowActivatorProtocol(Protocol):
    def activate(self, hwnd: int) -> bool: ...


class DelayProtocol(Protocol):
    def wait(self, milliseconds: int) -> None: ...


@dataclass(slots=True, frozen=True)
class FindActionResult:
    success: bool
    message: str
    match: BrowserWindowMatch | None = None


class SleepDelay:
    def wait(self, milliseconds: int) -> None:
        time.sleep(milliseconds / 1000)


class FindActionService:
    """Оркестрирует сценарий поиска в браузере."""

    def __init__(
        self,
        locator: WindowLocatorProtocol,
        activator: WindowActivatorProtocol,
        clipboard: ClipboardProtocol,
        keyboard: KeyboardProtocol,
        delay: DelayProtocol | None = None,
    ) -> None:
        self._locator = locator
        self._activator = activator
        self._clipboard = clipboard
        self._keyboard = keyboard
        self._delay = delay or SleepDelay()
        self._browser_profile_path: str | None = None

    def set_browser_profile_path(self, profile_path: str) -> None:
        self._browser_profile_path = profile_path
        locator_setter = getattr(self._locator, "set_profile_path", None)
        if callable(locator_setter):
            locator_setter(profile_path)

    def execute(
        self,
        search_text: str,
        minimize_window: Callable[[], None],
        delay_ms: int = 250,
        post_paste_delay_ms: int = 500,
        duplicate_tab: bool = False,
    ) -> FindActionResult:
        locate_result = self._locator.locate()
        if not locate_result.success:
            return FindActionResult(False, locate_result.message or "Окно браузера не найдено.")

        if not self._activator.activate(locate_result.match.hwnd):
            return FindActionResult(False, "Не удалось активировать окно браузера.")

        snapshot = self._clipboard.capture()
        try:
            self._delay.wait(delay_ms)
            if duplicate_tab:
                self._keyboard.send_shortcut(CTRL_L)
                self._delay.wait(delay_ms)
                self._keyboard.send_shortcut(ALT_ENTER)
                self._delay.wait(delay_ms)
            self._keyboard.send_shortcut(CTRL_F)
            self._delay.wait(delay_ms)
            self._clipboard.set_text(search_text)
            self._keyboard.send_shortcut(CTRL_V)
            self._delay.wait(post_paste_delay_ms)
            self._keyboard.send_key(ENTER)
            self._delay.wait(delay_ms)
            self._keyboard.send_key(ESCAPE)
            self._delay.wait(delay_ms)
            minimize_window()
        except Exception as error:
            self._clipboard.restore(snapshot)
            return FindActionResult(False, f"Не удалось завершить поиск: {error}")

        self._clipboard.restore(snapshot)
        return FindActionResult(True, "Поиск выполнен.", locate_result.match)
