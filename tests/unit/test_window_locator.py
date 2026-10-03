from __future__ import annotations

import subprocess

from app.models.browser import ProcessInfo, WindowInfo
from app.services import window_locator
from app.services.window_locator import BrowserWindowLocator, PowerShellProcessInfoProvider, WindowActivator


class StubEnumerator:
    def __init__(self, windows):
        self._windows = windows

    def enumerate_windows(self):
        return self._windows


class StubProcessProvider:
    def __init__(self, processes):
        self._processes = processes

    def get_processes(self, _process_name):
        return self._processes


class StubProfileInfoProvider:
    def __init__(self, directory_name: str, markers: tuple[str, ...]):
        self.directory_name = directory_name
        self.markers = markers

    def get_profile_identity(self, _profile_path):
        from app.services.window_locator import ProfileIdentity

        return ProfileIdentity(self.directory_name, self.markers)


class DynamicProfileInfoProvider:
    def get_profile_identity(self, profile_path):
        from app.services.window_locator import ProfileIdentity

        directory_name = profile_path.rsplit("\\", 1)[-1]
        return ProfileIdentity(directory_name, (directory_name,))


def test_locator_picks_visible_window_for_profile():
    locator = BrowserWindowLocator(
        process_name="browser.exe",
        profile_path=r"C:\Profiles\ExampleUser\AppData\Local\Yandex\YandexBrowser\User Data\Profile 1",
        enumerator=StubEnumerator(
            [
                WindowInfo(hwnd=10, pid=101, title="Окно 1", visible=True),
                WindowInfo(hwnd=20, pid=202, title="Окно 2", visible=True),
            ]
        ),
        process_provider=StubProcessProvider(
            {
                101: ProcessInfo(
                    pid=101,
                    name="browser.exe",
                    executable_path=r"C:\Profiles\ExampleUser\AppData\Local\Yandex\YandexBrowser\Application\browser.exe",
                    command_line='browser.exe --profile-directory="Profile 2"',
                ),
                202: ProcessInfo(
                    pid=202,
                    name="browser.exe",
                    executable_path=r"C:\Profiles\ExampleUser\AppData\Local\Yandex\YandexBrowser\Application\browser.exe",
                    command_line='browser.exe --profile-directory="Profile 1"',
                ),
            }
        ),
        profile_info_provider=StubProfileInfoProvider("Profile 1", ("Profile 1", "ExampleUser")),
    )

    result = locator.locate()

    assert result.success is True
    assert result.match.hwnd == 20


def test_locator_matches_title_marker_when_main_process_is_default():
    locator = BrowserWindowLocator(
        process_name="browser.exe",
        profile_path=r"C:\Profiles\ExampleUser\AppData\Local\Yandex\YandexBrowser\User Data\Profile 1",
        enumerator=StubEnumerator(
            [
                WindowInfo(hwnd=10, pid=101, title="Страница, профиль Другой — Яндекс Браузер", visible=True),
                WindowInfo(hwnd=20, pid=101, title="Документ, профиль ExampleUser — Яндекс Браузер", visible=True),
            ]
        ),
        process_provider=StubProcessProvider(
            {
                101: ProcessInfo(
                    pid=101,
                    name="browser.exe",
                    executable_path=r"C:\Program Files\Yandex\YandexBrowser\Application\browser.exe",
                    command_line='browser.exe --profile-directory=Default',
                ),
            }
        ),
        profile_info_provider=StubProfileInfoProvider("Profile 1", ("Profile 1", "Profi", "ExampleUser")),
    )

    result = locator.locate()

    assert result.success is True
    assert result.match.hwnd == 20


def test_locator_returns_error_when_profile_does_not_match():
    locator = BrowserWindowLocator(
        process_name="browser.exe",
        profile_path=r"C:\Profiles\ExampleUser\AppData\Local\Yandex\YandexBrowser\User Data\Profile 1",
        enumerator=StubEnumerator([WindowInfo(hwnd=10, pid=101, title="Окно", visible=True)]),
        process_provider=StubProcessProvider(
            {
                101: ProcessInfo(
                    pid=101,
                    name="browser.exe",
                    executable_path="browser.exe",
                    command_line='browser.exe --profile-directory="Profile 2"',
                )
            }
        ),
        profile_info_provider=StubProfileInfoProvider("Profile 1", ("Profile 1", "ExampleUser")),
    )

    result = locator.locate()

    assert result.success is False
    assert "профиль profile 1 не совпал" in result.message.casefold()


