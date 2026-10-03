from __future__ import annotations

import json
from typing import TYPE_CHECKING

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtWidgets import QFrame, QWidget

if TYPE_CHECKING:
    from app.ui.accordion import CategoryAccordionSection


ACTION_BUTTON_MIME_TYPE = "application/x-searchdeck-action-button"
CATEGORY_MIME_TYPE = "application/x-searchdeck-category"


def build_action_button_mime_data(source_category_id: str, button_id: str) -> QMimeData:
    mime_data = QMimeData()
    mime_data.setData(
        ACTION_BUTTON_MIME_TYPE,
        json.dumps(
            {
                "source_category_id": source_category_id,
                "button_id": button_id,
            },
            ensure_ascii=False,
        ).encode("utf-8"),
    )
    return mime_data


def extract_action_button_payload(mime_data: QMimeData) -> tuple[str, str] | None:
    return _extract_payload(
        mime_data,
        ACTION_BUTTON_MIME_TYPE,
        ("source_category_id", "button_id"),
    )


def build_category_mime_data(category_id: str) -> QMimeData:
    mime_data = QMimeData()
    mime_data.setData(
        CATEGORY_MIME_TYPE,
        json.dumps({"category_id": category_id}, ensure_ascii=False).encode("utf-8"),
    )
    return mime_data


def extract_category_payload(mime_data: QMimeData) -> str | None:
    payload = _extract_payload(mime_data, CATEGORY_MIME_TYPE, ("category_id",))
    if payload is None:
        return None
    return payload[0]


