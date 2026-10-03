from __future__ import annotations

import json
import logging

from PySide6.QtCore import Qt

from app.core.catalog_service import CatalogService
from app.models.app_settings import AppSettings
from app.models.catalog import ActionButton, Category
from app.services.settings_service import SettingsService
from app.ui.accordion import ActionButtonWidget
from app.ui.main_window import MainWindow


class RecordingFindActionService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.profile_path_calls: list[str] = []

    def set_browser_profile_path(self, profile_path: str) -> None:
        self.profile_path_calls.append(profile_path)

    def execute(
        self,
        search_text: str,
        minimize_window,
        delay_ms: int = 250,
        post_paste_delay_ms: int = 500,
        duplicate_tab: bool = False,
    ):
        self.calls.append(
            {
                "search_text": search_text,
                "delay_ms": delay_ms,
                "post_paste_delay_ms": post_paste_delay_ms,
                "duplicate_tab": duplicate_tab,
            }
        )
        return type("Result", (), {"success": True, "message": "ok", "match": None})()


def _build_window(qtbot, tmp_path, workflow: RecordingFindActionService) -> MainWindow:
    settings = AppSettings(
        categories=[
            Category(
                id="cat-1",
                name="Документы",
                buttons=[ActionButton(id="btn-1", label="ИНН", search_text="Искомый текст")],
            )
        ]
    )
    window = MainWindow(
        settings_service=SettingsService(tmp_path / "settings.json"),
        catalog_service=CatalogService(),
        find_action_service=workflow,
        initial_settings=settings,
        logger=logging.getLogger("test.window.settings.flow"),
    )
    qtbot.addWidget(window)
    window.show()
    return window


def test_opening_settings_updates_delays_and_persists_them(qtbot, tmp_path, monkeypatch):
    workflow = RecordingFindActionService()
    window = _build_window(qtbot, tmp_path, workflow)
    settings_path = tmp_path / "settings.json"

    class FakeDialog:
        DialogCode = type("DialogCode", (), {"Accepted": 1})

        def __init__(self, *args, **kwargs) -> None:
            self.kwargs = kwargs

        def exec(self) -> int:
            return 1

        def result_data(self):
            return type(
                "Result",
                (),
                {
                    "action_delay_ms": 640,
                    "post_paste_delay_ms": 900,
                    "ui_scale_delta_percent": 20,
                },
            )()

    monkeypatch.setattr("app.ui.main_window.SettingsDialog", FakeDialog)

    settings_action = next(action for action in window._build_window_menu().actions() if action.text() == "Настройки")
    settings_action.trigger()

    assert window._settings.action_delay.delay_ms == 640
    assert window._settings.action_delay.post_paste_delay_ms == 900
    assert window._settings.ui_scale.delta_percent == 20
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["action_delay_ms"] == 640
    assert payload["post_paste_delay_ms"] == 900
    assert payload["ui_scale_delta_percent"] == 20

    action_button = window.findChildren(ActionButtonWidget, "actionButton")[0]
    qtbot.mouseClick(action_button, Qt.MouseButton.LeftButton)

    assert workflow.calls == [
        {
            "search_text": "Искомый текст",
            "delay_ms": 640,
            "post_paste_delay_ms": 900,
            "duplicate_tab": False,
        }
    ]


def test_opening_browser_profile_dialog_updates_profile_and_persists(qtbot, tmp_path, monkeypatch):
    workflow = RecordingFindActionService()
    window = _build_window(qtbot, tmp_path, workflow)
    settings_path = tmp_path / "settings.json"

    class FakeDialog:
        DialogCode = type("DialogCode", (), {"Accepted": 1})

        def __init__(self, *args, **kwargs) -> None:
            self.kwargs = kwargs

        def exec(self) -> int:
            return 1

        def result_data(self):
            return type("Result", (), {"profile_number": 7})()

    monkeypatch.setattr("app.ui.main_window.BrowserProfileDialog", FakeDialog)

    window.top_bar.profile_button.click()

    assert window._settings.browser_profile_number == 7
    assert window.top_bar.profile_button.text() == "P7"
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["browser_profile_number"] == 7
    assert workflow.profile_path_calls[-1].endswith("Profile 7")