def test_locator_can_switch_profile_path_dynamically():
    locator = BrowserWindowLocator(
        process_name="browser.exe",
        profile_path=r"C:\Profiles\ExampleUser\AppData\Local\Yandex\YandexBrowser\User Data\Profile 1",
        enumerator=StubEnumerator(
            [
                WindowInfo(hwnd=10, pid=101, title="Окно 1", visible=True),
                WindowInfo(hwnd=20, pid=202, title="Окно 2", visible=True),
            ]
        ),
        process_provider=StubProcessProvider(
            {
                101: ProcessInfo(
                    pid=101,
                    name="browser.exe",
                    executable_path="browser.exe",
                    command_line='browser.exe --profile-directory="Profile 1"',
                ),
                202: ProcessInfo(
                    pid=202,
                    name="browser.exe",
                    executable_path="browser.exe",
                    command_line='browser.exe --profile-directory="Profile 7"',
                ),
            }
        ),
        profile_info_provider=DynamicProfileInfoProvider(),
    )

    locator.set_profile_path(
        r"C:\Profiles\ExampleUser\AppData\Local\Yandex\YandexBrowser\User Data\Profile 7"
    )
    result = locator.locate()

    assert result.success is True
    assert result.match.hwnd == 20


def test_window_activator_does_not_restore_non_minimized_window(monkeypatch):
    calls: list[tuple[str, int, int | None]] = []

    monkeypatch.setattr(window_locator, "IsIconic", lambda hwnd: False)
    monkeypatch.setattr(window_locator, "ShowWindow", lambda hwnd, code: calls.append(("show", hwnd, code)))
    monkeypatch.setattr(window_locator, "BringWindowToTop", lambda hwnd: calls.append(("top", hwnd, None)))
    monkeypatch.setattr(window_locator, "SetForegroundWindow", lambda hwnd: calls.append(("foreground", hwnd, None)) or 1)

    result = WindowActivator().activate(123)

    assert result is True
    assert ("show", 123, window_locator.SW_RESTORE) not in calls
    assert ("top", 123, None) in calls
    assert ("foreground", 123, None) in calls


def test_powershell_process_provider_returns_empty_dict_when_stdout_is_none(monkeypatch):
    provider = PowerShellProcessInfoProvider()

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args=args[0], returncode=0, stdout=None, stderr=None),
    )

    result = provider.get_processes("browser.exe")

    assert result == {}


def test_powershell_process_provider_decodes_non_utf8_stdout(monkeypatch):
    provider = PowerShellProcessInfoProvider()
    payload = (
        '[{"ProcessId":101,"Name":"browser.exe","ExecutablePath":"C:\\\\Program Files\\\\Yandex\\\\browser.exe",'
        '"CommandLine":"browser.exe --profile-directory=\\"Profile 1\\" --comment=\\"Пример\\""}]'
    )
    encoded_payload = payload.encode("cp866")

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=encoded_payload,
            stderr=b"",
        ),
    )

    result = provider.get_processes("browser.exe")

    assert 101 in result
    assert result[101].name == "browser.exe"
    assert "Profile 1" in result[101].command_line
    assert "Пример" in result[101].command_line


def test_powershell_process_provider_returns_empty_dict_for_undecodable_payload(monkeypatch):
    provider = PowerShellProcessInfoProvider()

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=b"\x81\x8d\x8f",
            stderr=b"",
        ),
    )

    result = provider.get_processes("browser.exe")

    assert result == {}


def test_powershell_process_provider_hides_console_window(monkeypatch):
    provider = PowerShellProcessInfoProvider()
    captured_kwargs: dict[str, object] = {}

    def _fake_run(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=b"",
            stderr=b"",
        )

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = provider.get_processes("browser.exe")

    assert result == {}
    assert captured_kwargs["check"] is False
    assert captured_kwargs["capture_output"] is True
    assert captured_kwargs.get("creationflags", 0) == getattr(subprocess, "CREATE_NO_WINDOW", 0)
    startupinfo = captured_kwargs.get("startupinfo")
    if startupinfo is not None:
        assert startupinfo.dwFlags & getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        assert startupinfo.wShowWindow == getattr(subprocess, "SW_HIDE", 0)
