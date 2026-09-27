from __future__ import annotations

from app.core.find_action_service import (
    ALT_ENTER,
    CTRL_F,
    CTRL_L,
    CTRL_V,
    ENTER,
    ESCAPE,
    FindActionService,
)
from app.models.browser import BrowserWindowMatch, LocateWindowResult


class FakeLocator:
    def __init__(self, result: LocateWindowResult) -> None:
        self.result = result
        self.profile_paths: list[str] = []

    def locate(self) -> LocateWindowResult:
        return self.result

    def set_profile_path(self, profile_path: str) -> None:
        self.profile_paths.append(profile_path)


class FakeActivator:
    def __init__(self, success: bool = True) -> None:
        self.success = success
        self.calls: list[int] = []

    def activate(self, hwnd: int) -> bool:
        self.calls.append(hwnd)
        return self.success


class FakeClipboard:
    def __init__(self) -> None:
        self.state = {"text/plain": b"old"}
        self.events: list[tuple[str, object]] = []

    def capture(self):
        self.events.append(("capture", None))
        return dict(self.state)

    def set_text(self, text: str) -> None:
        self.events.append(("set_text", text))
        self.state = {"text/plain": text.encode("utf-8")}

    def restore(self, snapshot) -> None:
        self.events.append(("restore", snapshot))
        self.state = snapshot


class FakeKeyboard:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def send_shortcut(self, shortcut: str) -> None:
        self.events.append(("shortcut", shortcut))

    def send_key(self, key_name: str) -> None:
        self.events.append(("key", key_name))


class FakeDelay:
    def __init__(self) -> None:
        self.delays: list[int] = []

    def wait(self, milliseconds: int) -> None:
        self.delays.append(milliseconds)


def test_execute_returns_error_when_browser_window_missing():
    service = FindActionService(
        locator=FakeLocator(LocateWindowResult(False, "Не найдено")),
        activator=FakeActivator(),
        clipboard=FakeClipboard(),
        keyboard=FakeKeyboard(),
        delay=FakeDelay(),
    )

    result = service.execute("ИНН", minimize_window=lambda: None)

    assert result.success is False
    assert result.message == "Не найдено"


def test_execute_runs_steps_in_expected_order_and_restores_clipboard():
    clipboard = FakeClipboard()
    keyboard = FakeKeyboard()
    delay = FakeDelay()
    minimized: list[str] = []
    service = FindActionService(
        locator=FakeLocator(
            LocateWindowResult(
                True,
                "ok",
                BrowserWindowMatch(hwnd=111, pid=123, title="Browser", score=100),
            )
        ),
        activator=FakeActivator(),
        clipboard=clipboard,
        keyboard=keyboard,
        delay=delay,
    )

    result = service.execute("Искомая строка", minimize_window=lambda: minimized.append("yes"))

    assert result.success is True
    assert keyboard.events == [
        ("shortcut", CTRL_F),
        ("shortcut", CTRL_V),
        ("key", ENTER),
        ("key", ESCAPE),
    ]
    assert delay.delays == [250, 250, 500, 250, 250]
    assert minimized == ["yes"]
    assert clipboard.events[0] == ("capture", None)
    assert clipboard.events[1] == ("set_text", "Искомая строка")
    assert clipboard.events[-1][0] == "restore"
    assert clipboard.state == {"text/plain": b"old"}


def test_execute_duplicate_tab_runs_extended_sequence_before_search():
    clipboard = FakeClipboard()
    keyboard = FakeKeyboard()
    delay = FakeDelay()
    minimized: list[str] = []
    service = FindActionService(
        locator=FakeLocator(
            LocateWindowResult(
                True,
                "ok",
                BrowserWindowMatch(hwnd=111, pid=123, title="Browser", score=100),
            )
        ),
        activator=FakeActivator(),
        clipboard=clipboard,
        keyboard=keyboard,
        delay=delay,
    )

    result = service.execute(
        "Искомая строка",
        minimize_window=lambda: minimized.append("yes"),
        duplicate_tab=True,
    )

    assert result.success is True
    assert keyboard.events == [
        ("shortcut", CTRL_L),
        ("shortcut", ALT_ENTER),
        ("shortcut", CTRL_F),
        ("shortcut", CTRL_V),
        ("key", ENTER),
        ("key", ESCAPE),
    ]
    assert delay.delays == [250, 250, 250, 250, 500, 250, 250]
    assert minimized == ["yes"]
    assert clipboard.state == {"text/plain": b"old"}


