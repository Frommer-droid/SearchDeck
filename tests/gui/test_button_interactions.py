from __future__ import annotations

import logging

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from app.core.catalog_service import CatalogService
from app.models.app_settings import AppSettings
from app.models.catalog import ActionButton, Category
from app.services.settings_service import SettingsService
from app.ui.accordion import ActionButtonWidget
from app.ui.main_window import MainWindow


class SpyMainWindow(MainWindow):
    def __init__(self, *args, **kwargs) -> None:
        self.button_menu_calls: list[tuple[str, str, str]] = []
        self.window_menu_calls: list[QPoint] = []
        super().__init__(*args, **kwargs)

    def _show_button_context_menu(self, category: Category, button: ActionButton, widget) -> None:
        self.button_menu_calls.append((category.id, button.id, widget.objectName()))

    def _show_window_context_menu(self, global_pos: QPoint) -> None:
        self.window_menu_calls.append(global_pos)


class RecordingFindActionService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

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


def _build_window(qtbot, tmp_path, workflow: RecordingFindActionService) -> SpyMainWindow:
    settings = AppSettings(
        categories=[
            Category(
                id="cat-1",
                name="Документы",
                buttons=[ActionButton(id="btn-1", label="ИНН", search_text="Искомый текст")],
            )
        ]
    )
    window = SpyMainWindow(
        settings_service=SettingsService(tmp_path / "settings.json"),
        catalog_service=CatalogService(),
        find_action_service=workflow,
        initial_settings=settings,
        logger=logging.getLogger("test.button.interactions"),
    )
    qtbot.addWidget(window)
    window.show()
    return window


def test_left_click_runs_search_in_current_tab(qtbot, tmp_path):
    workflow = RecordingFindActionService()
    window = _build_window(qtbot, tmp_path, workflow)
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
    assert window.button_menu_calls == []
    assert window.window_menu_calls == []


def test_right_click_runs_search_in_duplicated_tab(qtbot, tmp_path):
    workflow = RecordingFindActionService()
    window = _build_window(qtbot, tmp_path, workflow)
    action_button = window.findChildren(ActionButtonWidget, "actionButton")[0]

    assert action_button.contextMenuPolicy() == Qt.ContextMenuPolicy.PreventContextMenu

    qtbot.mouseClick(action_button, Qt.MouseButton.RightButton)

    assert workflow.calls == [
        {
            "search_text": "Искомый текст",
            "delay_ms": 250,
            "post_paste_delay_ms": 500,
            "duplicate_tab": True,
        }
    ]
    assert window.button_menu_calls == []
    assert window.window_menu_calls == []


def test_ctrl_right_click_opens_button_crud_menu_without_running_search(qtbot, tmp_path):
    workflow = RecordingFindActionService()
    window = _build_window(qtbot, tmp_path, workflow)
    action_button = window.findChildren(ActionButtonWidget, "actionButton")[0]

    qtbot.mouseClick(action_button, Qt.MouseButton.RightButton, Qt.KeyboardModifier.ControlModifier)

    assert workflow.calls == []
    assert window.button_menu_calls == [("cat-1", "btn-1", "actionButton")]
    assert window.window_menu_calls == []


def test_drag_start_on_button_does_not_run_search(qtbot, tmp_path):
    workflow = RecordingFindActionService()
    window = _build_window(qtbot, tmp_path, workflow)
    action_button = window.findChildren(ActionButtonWidget, "actionButton")[0]
    drag_calls: list[str] = []
    start_pos = action_button.rect().center()
    move_pos = start_pos + QPoint(24, 0)

    def fake_start_drag() -> None:
        drag_calls.append(action_button.action_button.id)
        action_button._drag_started = True

    action_button._start_drag = fake_start_drag  # type: ignore[method-assign]

    qtbot.mousePress(action_button, Qt.MouseButton.LeftButton, pos=start_pos)
    move_event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(move_pos),
        QPointF(action_button.mapToGlobal(move_pos)),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(action_button, move_event)
    qtbot.mouseRelease(action_button, Qt.MouseButton.LeftButton, pos=move_pos)

    assert drag_calls == ["btn-1"]
    assert workflow.calls == []
