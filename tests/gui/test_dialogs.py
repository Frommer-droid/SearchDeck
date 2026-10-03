from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QStyle, QStyleOptionSpinBox

from app.config.app_config import project_root
from app.config.theme import build_stylesheet, build_theme_metrics
from app.ui.dialogs import ActionButtonDialog, BrowserProfileDialog, CategoryDialog, TabDialog


def test_category_dialog_accepts_non_empty_name(qtbot):
    dialog = CategoryDialog("Категория")
    qtbot.addWidget(dialog)
    dialog.name_edit.setText("Документы")

    dialog._submit()

    assert dialog.result_data().name == "Документы"


def test_category_dialog_rejects_empty_name(qtbot, monkeypatch):
    dialog = CategoryDialog("Категория")
    qtbot.addWidget(dialog)
    called = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: called.append(True))

    dialog._submit()

    assert called == [True]


def test_action_button_dialog_prefills_fields(qtbot):
    dialog = ActionButtonDialog("Кнопка", initial_label="ИНН", initial_search_text="Идентификатор")
    qtbot.addWidget(dialog)

    assert dialog.label_edit.text() == "ИНН"
    assert dialog.search_text_edit.toPlainText() == "Идентификатор"


def test_tab_dialog_accepts_non_empty_name(qtbot):
    dialog = TabDialog("Вкладка", initial_name="Архив")
    qtbot.addWidget(dialog)

    dialog._submit()

    assert dialog.result_data().name == "Архив"


def test_tab_dialog_rejects_empty_name(qtbot, monkeypatch):
    dialog = TabDialog("Вкладка")
    qtbot.addWidget(dialog)
    called = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: called.append(True))

    dialog._submit()

    assert called == [True]


def test_browser_profile_dialog_prefills_and_returns_profile_number(qtbot):
    dialog = BrowserProfileDialog(initial_profile_number=7)
    qtbot.addWidget(dialog)

    dialog.profile_spinbox.setValue(9)
    dialog._submit()

    assert dialog.result_data().profile_number == 9


def test_browser_profile_spinbox_step_buttons_are_clickable(qtbot):
    dialog = BrowserProfileDialog(initial_profile_number=1)
    dialog.setStyleSheet(
        build_stylesheet(build_theme_metrics(1.0), project_root() / "assets" / "icons")
    )
    qtbot.addWidget(dialog)
    dialog.show()

    spinbox = dialog.profile_spinbox
    option = QStyleOptionSpinBox()
    spinbox.initStyleOption(option)
    up_rect = spinbox.style().subControlRect(
        QStyle.ComplexControl.CC_SpinBox,
        option,
        QStyle.SubControl.SC_SpinBoxUp,
        spinbox,
    )
    down_rect = spinbox.style().subControlRect(
        QStyle.ComplexControl.CC_SpinBox,
        option,
        QStyle.SubControl.SC_SpinBoxDown,
        spinbox,
    )

    assert up_rect.width() >= 28
    assert "arrowup.png" in dialog.styleSheet()
    assert "arrowdown.png" in dialog.styleSheet()
    qtbot.mouseClick(spinbox, Qt.MouseButton.LeftButton, pos=up_rect.center())
    assert spinbox.value() == 2
    qtbot.mouseClick(spinbox, Qt.MouseButton.LeftButton, pos=down_rect.center())
    assert spinbox.value() == 1
