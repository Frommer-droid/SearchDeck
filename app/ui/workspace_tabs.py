from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QTabBar

from app.models.app_settings import WorkspaceTab


class WorkspaceTabBar(QTabBar):
    tab_changed = Signal(str)
    tab_context_requested = Signal(str, QPoint)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workspaceTabBar")
        self.setDrawBase(False)
        self.setMovable(False)
        self.setTabsClosable(False)
        self.setUsesScrollButtons(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setExpanding(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.customContextMenuRequested.connect(self._emit_tab_context_requested)
        self.currentChanged.connect(self._emit_tab_changed)

    def sync_tabs(self, tabs: list[WorkspaceTab], active_tab_id: str) -> None:
        was_blocked = self.blockSignals(True)
        try:
            while self.count():
                self.removeTab(0)
            for tab in tabs:
                index = self.addTab(tab.title)
                self.setTabData(index, tab.id)
            self.set_active_tab_id(active_tab_id)
        finally:
            self.blockSignals(was_blocked)
        self.updateGeometry()

    def set_active_tab_id(self, tab_id: str) -> None:
        for index in range(self.count()):
            if self.tabData(index) == tab_id:
                if index != self.currentIndex():
                    self.setCurrentIndex(index)
                return
        if self.count():
            self.setCurrentIndex(0)

    def active_tab_id(self) -> str:
        current_index = self.currentIndex()
        if current_index < 0:
            return ""
        return str(self.tabData(current_index) or "")

    def _emit_tab_changed(self, _index: int) -> None:
        tab_id = self.active_tab_id()
        if tab_id:
            self.tab_changed.emit(tab_id)

    def _emit_tab_context_requested(self, pos: QPoint) -> None:
        tab_index = self.tabAt(pos)
        if tab_index < 0:
            return
        tab_id = str(self.tabData(tab_index) or "")
        if not tab_id:
            return
        self.tab_context_requested.emit(tab_id, self.mapToGlobal(pos))
