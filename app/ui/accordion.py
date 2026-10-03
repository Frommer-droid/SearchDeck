from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QContextMenuEvent, QDrag
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.models.catalog import ActionButton, Category
from app.ui.drag_drop import (
    CategoryButtonDropArea,
    build_action_button_mime_data,
    build_category_mime_data,
    extract_action_button_payload,
    extract_category_payload,
)


class ActionButtonWidget(QPushButton):
    secondary_requested = Signal(object)
    context_requested = Signal(object)
    reorder_before_requested = Signal(str, str, str)

    def __init__(self, action_button: ActionButton, category_id: str, parent=None) -> None:
        super().__init__(action_button.label, parent)
        self.action_button = action_button
        self.category_id = category_id
        self.setObjectName("actionButton")
        self.setProperty("variant", "main")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.setAcceptDrops(True)
        self._drag_start_pos: QPoint | None = None
        self._drag_started = False

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self._drag_started = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and self._drag_start_pos is not None
            and (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            self._start_drag()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self._drag_started:
            self._drag_start_pos = None
            self._drag_started = False
            self.setDown(False)
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            if self.rect().contains(event.position().toPoint()):
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self.context_requested.emit(self)
                else:
                    self.secondary_requested.emit(self)
            self._drag_start_pos = None
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # type: ignore[override]
        event.accept()

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if self._accepts_internal_drop(event.mimeData()):
            self._show_drop_indicator()
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._accepts_internal_drop(event.mimeData()):
            self._show_drop_indicator()
            event.acceptProposedAction()
            return
        self._hide_drop_indicator()
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        self._hide_drop_indicator()
        event.accept()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        payload = extract_action_button_payload(event.mimeData())
        if payload is None:
            self._hide_drop_indicator()
            event.ignore()
            return
        source_category_id, button_id = payload
        if source_category_id != self.category_id or button_id == self.action_button.id:
            self._hide_drop_indicator()
            event.ignore()
            return
        self._hide_drop_indicator()
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        self.reorder_before_requested.emit(source_category_id, button_id, self.action_button.id)

    def _start_drag(self) -> None:
        if self._drag_started or self._drag_start_pos is None:
            return

        self._drag_started = True
        self.setDown(False)
        drag = QDrag(self)
        drag.setMimeData(build_action_button_mime_data(self.category_id, self.action_button.id))
        pixmap = self.grab()
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(self._drag_start_pos)
        drag.exec(Qt.DropAction.MoveAction)

    def _accepts_internal_drop(self, mime_data) -> bool:
        payload = extract_action_button_payload(mime_data)
        if payload is None:
            return False
        source_category_id, button_id = payload
        return source_category_id == self.category_id and button_id != self.action_button.id

    def _show_drop_indicator(self) -> None:
        drop_area = self._drop_area()
        if drop_area is not None:
            drop_area.show_drop_indicator_before_button(self.action_button.id)

    def _hide_drop_indicator(self) -> None:
        drop_area = self._drop_area()
        if drop_area is not None:
            drop_area.hide_drop_indicator()

    def _drop_area(self) -> CategoryButtonDropArea | None:
        parent = self.parentWidget()
        return parent if isinstance(parent, CategoryButtonDropArea) else None


class CategoryHeaderButton(QToolButton):
    context_requested = Signal()
    button_drop_requested = Signal(str, str)
    category_reorder_before_requested = Signal(str, str)
    category_drop_indicator_requested = Signal(str)
    category_drop_indicator_cleared = Signal()

    def __init__(self, category: Category, parent=None) -> None:
        super().__init__(parent)
        self.category = category
        self.setObjectName("categoryHeader")
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setArrowType(Qt.ArrowType.DownArrow)
        self.setText(category.name)
        self.setCheckable(True)
        self.setChecked(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setAcceptDrops(True)
        self.customContextMenuRequested.connect(lambda _pos: self.context_requested.emit())
        self._drag_start_pos: QPoint | None = None
        self._drag_started = False

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self._drag_started = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and self._drag_start_pos is not None
            and (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            self._start_drag()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self._drag_started:
            self._drag_start_pos = None
            self._drag_started = False
            self.setDown(False)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if self._accepts_button_drop(event.mimeData()):
            event.acceptProposedAction()
            return
        if self._accepts_category_drop(event.mimeData()):
            self.category_drop_indicator_requested.emit(self.category.id)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._accepts_button_drop(event.mimeData()):
            event.acceptProposedAction()
            return
        if self._accepts_category_drop(event.mimeData()):
            self.category_drop_indicator_requested.emit(self.category.id)
            event.acceptProposedAction()
            return
        self.category_drop_indicator_cleared.emit()
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        self.category_drop_indicator_cleared.emit()
        event.accept()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        button_payload = extract_action_button_payload(event.mimeData())
        if button_payload is not None:
            source_category_id, button_id = button_payload
            if source_category_id == self.category.id:
                event.ignore()
                return
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            self.button_drop_requested.emit(source_category_id, button_id)
            return

        category_id = extract_category_payload(event.mimeData())
        if category_id is None or category_id == self.category.id:
            self.category_drop_indicator_cleared.emit()
            event.ignore()
            return
        self.category_drop_indicator_cleared.emit()
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        self.category_reorder_before_requested.emit(category_id, self.category.id)

    def _start_drag(self) -> None:
        if self._drag_started or self._drag_start_pos is None:
            return

        self._drag_started = True
        self.setDown(False)
        drag = QDrag(self)
        drag.setMimeData(build_category_mime_data(self.category.id))
        pixmap = self.grab()
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(self._drag_start_pos)
        drag.exec(Qt.DropAction.MoveAction)

    def _accepts_button_drop(self, mime_data) -> bool:
        payload = extract_action_button_payload(mime_data)
        if payload is None:
            return False
        source_category_id, _button_id = payload
        return source_category_id != self.category.id

    def _accepts_category_drop(self, mime_data) -> bool:
        category_id = extract_category_payload(mime_data)
        return category_id is not None and category_id != self.category.id


class CategoryAccordionSection(QWidget):
    category_context_requested = Signal(object, object)
    button_context_requested = Signal(object, object, object)
    action_triggered = Signal(object, bool)
    button_move_requested = Signal(str, str, str)
    button_reorder_requested = Signal(str, str, int)
    category_reorder_before_requested = Signal(str, str)
    category_drop_indicator_requested = Signal(str)
    category_drop_indicator_cleared = Signal()

    def __init__(self, category: Category, expanded: bool = True, parent=None) -> None:
        super().__init__(parent)
        self.category = category
        self.setObjectName("categorySection")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        self.header_button = CategoryHeaderButton(category)
        self.header_button.setChecked(expanded)
        self.header_button.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self.header_button.toggled.connect(self.set_expanded)
        self.header_button.context_requested.connect(
            lambda: self.category_context_requested.emit(self.category, self.header_button)
        )
        self.header_button.button_drop_requested.connect(
            lambda source_category_id, button_id: self.button_move_requested.emit(
                source_category_id,
                button_id,
                self.category.id,
            )
        )
        self.header_button.category_reorder_before_requested.connect(
            self.category_reorder_before_requested.emit
        )
        self.header_button.category_drop_indicator_requested.connect(
            self.category_drop_indicator_requested.emit
        )
        self.header_button.category_drop_indicator_cleared.connect(
            self.category_drop_indicator_cleared.emit
        )
        self.layout.addWidget(self.header_button)

        self.body_widget = CategoryButtonDropArea(category.id)
        self.body_widget.setObjectName("categoryBody")
        self.body_widget.reorder_requested.connect(self.button_reorder_requested.emit)
        self.body_layout = QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(2)
        self.layout.addWidget(self.body_widget)

        self.button_widgets: list[ActionButtonWidget] = []
        self._render_buttons()
        self.set_expanded(expanded)

    def set_expanded(self, expanded: bool) -> None:
        self.header_button.blockSignals(True)
        self.header_button.setChecked(expanded)
        self.header_button.blockSignals(False)
        self.header_button.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self.body_widget.setVisible(expanded)

    def is_expanded(self) -> bool:
        return self.body_widget.isVisible()

    def update_category(self, category: Category) -> None:
        self.category = category
        self.header_button.category = category
        self.header_button.setText(category.name)
        self.body_widget.set_category_id(category.id)
        self._render_buttons()

    def _render_buttons(self) -> None:
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.button_widgets = []
        if not self.category.buttons:
            self.body_widget.set_button_widgets([])
            placeholder = QLabel("Пусто")
            placeholder.setObjectName("emptyCategoryLabel")
            self.body_layout.addWidget(placeholder)
            return

        for button in self.category.buttons:
            widget = ActionButtonWidget(button, self.category.id)
            widget.clicked.connect(
                lambda _checked=False, current_button=button: self.action_triggered.emit(
                    current_button,
                    False,
                )
            )
            widget.secondary_requested.connect(
                lambda _button_widget, current_button=button: self.action_triggered.emit(
                    current_button,
                    True,
                )
            )
            widget.context_requested.connect(
                lambda button_widget, current_button=button: self.button_context_requested.emit(
                    self.category,
                    current_button,
                    button_widget,
                )
            )
            widget.reorder_before_requested.connect(self._emit_reorder_before_request)
            self.body_layout.addWidget(widget)
            self.button_widgets.append(widget)
        self.body_widget.set_button_widgets(self.button_widgets)

    def _emit_reorder_before_request(
        self,
        source_category_id: str,
        button_id: str,
        target_button_id: str,
    ) -> None:
        for index, button_widget in enumerate(self.button_widgets):
            if button_widget.action_button.id == target_button_id:
                self.button_reorder_requested.emit(source_category_id, button_id, index)
                return
