from __future__ import annotations

import logging
from functools import partial
from typing import Callable

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.config.app_config import WINDOW_TITLE, build_browser_profile_path, runtime_root
from app.config.theme import build_stylesheet, build_theme_metrics
from app.core.catalog_service import CatalogError, CatalogNotFoundError, CatalogService
from app.core.find_action_service import FindActionService
from app.core.workspace_tab_service import (
    WorkspaceTabError,
    WorkspaceTabNotFoundError,
    WorkspaceTabService,
)
from app.models.app_settings import (
    AppSettings,
    UiScaleSettings,
    WindowGeometry,
    WorkspaceTab,
    normalize_browser_profile_number,
    normalize_active_tab_id,
    normalize_workspace_tabs,
)
from app.models.catalog import ActionButton, Category
from app.models.ui_scale import ScreenMetrics
from app.services.settings_service import SettingsService
from app.services.ui_scale_service import calculate_scale_state, clamp_content_window_height
from app.ui.accordion import CategoryAccordionSection
from app.ui.drag_drop import CategoryListDropArea
from app.ui.dialogs import (
    ActionButtonDialog,
    BrowserProfileDialog,
    CategoryDialog,
    SettingsDialog,
    TabDialog,
)
from app.ui.window_chrome import TopBar
from app.ui.workspace_tabs import WorkspaceTabBar
from app.ui.theme import enforce_button_proportions


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings_service: SettingsService,
        catalog_service: CatalogService,
        find_action_service: FindActionService,
        initial_settings: AppSettings,
        logger: logging.Logger,
        workspace_tab_service: WorkspaceTabService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._settings_service = settings_service
        self._catalog_service = catalog_service
        self._find_action_service = find_action_service
        self._logger = logger
        self._workspace_tab_service = workspace_tab_service or WorkspaceTabService()
        self._settings = self._normalize_settings(initial_settings)
        self._window_handle_connected = False
        self._screen_connections: list[tuple[object, str, Callable]] = []
        self._active_tab_id = normalize_active_tab_id(
            self._settings.active_tab_id,
            self._settings.tabs,
        )
        self._expanded_category_ids_by_tab = self._build_expanded_state_map(self._settings.tabs)
        self._category_sections: dict[str, CategoryAccordionSection] = {}
        self._live_persist_enabled = False

        self._scale_state = calculate_scale_state(
            self._current_screen_metrics(),
            self._settings.ui_scale.delta_percent,
        )
        self._theme_metrics = build_theme_metrics(self._scale_state.scale_factor)

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowTitle(WINDOW_TITLE)
        self.setObjectName("mainWindow")
        self._build_ui()
        self._apply_browser_profile_to_find_service()
        self._populate_categories()
        self._apply_scale()
        self._restore_initial_geometry()
        self._connect_screen_signals()
        self._live_persist_enabled = True

    @property
    def categories(self) -> list[Category]:
        return self._current_tab().categories

    @property
    def active_tab_id(self) -> str:
        return self._active_tab_id

    @staticmethod
    def _normalize_settings(settings: AppSettings) -> AppSettings:
        settings.tabs = normalize_workspace_tabs(
            settings.tabs,
            legacy_categories=settings.categories,
            legacy_expanded_category_ids=settings.expanded_category_ids,
        )
        settings.active_tab_id = normalize_active_tab_id(settings.active_tab_id, settings.tabs)
        settings.browser_profile_number = normalize_browser_profile_number(
            settings.browser_profile_number
        )
        return settings

    @staticmethod
    def _build_expanded_state_map(tabs: list[WorkspaceTab]) -> dict[str, set[str]]:
        return {
            tab.id: (
                set(tab.expanded_category_ids)
                if tab.expanded_category_ids is not None
                else {category.id for category in tab.categories}
            )
            for tab in tabs
        }

    def _current_tab(self) -> WorkspaceTab:
        for tab in self._settings.tabs:
            if tab.id == self._active_tab_id:
                return tab
        return self._settings.tabs[0]

    def _current_expanded_category_ids(self) -> set[str]:
        return self._expanded_category_ids_by_tab.setdefault(self._active_tab_id, set())

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self.windowHandle() and not self._window_handle_connected:
            self.windowHandle().screenChanged.connect(self._on_window_screen_changed)
            self._window_handle_connected = True
        self._connect_screen_signals()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._persist_settings()
        super().closeEvent(event)

    def moveEvent(self, event) -> None:  # type: ignore[override]
        super().moveEvent(event)
        self._persist_settings_live()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._persist_settings_live()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._persist_settings_live()

    def _build_ui(self) -> None:
        self.root_widget = QWidget()
        self.root_widget.setObjectName("panelRoot")
        self.root_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.root_widget.customContextMenuRequested.connect(
            lambda pos: self._show_window_context_menu(
                self.root_widget.mapToGlobal(pos)
            )
        )
        self.setCentralWidget(self.root_widget)

        self.root_layout = QVBoxLayout(self.root_widget)
        self.root_layout.setContentsMargins(4, 4, 4, 4)
        self.root_layout.setSpacing(4)

        self.top_bar = TopBar()
        self.top_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.top_bar.customContextMenuRequested.connect(
            lambda pos: self._show_window_context_menu(self.top_bar.mapToGlobal(pos))
        )
        self.top_bar.profile_button.clicked.connect(self._open_browser_profile_dialog)
        self._update_browser_profile_button()
        self.root_layout.addWidget(self.top_bar)

        self.workspace_tab_bar = WorkspaceTabBar()
        self.workspace_tab_bar.tab_changed.connect(self._on_tab_changed)
        self.workspace_tab_bar.tab_context_requested.connect(self._show_tab_context_menu)
        self.workspace_tab_bar.sync_tabs(self._settings.tabs, self._active_tab_id)
        self.root_layout.addWidget(self.workspace_tab_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("accordionScrollArea")
        self.root_layout.addWidget(self.scroll_area, stretch=1)
        self.scroll_area.viewport().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.scroll_area.viewport().customContextMenuRequested.connect(
            lambda pos: self._show_window_context_menu(
                self.scroll_area.viewport().mapToGlobal(pos)
            )
        )

        self.category_drop_area = CategoryListDropArea()
        self.category_drop_area.setObjectName("accordionContainer")
        self.category_drop_area.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.category_drop_area.customContextMenuRequested.connect(
            lambda pos: self._show_window_context_menu(
                self.category_drop_area.mapToGlobal(pos)
            )
        )
        self.category_drop_area.reorder_requested.connect(self._reorder_category)
        self.scroll_content = self.category_drop_area
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(4)
        self.scroll_area.setWidget(self.scroll_content)

    def _populate_categories(self, remember_current_state: bool = True) -> None:
        if remember_current_state:
            self._remember_expanded_state()
        self._category_sections.clear()
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        current_tab = self._current_tab()
        if not current_tab.categories:
            self.category_drop_area.set_sections([])
            placeholder = QLabel("Правый клик для добавления категории")
            placeholder.setObjectName("emptyCategoryLabel")
            placeholder.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            placeholder.customContextMenuRequested.connect(
                lambda pos: self._show_window_context_menu(placeholder.mapToGlobal(pos))
            )
            self.scroll_layout.addWidget(placeholder)
            self.scroll_layout.addStretch(1)
            return

        expanded_category_ids = self._current_expanded_category_ids()
        for category in current_tab.categories:
            expanded = category.id in expanded_category_ids
            section = CategoryAccordionSection(category, expanded=expanded)
            section.header_button.toggled.connect(
                partial(self._on_category_toggled, category.id)
            )
            section.category_context_requested.connect(self._show_category_context_menu)
            section.category_reorder_before_requested.connect(self._reorder_category_before_target)
            section.category_drop_indicator_requested.connect(
                self.category_drop_area.show_drop_indicator_before_category
            )
            section.category_drop_indicator_cleared.connect(
                self.category_drop_area.hide_drop_indicator
            )
            section.button_context_requested.connect(self._show_button_context_menu)
            section.button_move_requested.connect(self._move_action_button)
            section.button_reorder_requested.connect(self._reorder_action_button)
            section.action_triggered.connect(self._trigger_action_button)
            self.scroll_layout.addWidget(section)
            self._category_sections[category.id] = section
        self.category_drop_area.set_sections(list(self._category_sections.values()))
        self.scroll_layout.addStretch(1)

    def _remember_expanded_state(self) -> None:
        if not self._category_sections:
            return
        self._expanded_category_ids_by_tab[self._active_tab_id] = {
            category_id
            for category_id, section in self._category_sections.items()
            if section.is_expanded()
        }

    def _on_category_toggled(self, category_id: str, expanded: bool) -> None:
        expanded_category_ids = self._current_expanded_category_ids()
        if expanded:
            expanded_category_ids.add(category_id)
        else:
            expanded_category_ids.discard(category_id)
        self._persist_settings_live()

    def _on_tab_changed(self, tab_id: str) -> None:
        normalized_tab_id = normalize_active_tab_id(tab_id, self._settings.tabs)
        if normalized_tab_id == self._active_tab_id:
            return
        self._remember_expanded_state()
        self._active_tab_id = normalized_tab_id
        self._settings.active_tab_id = normalized_tab_id
        self._populate_categories(remember_current_state=False)
        QApplication.processEvents()
        self._persist_settings_live()

    def _move_window(self, point: QPoint) -> None:
        if not self.isMaximized():
            self.move(point)

    def _build_window_menu(self) -> QMenu:
        menu = QMenu(self)
        add_category_action = menu.addAction("Добавить категорию")
        add_category_action.triggered.connect(self._add_category)

        if self.categories:
            add_button_menu = menu.addMenu("Добавить кнопку")
            for category in self.categories:
                action = add_button_menu.addAction(category.name)
                action.triggered.connect(partial(self._add_action_button, category))

        menu.addSeparator()
        settings_action = menu.addAction("Настройки")
        settings_action.triggered.connect(self._open_settings_dialog)
        minimize_action = menu.addAction("Свернуть")
        minimize_action.triggered.connect(self.showMinimized)
        close_action = menu.addAction("Закрыть")
        close_action.triggered.connect(self.close)
        return menu

    def _build_tab_menu(self, tab_id: str) -> QMenu:
        menu = QMenu(self)
        rename_action = menu.addAction("Переименовать")
        rename_action.triggered.connect(partial(self._rename_workspace_tab, tab_id))
        add_tab_action = menu.addAction("Добавить вкладку")
        add_tab_action.triggered.connect(self._add_workspace_tab)
        sort_categories_action = menu.addAction("Сортировать категории")
        sort_categories_action.triggered.connect(
            partial(self._sort_workspace_tab_categories, tab_id)
        )
        return menu

    def _build_category_menu(self, category: Category) -> QMenu:
        menu = QMenu(self)
        add_button_action = menu.addAction("Добавить кнопку")
        add_button_action.triggered.connect(partial(self._add_action_button, category))

        section = self._category_sections.get(category.id)
        if section is not None:
            toggle_action = menu.addAction(
                "Свернуть категорию" if section.is_expanded() else "Развернуть категорию"
            )
            toggle_action.triggered.connect(
                partial(section.set_expanded, not section.is_expanded())
            )
        sort_action = menu.addAction("Сортировать")
        sort_action.triggered.connect(partial(self._sort_category_buttons, category))

        menu.addSeparator()
        edit_action = menu.addAction("Изменить категорию")
        edit_action.triggered.connect(partial(self._edit_category, category))
        delete_action = menu.addAction("Удалить категорию")
        delete_action.triggered.connect(partial(self._delete_category, category))
        return menu

    def _build_button_menu(self, category: Category, button: ActionButton) -> QMenu:
        menu = QMenu(self)
        edit_action = menu.addAction("Изменить")
        edit_action.triggered.connect(partial(self._edit_action_button, category, button))
        duplicate_action = menu.addAction("Дублировать")
        duplicate_action.triggered.connect(partial(self._duplicate_action_button, category, button))
        target_categories = [
            target_category
            for target_category in self.categories
            if target_category.id != category.id
        ]
        if target_categories:
            move_menu = menu.addMenu("Перенести")
            for target_category in target_categories:
                action = move_menu.addAction(target_category.name)
                action.triggered.connect(
                    partial(
                        self._move_action_button,
                        category.id,
                        button.id,
                        target_category.id,
                    )
                )
        delete_action = menu.addAction("Удалить")
        delete_action.triggered.connect(partial(self._delete_action_button, category, button))
        return menu

    def _show_window_context_menu(self, global_pos: QPoint) -> None:
        self._build_window_menu().exec(global_pos)

    def _show_tab_context_menu(self, tab_id: str, global_pos: QPoint) -> None:
        self._build_tab_menu(tab_id).exec(global_pos)

    def _show_category_context_menu(self, category: Category, widget: QWidget) -> None:
        self._build_category_menu(category).exec(widget.mapToGlobal(widget.rect().bottomLeft()))

    def _show_button_context_menu(
        self,
        category: Category,
        button: ActionButton,
        widget: QWidget,
    ) -> None:
        self._build_button_menu(category, button).exec(
            widget.mapToGlobal(widget.rect().bottomLeft())
        )

    def _add_category(self) -> None:
        dialog = CategoryDialog("Добавить категорию", parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        current_tab = self._current_tab()
        try:
            categories, category = self._catalog_service.add_category(
                current_tab.categories,
                dialog.result_data().name,
            )
        except CatalogError as error:
            self._show_error(str(error))
            return
        current_tab.categories = categories
        self._current_expanded_category_ids().add(category.id)
        self._populate_categories()
        self._persist_settings()

    def _add_workspace_tab(self) -> None:
        dialog = TabDialog("Добавить вкладку", parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        try:
            self._settings.tabs, created_tab = self._workspace_tab_service.add_tab(
                self._settings.tabs,
                dialog.result_data().name,
            )
        except WorkspaceTabError as error:
            self._show_error(str(error))
            return

        self._active_tab_id = created_tab.id
        self._settings.active_tab_id = created_tab.id
        self._expanded_category_ids_by_tab.setdefault(created_tab.id, set())
        self.workspace_tab_bar.sync_tabs(self._settings.tabs, self._active_tab_id)
        self._populate_categories(remember_current_state=False)
        QApplication.processEvents()
        self._persist_settings()

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(
            initial_delay_ms=self._settings.action_delay.delay_ms,
            initial_post_paste_delay_ms=self._settings.action_delay.post_paste_delay_ms,
            initial_ui_scale_delta_percent=self._settings.ui_scale.delta_percent,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        result = dialog.result_data()
        self._settings.action_delay.delay_ms = result.action_delay_ms
        self._settings.action_delay.post_paste_delay_ms = result.post_paste_delay_ms
        scale_changed = result.ui_scale_delta_percent != self._settings.ui_scale.delta_percent
        self._settings.ui_scale.delta_percent = result.ui_scale_delta_percent
        if scale_changed:
            self._apply_scale()
            self._resize_to_content()
        self._persist_settings()

    def _open_browser_profile_dialog(self) -> None:
        dialog = BrowserProfileDialog(
            initial_profile_number=self._settings.browser_profile_number,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        self._settings.browser_profile_number = normalize_browser_profile_number(
            dialog.result_data().profile_number
        )
        self._update_browser_profile_button()
        self._apply_browser_profile_to_find_service()
        self._persist_settings()

    def _rename_workspace_tab(self, tab_id: str) -> None:
        try:
            tab = self._find_tab(tab_id)
        except WorkspaceTabNotFoundError as error:
            self._show_error(str(error))
            return

        dialog = TabDialog("Переименовать вкладку", initial_name=tab.title, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        try:
            self._settings.tabs = self._workspace_tab_service.rename_tab(
                self._settings.tabs,
                tab_id,
                dialog.result_data().name,
            )
        except (WorkspaceTabError, WorkspaceTabNotFoundError) as error:
            self._show_error(str(error))
            return

        self.workspace_tab_bar.sync_tabs(self._settings.tabs, self._active_tab_id)
        self._persist_settings()

    def _edit_category(self, category: Category) -> None:
        dialog = CategoryDialog("Изменить категорию", initial_name=category.name, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        current_tab = self._current_tab()
        try:
            current_tab.categories = self._catalog_service.rename_category(
                current_tab.categories,
                category.id,
                dialog.result_data().name,
            )
        except (CatalogError, CatalogNotFoundError) as error:
            self._show_error(str(error))
            return
        self._populate_categories()
        self._persist_settings()

    def _delete_category(self, category: Category) -> None:
        answer = QMessageBox.question(
            self,
            "Удаление категории",
            f"Удалить категорию «{category.name}» вместе со всеми кнопками?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        current_tab = self._current_tab()
        try:
            current_tab.categories = self._catalog_service.delete_category(
                current_tab.categories,
                category.id,
            )
        except CatalogNotFoundError as error:
            self._show_error(str(error))
            return
        self._current_expanded_category_ids().discard(category.id)
        self._populate_categories()
        self._persist_settings()

    def _add_action_button(self, category: Category) -> None:
        dialog = ActionButtonDialog("Добавить кнопку", parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        result = dialog.result_data()
        current_tab = self._current_tab()
        try:
            current_tab.categories, _ = self._catalog_service.add_button(
                current_tab.categories,
                category.id,
                result.label,
                result.search_text,
            )
        except (CatalogError, CatalogNotFoundError) as error:
            self._show_error(str(error))
            return
        self._current_expanded_category_ids().add(category.id)
        self._populate_categories()
        self._persist_settings()

    def _edit_action_button(self, category: Category, button: ActionButton) -> None:
        dialog = ActionButtonDialog(
            "Изменить кнопку",
            initial_label=button.label,
            initial_search_text=button.search_text,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        result = dialog.result_data()
        current_tab = self._current_tab()
        try:
            current_tab.categories = self._catalog_service.update_button(
                current_tab.categories,
                category.id,
                button.id,
                result.label,
                result.search_text,
            )
        except (CatalogError, CatalogNotFoundError) as error:
            self._show_error(str(error))
            return
        self._current_expanded_category_ids().add(category.id)
        self._populate_categories()
        self._persist_settings()

    def _delete_action_button(self, category: Category, button: ActionButton) -> None:
        answer = QMessageBox.question(
            self,
            "Удаление кнопки",
            f"Удалить кнопку «{button.label}»?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        current_tab = self._current_tab()
        try:
            current_tab.categories = self._catalog_service.delete_button(
                current_tab.categories,
                category.id,
                button.id,
            )
        except CatalogNotFoundError as error:
            self._show_error(str(error))
            return
        self._current_expanded_category_ids().add(category.id)
        self._populate_categories()
        self._persist_settings()

    def _duplicate_action_button(self, category: Category, button: ActionButton) -> None:
        current_tab = self._current_tab()
        try:
            current_tab.categories, _ = self._catalog_service.duplicate_button(
                current_tab.categories,
                category.id,
                button.id,
            )
        except CatalogNotFoundError as error:
            self._show_error(str(error))
            return
        self._current_expanded_category_ids().add(category.id)
        self._populate_categories()
        self._persist_settings()

    def _move_action_button(
        self,
        source_category_id: str,
        button_id: str,
        target_category_id: str,
    ) -> None:
        current_tab = self._current_tab()
        try:
            current_tab.categories = self._catalog_service.move_button(
                current_tab.categories,
                source_category_id,
                button_id,
                target_category_id,
            )
        except CatalogNotFoundError as error:
            self._show_error(str(error))
            return
        expanded_category_ids = self._current_expanded_category_ids()
        expanded_category_ids.add(source_category_id)
        expanded_category_ids.add(target_category_id)
        self._populate_categories()
        target_section = self._category_sections.get(target_category_id)
        if target_section is not None:
            target_section.set_expanded(True)
            QApplication.processEvents()
        expanded_category_ids.add(target_category_id)
        self._persist_settings()

    def _reorder_action_button(
        self,
        category_id: str,
        button_id: str,
        target_index: int,
    ) -> None:
        current_tab = self._current_tab()
        try:
            current_tab.categories = self._catalog_service.reorder_button(
                current_tab.categories,
                category_id,
                button_id,
                target_index,
            )
        except CatalogNotFoundError as error:
            self._show_error(str(error))
            return
        self._current_expanded_category_ids().add(category_id)
        self._populate_categories()
        self._persist_settings()

    def _reorder_category_before_target(
        self,
        source_category_id: str,
        target_category_id: str,
    ) -> None:
        current_tab = self._current_tab()
        for index, category in enumerate(current_tab.categories):
            if category.id == target_category_id:
                self._reorder_category(source_category_id, index)
                return
        self._show_error("Категория не найдена.")

    def _reorder_category(self, category_id: str, target_index: int) -> None:
        current_tab = self._current_tab()
        try:
            current_tab.categories = self._catalog_service.reorder_category(
                current_tab.categories,
                category_id,
                target_index,
            )
        except CatalogNotFoundError as error:
            self._show_error(str(error))
            return
        self.category_drop_area.hide_drop_indicator()
        self._populate_categories()
        self._persist_settings()

    def _sort_category_buttons(self, category: Category) -> None:
        current_tab = self._current_tab()
        try:
            current_tab.categories = self._catalog_service.sort_buttons(
                current_tab.categories,
                category.id,
            )
        except CatalogNotFoundError as error:
            self._show_error(str(error))
            return
        self._current_expanded_category_ids().add(category.id)
        self._populate_categories()
        self._persist_settings()

    def _sort_workspace_tab_categories(self, tab_id: str) -> None:
        try:
            tab = self._find_tab(tab_id)
        except WorkspaceTabNotFoundError as error:
            self._show_error(str(error))
            return

        tab.categories = self._catalog_service.sort_categories(tab.categories)
        if tab.id == self._active_tab_id:
            self._populate_categories()
        self._persist_settings()

    def _trigger_action_button(self, button: ActionButton, duplicate_tab: bool = False) -> None:
        QApplication.processEvents()
        result = self._find_action_service.execute(
            button.search_text,
            minimize_window=self.showMinimized,
            delay_ms=self._settings.action_delay.delay_ms,
            post_paste_delay_ms=self._settings.action_delay.post_paste_delay_ms,
            duplicate_tab=duplicate_tab,
        )
        self._logger.info(
            "Сценарий кнопки '%s' (%s): %s",
            button.label,
            "duplicate_tab" if duplicate_tab else "current_tab",
            result.message,
        )
        if not result.success:
            self._show_error(result.message)

    def _apply_scale(self) -> None:
        self._scale_state = calculate_scale_state(
            self._current_screen_metrics(),
            self._settings.ui_scale.delta_percent,
        )
        self._settings.ui_scale = UiScaleSettings(
            mode="auto",
            delta_percent=self._scale_state.delta_percent,
            percent=self._scale_state.final_percent,
        )
        self._theme_metrics = build_theme_metrics(self._scale_state.scale_factor)
        self.setStyleSheet(build_stylesheet(self._theme_metrics, runtime_root() / "assets" / "icons"))
        from PySide6.QtWidgets import QAbstractButton
        enforce_button_proportions(self.findChildren(QAbstractButton))
        self.setMinimumSize(self._theme_metrics.minimum_width, self._theme_metrics.minimum_height)
        margin = max(4, round(4 * self._scale_state.scale_factor))
        self.root_layout.setContentsMargins(margin, margin, margin, margin)
        self.root_layout.setSpacing(self._theme_metrics.spacing)
        self.scroll_layout.setSpacing(self._theme_metrics.spacing)
        self.top_bar.setFixedHeight(self._theme_metrics.title_bar_height + 4)

    def _restore_initial_geometry(self) -> None:
        if self._settings.window.is_valid():
            self.setGeometry(
                self._settings.window.x or 100,
                self._settings.window.y or 100,
                max(self._settings.window.width or 0, self._theme_metrics.minimum_width),
                max(self._settings.window.height or 0, self._theme_metrics.minimum_height),
            )
            if self._settings.window.maximized:
                self.showMaximized()
            return
        self._resize_to_content()
        self._center_on_screen()

    def _resize_to_content(self) -> None:
        if self.isMaximized():
            return
        QApplication.processEvents()
        screen = self._current_qscreen()
        available = screen.availableGeometry()
        width = max(
            self.minimumWidth(),
            self.root_widget.sizeHint().width(),
            self._theme_metrics.sidebar_width,
        )
        content_height = self._calculate_content_window_height()
        target_height = clamp_content_window_height(
            content_height,
            self.minimumHeight(),
            available.height(),
        )
        current_top_left = self.geometry().topLeft()
        max_x = max(available.left(), available.right() - width)
        max_y = max(available.top(), available.bottom() - target_height)
        x = min(max(available.left(), current_top_left.x()), max_x)
        y = min(max(available.top(), current_top_left.y()), max_y)
        self.setGeometry(x, y, width, target_height)

    def _calculate_content_window_height(self) -> int:
        root_margins = self.root_layout.contentsMargins()
        spacing = self.root_layout.spacing()
        visible_blocks = [
            self.top_bar.height() or self.top_bar.sizeHint().height(),
            self.workspace_tab_bar.sizeHint().height(),
            self.scroll_content.sizeHint().height(),
        ]
        return (
            root_margins.top()
            + root_margins.bottom()
            + sum(visible_blocks)
            + spacing * max(0, len(visible_blocks) - 1)
        )

    def _center_on_screen(self) -> None:
        screen = self._current_qscreen()
        available = screen.availableGeometry()
        geometry = self.frameGeometry()
        geometry.moveCenter(available.center())
        self.move(geometry.topLeft())

    def _persist_settings(self) -> None:
        self._remember_expanded_state()
        geometry = self.normalGeometry() if self.isMaximized() else self.geometry()
        self._settings.window = WindowGeometry(
            x=geometry.x(),
            y=geometry.y(),
            width=geometry.width(),
            height=geometry.height(),
            maximized=self.isMaximized(),
        )
        self._settings.active_tab_id = normalize_active_tab_id(
            self._active_tab_id,
            self._settings.tabs,
        )
        self._settings.browser_profile_number = normalize_browser_profile_number(
            self._settings.browser_profile_number
        )
        for tab in self._settings.tabs:
            expanded_category_ids = self._expanded_category_ids_by_tab.setdefault(tab.id, set())
            tab.expanded_category_ids = [
                category.id
                for category in tab.categories
                if category.id in expanded_category_ids
            ]
        self._settings_service.save(self._settings)

    def _persist_settings_live(self) -> None:
        if not self._live_persist_enabled:
            return
        self._persist_settings()

    def _connect_screen_signals(self) -> None:
        self._disconnect_screen_signals()
        app = QApplication.instance()
        if app is None:
            return

        for signal_name in ("primaryScreenChanged", "screenAdded", "screenRemoved"):
            signal = getattr(app, signal_name)
            signal.connect(self._on_app_screen_event)
            self._screen_connections.append((app, signal_name, self._on_app_screen_event))

        screen = self._current_qscreen()
        for signal_name in (
            "logicalDotsPerInchChanged",
            "geometryChanged",
            "availableGeometryChanged",
        ):
            signal = getattr(screen, signal_name)
            signal.connect(self._on_screen_metrics_changed)
            self._screen_connections.append((screen, signal_name, self._on_screen_metrics_changed))

    def _disconnect_screen_signals(self) -> None:
        for owner, signal_name, handler in self._screen_connections:
            try:
                getattr(owner, signal_name).disconnect(handler)
            except (RuntimeError, TypeError):
                continue
        self._screen_connections.clear()

    def _on_window_screen_changed(self, _screen) -> None:
        self._connect_screen_signals()
        self._apply_scale()

    def _on_app_screen_event(self, *_args) -> None:
        self._connect_screen_signals()
        self._apply_scale()

    def _on_screen_metrics_changed(self, *_args) -> None:
        self._apply_scale()

    def _current_qscreen(self):
        app = QApplication.instance()
        window_handle = self.windowHandle()
        if window_handle and window_handle.screen():
            return window_handle.screen()
        return app.primaryScreen()

    def _current_screen_metrics(self) -> ScreenMetrics:
        screen = self._current_qscreen()
        available = screen.availableGeometry()
        return ScreenMetrics(
            width=available.width(),
            height=available.height(),
            dpi=screen.logicalDotsPerInch(),
        )

    def _find_tab(self, tab_id: str) -> WorkspaceTab:
        for tab in self._settings.tabs:
            if tab.id == tab_id:
                return tab
        raise WorkspaceTabNotFoundError("Вкладка не найдена.")

    def _update_browser_profile_button(self) -> None:
        profile_number = normalize_browser_profile_number(self._settings.browser_profile_number)
        self.top_bar.profile_button.setText(f"P{profile_number}")
        self.top_bar.profile_button.setToolTip(f"Профиль браузера: {profile_number}")

    def _apply_browser_profile_to_find_service(self) -> None:
        profile_path = build_browser_profile_path(self._settings.browser_profile_number)
        profile_setter = getattr(self._find_action_service, "set_browser_profile_path", None)
        if callable(profile_setter):
            profile_setter(profile_path)

    def _show_error(self, message: str) -> None:
        self._logger.error(message)
        QMessageBox.warning(self, "Ошибка", message)
