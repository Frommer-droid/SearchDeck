from __future__ import annotations

import json
import logging

from app.models.app_settings import (
    ActionDelaySettings,
    AppSettings,
    DEFAULT_ACTIVE_TAB_ID,
    DEFAULT_ACTION_DELAY_MS,
    DEFAULT_BROWSER_PROFILE_NUMBER,
    EXAMPLE_TAB_ID,
    MOSCOW_TAB_ID,
    DEFAULT_POST_PASTE_DELAY_MS,
    SPB_TAB_ID,
    UiScaleSettings,
    WindowGeometry,
    WorkspaceTab,
)
from app.models.catalog import ActionButton, Category
from app.services.settings_service import SettingsService


def test_load_returns_defaults_when_file_missing(tmp_path):
    service = SettingsService(tmp_path / "settings.json")

    settings = service.load()

    assert settings.window == WindowGeometry()
    assert settings.ui_scale == UiScaleSettings()
    assert settings.action_delay.delay_ms == DEFAULT_ACTION_DELAY_MS
    assert settings.action_delay.post_paste_delay_ms == DEFAULT_POST_PASTE_DELAY_MS
    assert settings.active_tab_id == DEFAULT_ACTIVE_TAB_ID
    assert settings.browser_profile_number == DEFAULT_BROWSER_PROFILE_NUMBER
    assert [tab.title for tab in settings.tabs] == ["Пример"]
    assert settings.categories == []


def test_save_and_load_roundtrip_window_and_categories(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    source = AppSettings(
        window=WindowGeometry(x=10, y=20, width=900, height=650, maximized=True),
        ui_scale=UiScaleSettings(mode="auto", delta_percent=20, percent=120),
        action_delay=ActionDelaySettings(delay_ms=640, post_paste_delay_ms=900),
        active_tab_id=MOSCOW_TAB_ID,
        browser_profile_number=3,
        tabs=[
            WorkspaceTab(
                id=SPB_TAB_ID,
                title="СПб",
                categories=[
                    Category(
                        id="cat-1",
                        name="Справки",
                        buttons=[ActionButton(id="btn-1", label="ИНН", search_text="ИНН")],
                    )
                ],
                expanded_category_ids=["cat-1"],
            ),
            WorkspaceTab(
                id=MOSCOW_TAB_ID,
                title="Москва",
                categories=[
                    Category(
                        id="cat-2",
                        name="Пациенты",
                        buttons=[ActionButton(id="btn-2", label="ФИО", search_text="ФИО")],
                    )
                ],
                expanded_category_ids=[],
            ),
        ],
    )

    service.save(source)
    loaded = service.load()

    assert loaded.window == source.window
    assert loaded.ui_scale == source.ui_scale
    assert loaded.action_delay == source.action_delay
    assert loaded.active_tab_id == MOSCOW_TAB_ID
    assert loaded.browser_profile_number == 3
    assert loaded.tabs[0].expanded_category_ids == ["cat-1"]
    assert loaded.tabs[0].categories[0].name == "Справки"
    assert loaded.tabs[0].categories[0].buttons[0].search_text == "ИНН"
    assert loaded.tabs[1].categories[0].name == "Пациенты"


def test_save_and_load_preserves_dynamic_tabs_and_active_tab(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    source = AppSettings(
        active_tab_id="tab-archive",
        browser_profile_number=8,
        tabs=[
            WorkspaceTab(id="tab-inbox", title="Входящие"),
            WorkspaceTab(id="tab-archive", title="Архив"),
            WorkspaceTab(id="tab-ready", title="Готово"),
        ],
    )

    service.save(source)
    loaded = service.load()

    assert loaded.active_tab_id == "tab-archive"
    assert loaded.browser_profile_number == 8
    assert [(tab.id, tab.title) for tab in loaded.tabs] == [
        ("tab-inbox", "Входящие"),
        ("tab-archive", "Архив"),
        ("tab-ready", "Готово"),
    ]


def test_invalid_json_returns_defaults_and_logs_warning(tmp_path, caplog):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text("{invalid", encoding="utf-8")
    logger = logging.getLogger("test.settings")

    service = SettingsService(settings_file, logger=logger)
    with caplog.at_level(logging.WARNING):
        settings = service.load()

    assert settings == AppSettings()
    assert "Не удалось прочитать settings.json" in caplog.text


def test_legacy_ui_scale_percent_is_migrated_to_delta(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"ui_scale_percent": 130}, ensure_ascii=False),
        encoding="utf-8",
    )

    service = SettingsService(settings_file)
    settings = service.load()

    assert settings.ui_scale.delta_percent == 30
    assert settings.ui_scale.percent == 130