def test_execute_uses_custom_post_paste_delay_when_provided():
    clipboard = FakeClipboard()
    keyboard = FakeKeyboard()
    delay = FakeDelay()
    service = FindActionService(
        locator=FakeLocator(
            LocateWindowResult(
                True,
                "ok",
                BrowserWindowMatch(hwnd=111, pid=123, title="Browser", score=100),
            )
        ),
        activator=FakeActivator(),
        clipboard=clipboard,
        keyboard=keyboard,
        delay=delay,
    )

    result = service.execute(
        "Искомая строка",
        minimize_window=lambda: None,
        delay_ms=120,
        post_paste_delay_ms=500,
    )

    assert result.success is True
    assert delay.delays == [120, 120, 500, 120, 120]


def test_execute_restores_clipboard_on_failure():
    class BrokenKeyboard(FakeKeyboard):
        def send_key(self, key_name: str) -> None:
            raise RuntimeError("boom")

    clipboard = FakeClipboard()
    service = FindActionService(
        locator=FakeLocator(
            LocateWindowResult(
                True,
                "ok",
                BrowserWindowMatch(hwnd=111, pid=123, title="Browser", score=100),
            )
        ),
        activator=FakeActivator(),
        clipboard=clipboard,
        keyboard=BrokenKeyboard(),
        delay=FakeDelay(),
    )

    result = service.execute("строка", minimize_window=lambda: None)

    assert result.success is False
    assert clipboard.state == {"text/plain": b"old"}


def test_execute_stops_when_duplicate_tab_fails():
    class BrokenKeyboard(FakeKeyboard):
        def send_shortcut(self, shortcut: str) -> None:
            if shortcut == ALT_ENTER:
                raise RuntimeError("duplicate failed")
            super().send_shortcut(shortcut)

    clipboard = FakeClipboard()
    keyboard = BrokenKeyboard()
    delay = FakeDelay()
    minimized: list[str] = []
    service = FindActionService(
        locator=FakeLocator(
            LocateWindowResult(
                True,
                "ok",
                BrowserWindowMatch(hwnd=111, pid=123, title="Browser", score=100),
            )
        ),
        activator=FakeActivator(),
        clipboard=clipboard,
        keyboard=keyboard,
        delay=delay,
    )

    result = service.execute(
        "строка",
        minimize_window=lambda: minimized.append("yes"),
        duplicate_tab=True,
    )

    assert result.success is False
    assert keyboard.events == [("shortcut", CTRL_L)]
    assert minimized == []
    assert clipboard.events[-1][0] == "restore"
    assert clipboard.state == {"text/plain": b"old"}


def test_set_browser_profile_path_updates_locator_before_execution():
    locator = FakeLocator(
        LocateWindowResult(
            True,
            "ok",
            BrowserWindowMatch(hwnd=111, pid=123, title="Browser", score=100),
        )
    )
    service = FindActionService(
        locator=locator,
        activator=FakeActivator(),
        clipboard=FakeClipboard(),
        keyboard=FakeKeyboard(),
        delay=FakeDelay(),
    )

    service.set_browser_profile_path(
        r"C:\Users\ExampleUser\AppData\Local\Yandex\YandexBrowser\User Data\Profile 7"
    )
    result = service.execute("строка", minimize_window=lambda: None)

    assert result.success is True
    assert locator.profile_paths == [
        r"C:\Users\ExampleUser\AppData\Local\Yandex\YandexBrowser\User Data\Profile 7"
    ]
