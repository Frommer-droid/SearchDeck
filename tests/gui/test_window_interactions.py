from __future__ import annotations

import json
import logging

from PySide6.QtCore import QPoint

from app.core.catalog_service import CatalogService
from app.models.app_settings import AppSettings
from app.models.catalog import ActionButton, Category
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow


class SpyMainWindow(MainWindow):
    def __init__(self, *args, **kwargs) -> None:
        self.minimize_calls = 0
        self.close_calls = 0
        super().__init__(*args, **kwargs)

    def showMinimized(self) -> None:  # type: ignore[override]
        self.minimize_calls += 1
        super().showMinimized()

    def close(self) -> bool:  # type: ignore[override]
        self.close_calls += 1
        return super().close()


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


def _build_window(qtbot, tmp_path) -> SpyMainWindow:
    settings = AppSettings(
        categories=[
            Category(
                id="cat-1",
                name="Документы",
                buttons=[ActionButton(id="btn-1", label="ИНН", search_text="ИНН")],
            )
        ]
    )
    window = SpyMainWindow(
        settings_service=SettingsService(tmp_path / "settings.json"),
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=settings,
        logger=logging.getLogger("test.window.interactions"),
    )
    qtbot.addWidget(window)
    window.show()
    return window


def test_live_save_persists_geometry_after_native_move(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    settings_path = tmp_path / "settings.json"

    window.move(window.geometry().topLeft() + QPoint(30, 18))

    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["x"] == window.geometry().x()
    assert payload["y"] == window.geometry().y()


def test_window_menu_minimize_and_close_actions(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    menu = window._build_window_menu()
    actions = {action.text(): action for action in menu.actions() if action.text()}

    actions["Свернуть"].trigger()
    actions["Закрыть"].trigger()

    assert window.minimize_calls == 1
    assert window.close_calls == 1