def test_missing_action_delay_uses_default(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"x": 10}, ensure_ascii=False), encoding="utf-8")

    service = SettingsService(settings_file)
    settings = service.load()

    assert settings.action_delay.delay_ms == DEFAULT_ACTION_DELAY_MS
    assert settings.action_delay.post_paste_delay_ms == DEFAULT_POST_PASTE_DELAY_MS


def test_invalid_action_delay_is_normalized_to_default(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"action_delay_ms": "bad"}, ensure_ascii=False),
        encoding="utf-8",
    )

    service = SettingsService(settings_file)
    settings = service.load()

    assert settings.action_delay.delay_ms == DEFAULT_ACTION_DELAY_MS
    assert settings.action_delay.post_paste_delay_ms == DEFAULT_POST_PASTE_DELAY_MS


def test_missing_post_paste_delay_uses_default(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"action_delay_ms": 180}, ensure_ascii=False),
        encoding="utf-8",
    )

    service = SettingsService(settings_file)
    settings = service.load()

    assert settings.action_delay.delay_ms == 180
    assert settings.action_delay.post_paste_delay_ms == DEFAULT_POST_PASTE_DELAY_MS


def test_invalid_post_paste_delay_is_normalized_to_default(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"post_paste_delay_ms": "bad"}, ensure_ascii=False),
        encoding="utf-8",
    )

    service = SettingsService(settings_file)
    settings = service.load()

    assert settings.action_delay.delay_ms == DEFAULT_ACTION_DELAY_MS
    assert settings.action_delay.post_paste_delay_ms == DEFAULT_POST_PASTE_DELAY_MS


def test_missing_accordion_state_uses_legacy_default_behavior(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"categories": [{"id": "cat-1", "name": "Документы", "buttons": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    service = SettingsService(settings_file)
    settings = service.load()

    assert settings.expanded_category_ids is None
    assert settings.tabs[0].categories[0].name == "Документы"
    assert len(settings.tabs) == 1


def test_invalid_accordion_state_is_ignored(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"accordion_expanded_category_ids": "bad"}, ensure_ascii=False),
        encoding="utf-8",
    )

    service = SettingsService(settings_file)
    settings = service.load()

    assert settings.expanded_category_ids is None


def test_legacy_categories_are_migrated_to_example_tab(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "categories": [
                    {
                        "id": "cat-1",
                        "name": "Документы",
                        "buttons": [{"id": "btn-1", "label": "ИНН", "search_text": "ИНН"}],
                    }
                ],
                "accordion_expanded_category_ids": ["cat-1"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    service = SettingsService(settings_file)
    settings = service.load()

    assert settings.active_tab_id == EXAMPLE_TAB_ID
    assert settings.tabs[0].categories[0].name == "Документы"
    assert settings.tabs[0].expanded_category_ids == ["cat-1"]
    assert len(settings.tabs) == 1


def test_old_placeholder_tabs_are_replaced_with_example_tab(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "tabs": [
                    {"id": "spb", "title": "СПб", "categories": []},
                    {"id": "moscow", "title": "Москва", "categories": []},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    service = SettingsService(settings_file)
    settings = service.load()

    assert [(tab.id, tab.title) for tab in settings.tabs] == [(EXAMPLE_TAB_ID, "Пример")]


def test_invalid_active_tab_falls_back_to_example(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"active_tab_id": "unknown"}, ensure_ascii=False),
        encoding="utf-8",
    )

    service = SettingsService(settings_file)
    settings = service.load()

    assert settings.active_tab_id == EXAMPLE_TAB_ID


def test_invalid_browser_profile_number_falls_back_to_default(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"browser_profile_number": "bad"}, ensure_ascii=False),
        encoding="utf-8",
    )

    service = SettingsService(settings_file)
    settings = service.load()

    assert settings.browser_profile_number == DEFAULT_BROWSER_PROFILE_NUMBER
