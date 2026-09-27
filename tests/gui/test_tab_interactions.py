from __future__ import annotations

import json
import logging

from PySide6.QtCore import Qt

from app.core.catalog_service import CatalogService
from app.models.app_settings import AppSettings, MOSCOW_TAB_ID, SPB_TAB_ID, WorkspaceTab
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


def _build_settings() -> AppSettings:
    return AppSettings(
        tabs=[
            WorkspaceTab(
                id=SPB_TAB_ID,
                title="СПб",
                categories=[
                    Category(
                        id="spb-cat-1",
                        name="СПб документы",
                        buttons=[ActionButton(id="spb-btn-1", label="ИНН", search_text="ИНН")],
                    )
                ],
                expanded_category_ids=["spb-cat-1"],
            ),
            WorkspaceTab(
                id=MOSCOW_TAB_ID,
                title="Москва",
                categories=[
                    Category(
                        id="msk-cat-1",
                        name="Москва документы",
                        buttons=[ActionButton(id="msk-btn-1", label="ФИО", search_text="ФИО")],
                    )
                ],
                expanded_category_ids=["msk-cat-1"],
            ),
        ]
    )


def _build_window(qtbot, tmp_path, settings: AppSettings | None = None) -> MainWindow:
    window = MainWindow(
        settings_service=SettingsService(tmp_path / "settings.json"),
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=settings or _build_settings(),
        logger=logging.getLogger("test.tabs"),
    )
    qtbot.addWidget(window)
    window.show()
    return window


def test_spb_tab_is_active_by_default_and_renders_its_categories(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)

    assert window.active_tab_id == SPB_TAB_ID
    assert [category.name for category in window.categories] == ["СПб документы"]
    assert list(window._category_sections.keys()) == ["spb-cat-1"]
    assert window.workspace_tab_bar.tabRect(1).width() > window.workspace_tab_bar.tabRect(0).width()


def test_left_click_on_moscow_tab_switches_active_content(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    moscow_index = 1
    moscow_center = window.workspace_tab_bar.tabRect(moscow_index).center()

    qtbot.mouseClick(window.workspace_tab_bar, Qt.MouseButton.LeftButton, pos=moscow_center)

    assert window.active_tab_id == MOSCOW_TAB_ID
    assert [category.name for category in window.categories] == ["Москва документы"]
    assert list(window._category_sections.keys()) == ["msk-cat-1"]


def test_active_tab_and_accordion_state_restore_after_restart(qtbot, tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_service = SettingsService(settings_path)
    first_window = MainWindow(
        settings_service=settings_service,
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=_build_settings(),
        logger=logging.getLogger("test.tabs.persist"),
    )
    qtbot.addWidget(first_window)
    first_window.show()

    qtbot.mouseClick(first_window.workspace_tab_bar, Qt.MouseButton.LeftButton, pos=first_window.workspace_tab_bar.tabRect(1).center())
    qtbot.mouseClick(first_window._category_sections["msk-cat-1"].header_button, Qt.MouseButton.LeftButton)
    first_window.close()

    restored_settings = settings_service.load()
    assert restored_settings.active_tab_id == MOSCOW_TAB_ID
    assert restored_settings.tabs[1].expanded_category_ids == []

    second_window = MainWindow(
        settings_service=settings_service,
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=restored_settings,
        logger=logging.getLogger("test.tabs.reopen"),
    )
    qtbot.addWidget(second_window)
    second_window.show()

    assert second_window.active_tab_id == MOSCOW_TAB_ID
    assert second_window._category_sections["msk-cat-1"].is_expanded() is False


def test_accordion_state_is_isolated_between_tabs(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)

    qtbot.mouseClick(window._category_sections["spb-cat-1"].header_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(window.workspace_tab_bar, Qt.MouseButton.LeftButton, pos=window.workspace_tab_bar.tabRect(1).center())

    assert window._category_sections["msk-cat-1"].is_expanded() is True

    qtbot.mouseClick(window.workspace_tab_bar, Qt.MouseButton.LeftButton, pos=window.workspace_tab_bar.tabRect(0).center())

    assert window._category_sections["spb-cat-1"].is_expanded() is False


def test_adding_tab_appends_it_to_end_activates_and_persists(qtbot, tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    settings_service = SettingsService(settings_path)
    window = MainWindow(
        settings_service=settings_service,
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=_build_settings(),
        logger=logging.getLogger("test.tabs.add"),
    )
    qtbot.addWidget(window)
    window.show()

    class FakeDialog:
        DialogCode = type("DialogCode", (), {"Accepted": 1})

        def __init__(self, *args, **kwargs) -> None:
            self.kwargs = kwargs

        def exec(self) -> int:
            return 1

        def result_data(self):
            return type("Result", (), {"name": "Архив"})()

    monkeypatch.setattr("app.ui.main_window.TabDialog", FakeDialog)

    add_action = window._build_tab_menu(window._settings.tabs[0].id).actions()[1]
    add_action.trigger()

    assert [window.workspace_tab_bar.tabText(index) for index in range(window.workspace_tab_bar.count())] == [
        "СПб",
        "Москва",
        "Архив",
    ]
    assert window.active_tab_id == window._settings.tabs[-1].id
    assert window.categories == []
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["tabs"][-1]["title"] == "Архив"
    assert payload["active_tab_id"] == payload["tabs"][-1]["id"]


def test_renaming_tab_updates_tab_bar_and_persists(qtbot, tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    settings_service = SettingsService(settings_path)
    window = MainWindow(
        settings_service=settings_service,
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=_build_settings(),
        logger=logging.getLogger("test.tabs.rename"),
    )
    qtbot.addWidget(window)
    window.show()

    class FakeDialog:
        DialogCode = type("DialogCode", (), {"Accepted": 1})

        def __init__(self, *args, **kwargs) -> None:
            self.kwargs = kwargs

        def exec(self) -> int:
            return 1

        def result_data(self):
            return type("Result", (), {"name": "Север"})()

    monkeypatch.setattr("app.ui.main_window.TabDialog", FakeDialog)

    rename_action = window._build_tab_menu(window._settings.tabs[0].id).actions()[0]
    rename_action.trigger()

    assert window.workspace_tab_bar.tabText(0) == "Север"
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["tabs"][0]["title"] == "Север"
