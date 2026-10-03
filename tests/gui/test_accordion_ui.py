from __future__ import annotations

import json
import logging

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from app.core.catalog_service import CatalogService
from app.models.app_settings import AppSettings
from app.models.catalog import ActionButton, Category
from app.services.settings_service import SettingsService
from app.ui.accordion import build_action_button_mime_data, build_category_mime_data
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
                buttons=[
                    ActionButton(id="btn-1", label="ИНН", search_text="ИНН"),
                    ActionButton(id="btn-2", label="СНИЛС", search_text="СНИЛС"),
                ],
            ),
            Category(
                id="cat-2",
                name="Пациенты",
                buttons=[ActionButton(id="btn-3", label="ФИО", search_text="ФИО")],
            ),
        ]
    )
    window = MainWindow(
        settings_service=SettingsService(tmp_path / "settings.json"),
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=settings,
        logger=logging.getLogger("test.accordion"),
    )
    qtbot.addWidget(window)
    window.show()
    return window


def test_multiple_categories_can_stay_expanded(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    documents = window._category_sections["cat-1"]
    patients = window._category_sections["cat-2"]

    assert documents.is_expanded() is True
    assert patients.is_expanded() is True

    qtbot.mouseClick(documents.header_button, Qt.MouseButton.LeftButton)

    assert documents.is_expanded() is False
    assert patients.is_expanded() is True


def test_expanded_category_renders_buttons_inside_body(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    documents = window._category_sections["cat-1"]

    assert [widget.text() for widget in documents.button_widgets] == ["ИНН", "СНИЛС"]
    assert documents.body_widget.isVisible() is True


def test_category_header_spans_full_width_and_right_side_click_toggles_section(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    documents = window._category_sections["cat-1"]
    header = documents.header_button

    assert header.width() >= documents.width() - 2
    assert header.width() > header.fontMetrics().horizontalAdvance(header.text()) + 20

    qtbot.mouseClick(
        header,
        Qt.MouseButton.LeftButton,
        pos=QPoint(header.width() - 5, header.height() // 2),
    )

    assert documents.is_expanded() is False


def test_drag_drop_button_on_other_category_header_moves_button(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    target_header = window._category_sections["cat-2"].header_button
    mime_data = build_action_button_mime_data("cat-1", "btn-1")

    drag_enter_event = QDragEnterEvent(
        QPoint(8, target_header.height() // 2),
        Qt.DropAction.MoveAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    target_header.dragEnterEvent(drag_enter_event)

    drop_event = QDropEvent(
        QPointF(8, target_header.height() // 2),
        Qt.DropAction.MoveAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    target_header.dropEvent(drop_event)

    assert drag_enter_event.isAccepted() is True
    assert drop_event.isAccepted() is True
    assert [widget.text() for widget in window._category_sections["cat-1"].button_widgets] == ["СНИЛС"]
    assert [widget.text() for widget in window._category_sections["cat-2"].button_widgets] == ["ФИО", "ИНН"]
    assert window._category_sections["cat-2"].is_expanded() is True


def test_drop_button_on_another_button_reorders_inside_same_category(qtbot, tmp_path):
    window = _build_window(qtbot, tmp_path)
    target_button = window._category_sections["cat-1"].button_widgets[0]
    mime_data = build_action_button_mime_data("cat-1", "btn-2")

    drag_enter_event = QDragEnterEvent(
        QPoint(8, target_button.height() // 2),
        Qt.DropAction.MoveAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    target_button.dragEnterEvent(drag_enter_event)

    drop_event = QDropEvent(
        QPointF(8, target_button.height() // 2),
        Qt.DropAction.MoveAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    target_button.dropEvent(drop_event)

    assert drag_enter_event.isAccepted() is True
    assert drop_event.isAccepted() is True
    assert [widget.text() for widget in window._category_sections["cat-1"].button_widgets] == ["СНИЛС", "ИНН"]


def test_dragging_button_shows_drop_indicator_before_target(qtbot, tmp_path):
    settings = AppSettings(
        categories=[
            Category(
                id="cat-1",
                name="Документы",
                buttons=[
                    ActionButton(id="btn-1", label="ИНН", search_text="ИНН"),
                    ActionButton(id="btn-2", label="СНИЛС", search_text="СНИЛС"),
                    ActionButton(id="btn-3", label="Паспорт", search_text="Паспорт"),
                ],
            )
        ]
    )
    window = MainWindow(
        settings_service=SettingsService(tmp_path / "settings.json"),
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=settings,
        logger=logging.getLogger("test.accordion.button.indicator"),
    )
    qtbot.addWidget(window)
    window.show()

    section = window._category_sections["cat-1"]
    target_button = section.button_widgets[1]
    mime_data = build_action_button_mime_data("cat-1", "btn-3")
    drag_enter_event = QDragEnterEvent(
        QPoint(8, target_button.height() // 2),
        Qt.DropAction.MoveAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    target_button.dragEnterEvent(drag_enter_event)

    indicator = section.body_widget.drop_indicator
    assert drag_enter_event.isAccepted() is True
    assert indicator.isVisible() is True
    assert abs(indicator.geometry().center().y() - target_button.geometry().top()) <= 2


def test_drop_button_below_last_item_moves_it_to_category_end_and_persists(qtbot, tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_service = SettingsService(settings_path)
    initial_settings = AppSettings(
        categories=[
            Category(
                id="cat-1",
                name="Документы",
                buttons=[
                    ActionButton(id="btn-1", label="ИНН", search_text="ИНН"),
                    ActionButton(id="btn-2", label="СНИЛС", search_text="СНИЛС"),
                    ActionButton(id="btn-3", label="Паспорт", search_text="Паспорт"),
                ],
            )
        ]
    )
    window = MainWindow(
        settings_service=settings_service,
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=initial_settings,
        logger=logging.getLogger("test.accordion.reorder.persist"),
    )
    qtbot.addWidget(window)
    window.show()

    section = window._category_sections["cat-1"]
    last_button = section.button_widgets[-1]
    mime_data = build_action_button_mime_data("cat-1", "btn-1")
    drop_y = last_button.geometry().bottom() + 12

    drag_enter_event = QDragEnterEvent(
        QPoint(8, drop_y),
        Qt.DropAction.MoveAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    section.body_widget.dragEnterEvent(drag_enter_event)

    drop_event = QDropEvent(
        QPointF(8, drop_y),
        Qt.DropAction.MoveAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    section.body_widget.dropEvent(drop_event)

    assert drag_enter_event.isAccepted() is True
    assert drop_event.isAccepted() is True
    assert [widget.text() for widget in window._category_sections["cat-1"].button_widgets] == [
        "СНИЛС",
        "Паспорт",
        "ИНН",
    ]
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert [button["id"] for button in payload["tabs"][0]["categories"][0]["buttons"]] == [
        "btn-2",
        "btn-3",
        "btn-1",
    ]


def test_drag_drop_category_on_other_header_reorders_before_target_and_persists(qtbot, tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_service = SettingsService(settings_path)
    initial_settings = AppSettings(
        categories=[
            Category(id="cat-1", name="Документы"),
            Category(id="cat-2", name="Пациенты"),
            Category(id="cat-3", name="Архив"),
        ]
    )
    window = MainWindow(
        settings_service=settings_service,
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=initial_settings,
        logger=logging.getLogger("test.accordion.category.reorder.persist"),
    )
    qtbot.addWidget(window)
    window.show()

    target_header = window._category_sections["cat-1"].header_button
    mime_data = build_category_mime_data("cat-3")
    drag_enter_event = QDragEnterEvent(
        QPoint(8, target_header.height() // 2),
        Qt.DropAction.MoveAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    target_header.dragEnterEvent(drag_enter_event)

    indicator = window.category_drop_area.drop_indicator
    assert drag_enter_event.isAccepted() is True
    assert indicator.isVisible() is True
    assert abs(indicator.geometry().center().y() - window._category_sections["cat-1"].geometry().top()) <= 2

    drop_event = QDropEvent(
        QPointF(8, target_header.height() // 2),
        Qt.DropAction.MoveAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    target_header.dropEvent(drop_event)

    assert drop_event.isAccepted() is True
    assert [category.name for category in window.categories] == ["Архив", "Документы", "Пациенты"]
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert [category["id"] for category in payload["tabs"][0]["categories"]] == [
        "cat-3",
        "cat-1",
        "cat-2",
    ]


def test_drop_category_below_last_item_moves_it_to_end_and_persists(qtbot, tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_service = SettingsService(settings_path)
    initial_settings = AppSettings(
        categories=[
            Category(id="cat-1", name="Документы"),
            Category(id="cat-2", name="Пациенты"),
            Category(id="cat-3", name="Архив"),
        ]
    )
    window = MainWindow(
        settings_service=settings_service,
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=initial_settings,
        logger=logging.getLogger("test.accordion.category.tail.persist"),
    )
    qtbot.addWidget(window)
    window.show()

    last_section = window._category_sections["cat-3"]
    mime_data = build_category_mime_data("cat-1")
    drop_y = last_section.geometry().bottom() + 12
    drag_enter_event = QDragEnterEvent(
        QPoint(8, drop_y),
        Qt.DropAction.MoveAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    window.category_drop_area.dragEnterEvent(drag_enter_event)

    indicator = window.category_drop_area.drop_indicator
    assert drag_enter_event.isAccepted() is True
    assert indicator.isVisible() is True
    assert indicator.geometry().center().y() >= last_section.geometry().bottom() - 1

    drop_event = QDropEvent(
        QPointF(8, drop_y),
        Qt.DropAction.MoveAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.category_drop_area.dropEvent(drop_event)

    assert drop_event.isAccepted() is True
    assert [category.id for category in window.categories] == ["cat-2", "cat-3", "cat-1"]
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert [category["id"] for category in payload["tabs"][0]["categories"]] == [
        "cat-2",
        "cat-3",
        "cat-1",
    ]


def test_accordion_state_is_restored_after_window_restart(qtbot, tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_service = SettingsService(settings_path)
    initial_settings = AppSettings(
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
    )
    first_window = MainWindow(
        settings_service=settings_service,
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=initial_settings,
        logger=logging.getLogger("test.accordion.persistence"),
    )
    qtbot.addWidget(first_window)
    first_window.show()

    qtbot.mouseClick(first_window._category_sections["cat-1"].header_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(first_window._category_sections["cat-2"].header_button, Qt.MouseButton.LeftButton)
    first_window.close()

    restored_settings = settings_service.load()
    assert restored_settings.tabs[0].expanded_category_ids == []

    second_window = MainWindow(
        settings_service=settings_service,
        catalog_service=CatalogService(),
        find_action_service=StubFindActionService(),
        initial_settings=restored_settings,
        logger=logging.getLogger("test.accordion.persistence.reopen"),
    )
    qtbot.addWidget(second_window)
    second_window.show()

    assert second_window._category_sections["cat-1"].is_expanded() is False
    assert second_window._category_sections["cat-2"].is_expanded() is False
