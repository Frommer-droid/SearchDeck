from __future__ import annotations

import logging

from PySide6.QtCore import QPoint, Qt

from app.core.catalog_service import CatalogService
from app.models.app_settings import AppSettings
from app.models.catalog import ActionButton, Category
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow


class SpyMainWindow(MainWindow):
    def __init__(self, *args, **kwargs) -> None:
        self.minimize_calls = 0
        self.window_menu_calls: list[QPoint] = []
        self.tab_menu_calls: list[str] = []
        self.category_menu_calls: list[tuple[str, str]] = []
        self.button_menu_calls: list[tuple[str, str, str]] = []
        self.settings_dialog_calls = 0
        super().__init__(*args, **kwargs)

    def showMinimized(self) -> None:  # type: ignore[override]
        self.minimize_calls += 1
        super().showMinimized()

    def _show_window_context_menu(self, global_pos: QPoint) -> None:
        self.window_menu_calls.append(global_pos)

    def _show_tab_context_menu(self, tab_id: str, global_pos: QPoint) -> None:
        self.tab_menu_calls.append(tab_id)

    def _show_category_context_menu(self, category: Category, widget) -> None:
        self.category_menu_calls.append((category.id, widget.objectName()))

    def _show_button_context_menu(self, category: Category, button: ActionButton, widget) -> None:
        self.button_menu_calls.append((category.id, button.id, widget.objectName()))

    def _open_settings_dialog(self) -> None:
        self.settings_dialog_calls += 1


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


def _build_window(qtbot, tmp_path, settings: AppSettings | None = None) -> SpyMainWindow:
    window = SpyMainWindow(
        settings_service=SettingsService(tmp_path / "settings.json"),
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=settings
        or AppSettings(
        categories=[
            Category(
                id="cat-1",
                name="Документы",
                buttons=[ActionButton(id="btn-1", label="ИНН", search_text="ИНН")],
            ),
            Category(
                id="cat-2",
                name="Пациенты",
                buttons=[ActionButton(id="btn-2", label="ФИО", search_text="ФИО")],
            ),
        ]
    ),
        logger=logging.getLogger("test.menus"),
    )
    qtbot.addWidget(window)
    window.show()
    return window


def _menu_texts(menu) -> list[str]:
    return [action.text() for action in menu.actions() if not action.isSeparator()]


def test_category_header_context_menu_contains_category_actions(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    category = window.categories[0]

    assert _menu_texts(window._build_category_menu(category)) == [
        "Добавить кнопку",
        "Свернуть категорию",
        "Сортировать",
        "Изменить категорию",
        "Удалить категорию",
    ]


def test_tab_context_menu_contains_rename_and_add_actions(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    first_tab_id = window._settings.tabs[0].id

    assert _menu_texts(window._build_tab_menu(first_tab_id)) == [
        "Переименовать",
        "Добавить вкладку",
        "Сортировать категории",
    ]


def test_button_context_menu_contains_edit_delete_and_duplicate(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    category = window.categories[0]
    button = category.buttons[0]
    menu = window._build_button_menu(category, button)
    move_action = next(action for action in menu.actions() if action.text() == "Перенести")

    assert _menu_texts(menu) == [
        "Изменить",
        "Дублировать",
        "Перенести",
        "Удалить",
    ]
    assert move_action.menu() is not None
    assert _menu_texts(move_action.menu()) == ["Пациенты"]


def test_empty_area_context_menu_contains_window_actions(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)

    assert _menu_texts(window._build_window_menu()) == [
        "Добавить категорию",
        "Добавить кнопку",
        "Настройки",
        "Свернуть",
        "Закрыть",
    ]


def test_context_signals_route_to_expected_menu_handlers(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    section = window._category_sections["cat-1"]
    button_widget = section.button_widgets[0]

    window.workspace_tab_bar.tab_context_requested.emit(window._settings.tabs[0].id, QPoint(0, 0))
    section.header_button.context_requested.emit()
    button_widget.context_requested.emit(button_widget)
    window.scroll_area.viewport().customContextMenuRequested.emit(QPoint(0, 0))

    assert window.tab_menu_calls == [window._settings.tabs[0].id]
    assert window.category_menu_calls == [("cat-1", "categoryHeader")]
    assert window.button_menu_calls == [("cat-1", "btn-1", "actionButton")]
    assert len(window.window_menu_calls) == 1


def test_plain_right_click_on_button_does_not_open_crud_menu(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    button_widget = window._category_sections["cat-1"].button_widgets[0]

    qtbot.mouseClick(button_widget, Qt.MouseButton.RightButton)

    assert window.button_menu_calls == []
    assert window.window_menu_calls == []


def test_ctrl_right_click_on_button_opens_crud_menu(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    button_widget = window._category_sections["cat-1"].button_widgets[0]

    qtbot.mouseClick(button_widget, Qt.MouseButton.RightButton, Qt.KeyboardModifier.ControlModifier)

    assert window.button_menu_calls == [("cat-1", "btn-1", "actionButton")]


def test_button_move_submenu_transfers_button_to_selected_category(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    category = window.categories[0]
    button = category.buttons[0]
    menu = window._build_button_menu(category, button)
    move_action = next(action for action in menu.actions() if action.text() == "Перенести")
    target_action = move_action.menu().actions()[0]

    target_action.trigger()

    assert [item.label for item in window.categories[0].buttons] == []
    assert [item.label for item in window.categories[1].buttons] == ["ФИО", "ИНН"]
    assert window._category_sections["cat-2"].is_expanded() is True


def test_sort_action_orders_buttons_inside_category(qtbot, tmp_path):
    settings = AppSettings(
        categories=[
            Category(
                id="cat-1",
                name="Документы",
                buttons=[
                    ActionButton(id="btn-1", label="Ярлык", search_text="Ярлык"),
                    ActionButton(id="btn-2", label="анализы", search_text="анализы"),
                    ActionButton(id="btn-3", label="Бланк", search_text="Бланк"),
                ],
            )
        ]
    )
    window = _build_window(qtbot, tmp_path, settings=settings)
    category = window.categories[0]
    menu = window._build_category_menu(category)
    sort_action = next(action for action in menu.actions() if action.text() == "Сортировать")

    sort_action.trigger()

    assert [button.label for button in window.categories[0].buttons] == ["анализы", "Бланк", "Ярлык"]


def test_tab_sort_action_orders_categories_inside_active_tab(qtbot, tmp_path):
    settings = AppSettings(
        categories=[
            Category(id="cat-1", name="Ярлык"),
            Category(id="cat-2", name="анализы"),
            Category(id="cat-3", name="Бланк"),
        ]
    )
    window = _build_window(qtbot, tmp_path, settings=settings)
    menu = window._build_tab_menu(window._settings.tabs[0].id)
    sort_action = next(action for action in menu.actions() if action.text() == "Сортировать категории")

    sort_action.trigger()

    assert [category.name for category in window.categories] == ["анализы", "Бланк", "Ярлык"]


def test_window_menu_settings_action_opens_settings(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)

    settings_action = next(action for action in window._build_window_menu().actions() if action.text() == "Настройки")
    settings_action.trigger()

    assert window.settings_dialog_calls == 1
