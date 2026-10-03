from __future__ import annotations

import json
import logging

from PySide6.QtCore import Qt

from app.core.catalog_service import CatalogService
from app.models.app_settings import AppSettings
from app.models.catalog import ActionButton, Category
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow


class StubFindActionService:
    def execute(
        self,
        search_text: str,
        minimize_window,
        delay_ms: int = 250,
        post_paste_delay_ms: int = 500,
        duplicate_tab: bool = False,
    ):
        return type("Result", (), {"success": True, "message": "ok", "match": None})()


def _build_window(qtbot, tmp_path) -> MainWindow:
    settings = AppSettings(
        categories=[
            Category(
                id="cat-1",
                name="Документы",
                buttons=[ActionButton(id="btn-1", label="ИНН", search_text="ИНН")],
            )
        ]
    )
    window = MainWindow(
        settings_service=SettingsService(tmp_path / "settings.json"),
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=settings,
        logger=logging.getLogger("test.window.resize"),
    )
    qtbot.addWidget(window)
    window.show()
    return window


def _build_empty_window(qtbot, tmp_path) -> MainWindow:
    window = MainWindow(
        settings_service=SettingsService(tmp_path / "settings.json"),
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=AppSettings(),
        logger=logging.getLogger("test.window.resize.empty"),
    )
    qtbot.addWidget(window)
    window.show()
    return window


def test_window_uses_native_windows_resize_frame(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)

    assert not window.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert window.windowFlags() & Qt.WindowType.WindowMinimizeButtonHint
    assert window.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint
    assert window.windowFlags() & Qt.WindowType.WindowCloseButtonHint


def test_live_save_persists_geometry_after_resize(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    settings_path = tmp_path / "settings.json"

    window.resize(window.width() + 40, window.height() + 24)

    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["width"] == window.geometry().width()
    assert payload["height"] == window.geometry().height()
    assert payload["x"] == window.geometry().x()
    assert payload["y"] == window.geometry().y()


def test_live_save_persists_geometry_after_move(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    settings_path = tmp_path / "settings.json"

    window.move(window.x() + 30, window.y() + 18)

    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["x"] == window.geometry().x()
    assert payload["y"] == window.geometry().y()
    assert payload["width"] == window.geometry().width()
    assert payload["height"] == window.geometry().height()


def test_live_save_marks_window_as_maximized(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    settings_path = tmp_path / "settings.json"

    window.showMaximized()

    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["maximized"] is True


def test_first_launch_empty_window_uses_content_height(qtbot, tmp_path):
    window = _build_empty_window(qtbot, tmp_path)
    available = window.screen().availableGeometry()

    assert window.height() == window.minimumHeight()
    assert window.height() < round(available.height() * 0.6)


def test_scale_change_resizes_empty_window_to_scaled_content(qtbot, tmp_path, monkeypatch):
    window = _build_empty_window(qtbot, tmp_path)
    original_height = window.height()

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
                    "action_delay_ms": window._settings.action_delay.delay_ms,
                    "post_paste_delay_ms": window._settings.action_delay.post_paste_delay_ms,
                    "ui_scale_delta_percent": 50,
                },
            )()

    monkeypatch.setattr("app.ui.main_window.SettingsDialog", FakeDialog)

    settings_action = next(
        action for action in window._build_window_menu().actions() if action.text() == "Настройки"
    )
    settings_action.trigger()

    assert window.height() == window.minimumHeight()
    assert window.height() > original_height
