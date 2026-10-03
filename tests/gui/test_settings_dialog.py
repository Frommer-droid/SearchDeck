from __future__ import annotations

from app.models.app_settings import (
    DEFAULT_ACTION_DELAY_MS,
    DEFAULT_POST_PASTE_DELAY_MS,
    MAX_ACTION_DELAY_MS,
    MIN_ACTION_DELAY_MS,
)
from app.ui.dialogs import SettingsDialog


def test_settings_dialog_prefills_delay_value(qtbot):
    dialog = SettingsDialog(
        initial_delay_ms=480,
        initial_post_paste_delay_ms=920,
        initial_ui_scale_delta_percent=20,
    )
    qtbot.addWidget(dialog)

    assert dialog.interval_group.title() == "Промежуток"
    assert dialog.delay_spinbox.value() == 480
    assert dialog.post_paste_delay_spinbox.value() == 920
    assert dialog.ui_scale_group.title() == "Масштаб интерфейса"
    assert dialog.ui_scale_combo.currentText() == "120%"
    assert dialog.ui_scale_combo.currentData() == 20


def test_settings_dialog_accepts_delay_in_range(qtbot):
    dialog = SettingsDialog(
        initial_delay_ms=DEFAULT_ACTION_DELAY_MS,
        initial_post_paste_delay_ms=DEFAULT_POST_PASTE_DELAY_MS,
    )
    qtbot.addWidget(dialog)
    dialog.delay_spinbox.setValue(700)
    dialog.post_paste_delay_spinbox.setValue(1200)
    dialog.ui_scale_combo.setCurrentIndex(dialog.ui_scale_combo.findData(-10))

    dialog._submit()

    assert dialog.result_data().action_delay_ms == 700
    assert dialog.result_data().post_paste_delay_ms == 1200
    assert dialog.result_data().ui_scale_delta_percent == -10


def test_settings_dialog_uses_expected_range(qtbot):
    dialog = SettingsDialog(
        initial_delay_ms=DEFAULT_ACTION_DELAY_MS,
        initial_post_paste_delay_ms=DEFAULT_POST_PASTE_DELAY_MS,
    )
    qtbot.addWidget(dialog)

    assert dialog.delay_spinbox.minimum() == MIN_ACTION_DELAY_MS
    assert dialog.delay_spinbox.maximum() == MAX_ACTION_DELAY_MS
    assert dialog.post_paste_delay_spinbox.minimum() == MIN_ACTION_DELAY_MS
    assert dialog.post_paste_delay_spinbox.maximum() == MAX_ACTION_DELAY_MS
    dialog.delay_spinbox.setValue(MAX_ACTION_DELAY_MS + 100)
    dialog.post_paste_delay_spinbox.setValue(MAX_ACTION_DELAY_MS + 100)

    assert dialog.delay_spinbox.value() == MAX_ACTION_DELAY_MS
    assert dialog.post_paste_delay_spinbox.value() == MAX_ACTION_DELAY_MS


def test_settings_dialog_scale_combo_contains_delta_values(qtbot):
    dialog = SettingsDialog()
    qtbot.addWidget(dialog)

    assert [dialog.ui_scale_combo.itemText(index) for index in range(dialog.ui_scale_combo.count())] == [
        "50%",
        "60%",
        "70%",
        "80%",
        "90%",
        "100%",
        "110%",
        "120%",
        "130%",
        "140%",
        "150%",
    ]
    assert [dialog.ui_scale_combo.itemData(index) for index in range(dialog.ui_scale_combo.count())] == [
        -50,
        -40,
        -30,
        -20,
        -10,
        0,
        10,
        20,
        30,
        40,
        50,
    ]
