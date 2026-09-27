from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStatusBar

from app.config.app_config import WINDOW_TITLE
from app.core.catalog_service import CatalogService
from app.models.app_settings import AppSettings
from app.models.browser import BrowserWindowMatch
from app.models.catalog import ActionButton, Category
from app.services.settings_service import SettingsService
from app.ui.accordion import ActionButtonWidget, CategoryAccordionSection
from app.ui.main_window import MainWindow
from app.ui.workspace_tabs import WorkspaceTabBar


class StubFindActionService:
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
        return type(
            "Result",
            (),
            {"success": True, "message": "ok", "match": BrowserWindowMatch(1, 1, "title", 1)},
        )()


def _build_window(qtbot, tmp_path, settings: AppSettings, workflow: StubFindActionService | None = None) -> MainWindow:
    window = MainWindow(
        settings_service=SettingsService(tmp_path / "settings.json"),
        catalog_service=CatalogService(),
        find_action_service=workflow or StubFindActionService(),
        initial_settings=settings,
        logger=logging.getLogger("test.window"),
    )
    qtbot.addWidget(window)
    window.show()
    return window


def test_main_window_builds_as_compact_native_window_accordion(qtbot, tmp_path):
    settings = AppSettings(
        categories=[
            Category(
                id="cat-1",
                name="Документы",
                buttons=[ActionButton(id="btn-1", label="ИНН", search_text="ИНН")],
            )
        ]
    )
    window = _build_window(qtbot, tmp_path, settings)

    assert window.windowTitle() == WINDOW_TITLE
    assert not window.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert window.windowFlags() & Qt.WindowType.WindowMinimizeButtonHint
    assert window.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint
    assert window.windowFlags() & Qt.WindowType.WindowCloseButtonHint
    assert window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert "#282C34" in window.styleSheet()
    assert '"Tahoma", "Segoe UI", "Aptos"' in window.styleSheet()
    assert "QTabBar#workspaceTabBar::tab:selected" in window.styleSheet()
    assert "#61AFEF" in window.styleSheet()
    assert "QToolButton#categoryHeader:pressed" in window.styleSheet()
    assert "QPushButton#actionButton:disabled" in window.styleSheet()
    assert not hasattr(window, "category_list")
    assert not hasattr(window, "scale_combo")
    assert window.findChild(QStatusBar) is None
    assert window.top_bar.profile_button.isVisible()
    assert window.top_bar.profile_button.text() == "P1"
    assert isinstance(window.workspace_tab_bar, WorkspaceTabBar)
    assert [window.workspace_tab_bar.tabText(index) for index in range(window.workspace_tab_bar.count())] == ["Пример"]
    assert len(window.findChildren(CategoryAccordionSection)) == 1
    assert len(window.findChildren(ActionButtonWidget, "actionButton")) == 1


def test_clicking_action_button_calls_workflow(qtbot, tmp_path):
    workflow = StubFindActionService()
    settings = AppSettings(
        categories=[
            Category(
                id="cat-1",
                name="Документы",
                buttons=[ActionButton(id="btn-1", label="ИНН", search_text="Искомый текст")],
            )
        ]
    )
    window = _build_window(qtbot, tmp_path, settings, workflow)

    action_button = window.findChildren(ActionButtonWidget, "actionButton")[0]
    qtbot.mouseClick(action_button, Qt.MouseButton.LeftButton)

    assert workflow.calls == [
        {
            "search_text": "Искомый текст",
            "delay_ms": 250,
            "post_paste_delay_ms": 500,
            "duplicate_tab": False,
        }
    ]
    assert workflow.profile_path_calls[-1].endswith("Profile 1")