def _extract_payload(
    mime_data: QMimeData,
    mime_type: str,
    keys: tuple[str, ...],
) -> tuple[str, ...] | None:
    if not mime_data.hasFormat(mime_type):
        return None
    try:
        payload = json.loads(bytes(mime_data.data(mime_type)).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    values: list[str] = []
    for key in keys:
        value = payload.get(key)
        if not isinstance(value, str):
            return None
        values.append(value)
    return tuple(values)


class DropIndicatorLine(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dropIndicator")
        self.setFixedHeight(3)
        self.hide()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


class CategoryButtonDropArea(QWidget):
    reorder_requested = Signal(str, str, int)

    def __init__(self, category_id: str, parent=None) -> None:
        super().__init__(parent)
        self.category_id = category_id
        self._button_widgets: list[QWidget] = []
        self._indicator_index: int | None = None
        self.drop_indicator = DropIndicatorLine(self)
        self.setAcceptDrops(True)

    def set_category_id(self, category_id: str) -> None:
        self.category_id = category_id

    def set_button_widgets(self, button_widgets: list[QWidget]) -> None:
        self._button_widgets = list(button_widgets)
        if self._indicator_index is not None and self.drop_indicator.isVisible():
            self._update_indicator_geometry()

    def show_drop_indicator(self, target_index: int) -> None:
        self._indicator_index = target_index
        self._update_indicator_geometry()
        self.drop_indicator.show()
        self.drop_indicator.raise_()

    def show_drop_indicator_before_button(self, button_id: str) -> None:
        for index, button_widget in enumerate(self._button_widgets):
            action_button = getattr(button_widget, "action_button", None)
            if getattr(action_button, "id", None) == button_id:
                self.show_drop_indicator(index)
                return

    def hide_drop_indicator(self) -> None:
        self._indicator_index = None
        self.drop_indicator.hide()

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if self._accepts_internal_drop(event.mimeData()):
            self.show_drop_indicator(self._resolve_target_index(event.position().toPoint()))
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._accepts_internal_drop(event.mimeData()):
            self.show_drop_indicator(self._resolve_target_index(event.position().toPoint()))
            event.acceptProposedAction()
            return
        self.hide_drop_indicator()
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        self.hide_drop_indicator()
        event.accept()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        payload = extract_action_button_payload(event.mimeData())
        if payload is None:
            self.hide_drop_indicator()
            event.ignore()
            return
        source_category_id, button_id = payload
        if source_category_id != self.category_id:
            self.hide_drop_indicator()
            event.ignore()
            return
        target_index = self._resolve_target_index(event.position().toPoint())
        self.hide_drop_indicator()
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        self.reorder_requested.emit(source_category_id, button_id, target_index)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._indicator_index is not None and self.drop_indicator.isVisible():
            self._update_indicator_geometry()

    def _accepts_internal_drop(self, mime_data: QMimeData) -> bool:
        payload = extract_action_button_payload(mime_data)
        if payload is None:
            return False
        source_category_id, _button_id = payload
        return source_category_id == self.category_id

    def _resolve_target_index(self, position: QPoint) -> int:
        if not self._button_widgets:
            return 0

        y = position.y()
        first_button = self._button_widgets[0]
        if y <= first_button.geometry().top():
            return 0

        for index, button_widget in enumerate(self._button_widgets):
            geometry = button_widget.geometry()
            if geometry.contains(position) or y < geometry.top():
                return index

        return len(self._button_widgets)

    def _resolve_indicator_y(self, target_index: int) -> int:
        if not self._button_widgets:
            return self.drop_indicator.height()
        if target_index <= 0:
            return self._button_widgets[0].geometry().top()
        if target_index >= len(self._button_widgets):
            return self._button_widgets[-1].geometry().bottom() + max(2, self._layout_spacing() // 2)
        return self._button_widgets[target_index].geometry().top()

    def _update_indicator_geometry(self) -> None:
        if self._indicator_index is None:
            return
        indicator_y = self._resolve_indicator_y(self._indicator_index)
        horizontal_margin = 8
        width = max(16, self.width() - horizontal_margin * 2)
        top = max(0, indicator_y - self.drop_indicator.height() // 2)
        self.drop_indicator.setGeometry(horizontal_margin, top, width, self.drop_indicator.height())

    def _layout_spacing(self) -> int:
        layout = self.layout()
        return layout.spacing() if layout is not None else 0


class CategoryListDropArea(QWidget):
    reorder_requested = Signal(str, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sections: list[CategoryAccordionSection] = []
        self._indicator_index: int | None = None
        self.drop_indicator = DropIndicatorLine(self)
        self.setAcceptDrops(True)

    def set_sections(self, sections: list[CategoryAccordionSection]) -> None:
        self._sections = list(sections)
        if not self._sections:
            self.hide_drop_indicator()
            return
        if self._indicator_index is not None and self.drop_indicator.isVisible():
            self._update_indicator_geometry()

    def show_drop_indicator(self, target_index: int) -> None:
        self._indicator_index = target_index
        self._update_indicator_geometry()
        self.drop_indicator.show()
        self.drop_indicator.raise_()

    def show_drop_indicator_before_category(self, category_id: str) -> None:
        for index, section in enumerate(self._sections):
            if section.category.id == category_id:
                self.show_drop_indicator(index)
                return

    def hide_drop_indicator(self) -> None:
        self._indicator_index = None
        self.drop_indicator.hide()

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if self._accepts_category_drop(event.mimeData()):
            self.show_drop_indicator(self._resolve_target_index(event.position().toPoint()))
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._accepts_category_drop(event.mimeData()):
            self.show_drop_indicator(self._resolve_target_index(event.position().toPoint()))
            event.acceptProposedAction()
            return
        self.hide_drop_indicator()
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        self.hide_drop_indicator()
        event.accept()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        category_id = extract_category_payload(event.mimeData())
        if category_id is None:
            self.hide_drop_indicator()
            event.ignore()
            return
        target_index = self._resolve_target_index(event.position().toPoint())
        self.hide_drop_indicator()
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        self.reorder_requested.emit(category_id, target_index)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._indicator_index is not None and self.drop_indicator.isVisible():
            self._update_indicator_geometry()

    def _accepts_category_drop(self, mime_data: QMimeData) -> bool:
        category_id = extract_category_payload(mime_data)
        if category_id is None or not self._sections:
            return False
        return any(section.category.id != category_id for section in self._sections)

    def _resolve_target_index(self, position: QPoint) -> int:
        if not self._sections:
            return 0

        y = position.y()
        if y <= self._sections[0].geometry().top():
            return 0

        for index, section in enumerate(self._sections):
            geometry = section.geometry()
            if geometry.contains(position) or y < geometry.top():
                return index

        return len(self._sections)

    def _resolve_indicator_y(self, target_index: int) -> int:
        if not self._sections:
            return self.drop_indicator.height()
        if target_index <= 0:
            return self._sections[0].geometry().top()
        if target_index >= len(self._sections):
            return self._sections[-1].geometry().bottom() + max(2, self._layout_spacing() // 2)
        return self._sections[target_index].geometry().top()

    def _update_indicator_geometry(self) -> None:
        if self._indicator_index is None:
            return
        indicator_y = self._resolve_indicator_y(self._indicator_index)
        horizontal_margin = 6
        width = max(16, self.width() - horizontal_margin * 2)
        top = max(0, indicator_y - self.drop_indicator.height() // 2)
        self.drop_indicator.setGeometry(horizontal_margin, top, width, self.drop_indicator.height())

    def _layout_spacing(self) -> int:
        layout = self.layout()
        return layout.spacing() if layout is not None else 0
