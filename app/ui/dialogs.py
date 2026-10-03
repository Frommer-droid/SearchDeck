from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
)

from app.models.app_settings import (
    DEFAULT_ACTION_DELAY_MS,
    DEFAULT_BROWSER_PROFILE_NUMBER,
    DEFAULT_POST_PASTE_DELAY_MS,
    MAX_ACTION_DELAY_MS,
    MAX_BROWSER_PROFILE_NUMBER,
    MIN_BROWSER_PROFILE_NUMBER,
    MIN_ACTION_DELAY_MS,
)


@dataclass(slots=True, frozen=True)
class CategoryDialogResult:
    name: str


@dataclass(slots=True, frozen=True)
class ActionButtonDialogResult:
    label: str
    search_text: str


@dataclass(slots=True, frozen=True)
class TabDialogResult:
    name: str


@dataclass(slots=True, frozen=True)
class SettingsDialogResult:
    action_delay_ms: int
    post_paste_delay_ms: int
    ui_scale_delta_percent: int


@dataclass(slots=True, frozen=True)
class BrowserProfileDialogResult:
    profile_number: int


class CategoryDialog(QDialog):
    def __init__(self, title: str, initial_name: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.name_edit = QLineEdit(initial_name)
        self.name_edit.setObjectName("categoryNameEdit")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        name_label = QLabel("Название категории")
        name_label.setObjectName("accentLabel")
        form.addRow(name_label, self.name_edit)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._submit)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.resize(420, 120)

    def result_data(self) -> CategoryDialogResult:
        return CategoryDialogResult(name=self.name_edit.text().strip())

    def _submit(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Пустое значение", "Введите название категории.")
            return
        self.accept()


class TabDialog(QDialog):
    def __init__(self, title: str, initial_name: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.name_edit = QLineEdit(initial_name)
        self.name_edit.setObjectName("workspaceTabNameEdit")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        name_label = QLabel("Название вкладки")
        name_label.setObjectName("accentLabel")
        form.addRow(name_label, self.name_edit)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._submit)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.resize(420, 120)

    def result_data(self) -> TabDialogResult:
        return TabDialogResult(name=self.name_edit.text().strip())

    def _submit(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Пустое значение", "Введите название вкладки.")
            return
        self.accept()


class ActionButtonDialog(QDialog):
    def __init__(
        self,
        title: str,
        initial_label: str = "",
        initial_search_text: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.label_edit = QLineEdit(initial_label)
        self.label_edit.setObjectName("actionLabelEdit")
        self.search_text_edit = QPlainTextEdit(initial_search_text)
        self.search_text_edit.setObjectName("actionSearchTextEdit")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        label_label = QLabel("Название кнопки")
        label_label.setObjectName("accentLabel")
        search_label = QLabel("Текст для поиска")
        search_label.setObjectName("accentLabel")
        form.addRow(label_label, self.label_edit)
        form.addRow(search_label, self.search_text_edit)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._submit)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.resize(520, 260)

    def result_data(self) -> ActionButtonDialogResult:
        return ActionButtonDialogResult(
            label=self.label_edit.text().strip(),
            search_text=self.search_text_edit.toPlainText().strip(),
        )

    def _submit(self) -> None:
        if not self.label_edit.text().strip():
            QMessageBox.warning(self, "Пустое значение", "Введите название кнопки.")
            return
        if not self.search_text_edit.toPlainText().strip():
            QMessageBox.warning(self, "Пустое значение", "Введите текст для поиска.")
            return
        self.accept()


class SettingsDialog(QDialog):
    def __init__(
        self,
        initial_delay_ms: int = DEFAULT_ACTION_DELAY_MS,
        initial_post_paste_delay_ms: int = DEFAULT_POST_PASTE_DELAY_MS,
        initial_ui_scale_delta_percent: int = 0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки")

        layout = QVBoxLayout(self)

        self.interval_group = QGroupBox("Промежуток")
        self.interval_group.setObjectName("intervalGroup")
        interval_layout = QFormLayout(self.interval_group)

        delay_label = QLabel("Задержка между действиями (мс)")
        delay_label.setObjectName("accentLabel")
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setObjectName("actionDelaySpinBox")
        self.delay_spinbox.setRange(MIN_ACTION_DELAY_MS, MAX_ACTION_DELAY_MS)
        self.delay_spinbox.setValue(initial_delay_ms)
        interval_layout.addRow(delay_label, self.delay_spinbox)

        post_paste_delay_label = QLabel("Пауза после вставки (мс)")
        post_paste_delay_label.setObjectName("accentLabel")
        self.post_paste_delay_spinbox = QSpinBox()
        self.post_paste_delay_spinbox.setObjectName("postPasteDelaySpinBox")
        self.post_paste_delay_spinbox.setRange(MIN_ACTION_DELAY_MS, MAX_ACTION_DELAY_MS)
        self.post_paste_delay_spinbox.setValue(initial_post_paste_delay_ms)
        interval_layout.addRow(post_paste_delay_label, self.post_paste_delay_spinbox)

        layout.addWidget(self.interval_group)

        self.ui_scale_group = QGroupBox("Масштаб интерфейса")
        self.ui_scale_group.setObjectName("uiScaleGroup")
        ui_scale_layout = QFormLayout(self.ui_scale_group)

        ui_scale_label = QLabel("Масштаб")
        ui_scale_label.setObjectName("accentLabel")
        self.ui_scale_combo = QComboBox()
        self.ui_scale_combo.setObjectName("uiScaleCombo")
        for delta_percent in range(-50, 51, 10):
            self.ui_scale_combo.addItem(f"{100 + delta_percent}%", delta_percent)
        normalized_delta = max(-50, min(50, initial_ui_scale_delta_percent))
        index = self.ui_scale_combo.findData(normalized_delta)
        if index >= 0:
            self.ui_scale_combo.setCurrentIndex(index)
        ui_scale_layout.addRow(ui_scale_label, self.ui_scale_combo)
        layout.addWidget(self.ui_scale_group)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._submit)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.resize(420, 180)

    def result_data(self) -> SettingsDialogResult:
        return SettingsDialogResult(
            action_delay_ms=self.delay_spinbox.value(),
            post_paste_delay_ms=self.post_paste_delay_spinbox.value(),
            ui_scale_delta_percent=int(self.ui_scale_combo.currentData()),
        )

    def _submit(self) -> None:
        self.accept()


class BrowserProfileDialog(QDialog):
    def __init__(
        self,
        initial_profile_number: int = DEFAULT_BROWSER_PROFILE_NUMBER,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Профиль браузера")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        profile_label = QLabel("Номер профиля")
        profile_label.setObjectName("accentLabel")
        self.profile_spinbox = QSpinBox()
        self.profile_spinbox.setObjectName("browserProfileSpinBox")
        self.profile_spinbox.setRange(MIN_BROWSER_PROFILE_NUMBER, MAX_BROWSER_PROFILE_NUMBER)
        self.profile_spinbox.setValue(initial_profile_number)
        form.addRow(profile_label, self.profile_spinbox)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._submit)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.resize(320, 120)

    def result_data(self) -> BrowserProfileDialogResult:
        return BrowserProfileDialogResult(profile_number=self.profile_spinbox.value())

    def _submit(self) -> None:
        self.accept()
