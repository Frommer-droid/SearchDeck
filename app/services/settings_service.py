from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models.app_settings import (
    AppSettings,
    ActionDelaySettings,
    DEFAULT_ACTIVE_TAB_ID,
    DEFAULT_ACTION_DELAY_MS,
    DEFAULT_POST_PASTE_DELAY_MS,
    MAX_ACTION_DELAY_MS,
    MIN_ACTION_DELAY_MS,
    UiScaleSettings,
    WindowGeometry,
    WorkspaceTab,
    normalize_browser_profile_number,
    normalize_active_tab_id,
    normalize_workspace_tabs,
)
from app.models.catalog import ActionButton, Category


MIN_DELTA = -50
MAX_DELTA = 50


class SettingsService:
    """Чтение и запись settings.json."""

    def __init__(self, path: Path, logger: logging.Logger | None = None) -> None:
        self._path = path
        self._logger = logger

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> AppSettings:
        if not self._path.exists():
            return AppSettings()

        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            if self._logger:
                self._logger.warning("Не удалось прочитать settings.json: %s", error)
            return AppSettings()

        return self._deserialize(payload)

    def save(self, settings: AppSettings) -> None:
        payload = self._serialize(settings)
        self._path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _deserialize(self, payload: dict[str, object]) -> AppSettings:
        ui_scale_percent = self._as_int(payload.get("ui_scale_percent"), 100)
        raw_delta = payload.get("ui_scale_delta_percent")
        if raw_delta is None:
            raw_delta = ui_scale_percent - 100
        delta = self._normalize_delta(self._as_int(raw_delta, 0))
        legacy_categories = self._deserialize_categories(payload.get("categories"))
        legacy_expanded_category_ids = self._deserialize_expanded_category_ids(
            payload.get("accordion_expanded_category_ids")
        )
        tabs = self._deserialize_tabs(
            payload.get("tabs"),
            legacy_categories=legacy_categories,
            legacy_expanded_category_ids=legacy_expanded_category_ids,
        )

        return AppSettings(
            window=WindowGeometry(
                x=self._optional_int(payload.get("x")),
                y=self._optional_int(payload.get("y")),
                width=self._optional_int(payload.get("width")),
                height=self._optional_int(payload.get("height")),
                maximized=bool(payload.get("maximized", False)),
            ),
            ui_scale=UiScaleSettings(
                mode=str(payload.get("ui_scale_mode") or "auto"),
                delta_percent=delta,
                percent=self._as_int(payload.get("ui_scale_percent"), 100),
            ),
            action_delay=ActionDelaySettings(
                delay_ms=self._normalize_action_delay(
                    self._optional_int(payload.get("action_delay_ms")),
                    DEFAULT_ACTION_DELAY_MS,
                ),
                post_paste_delay_ms=self._normalize_action_delay(
                    self._optional_int(payload.get("post_paste_delay_ms")),
                    DEFAULT_POST_PASTE_DELAY_MS,
                ),
            ),
            active_tab_id=normalize_active_tab_id(
                str(payload.get("active_tab_id") or DEFAULT_ACTIVE_TAB_ID),
                tabs=tabs,
            ),
            browser_profile_number=normalize_browser_profile_number(
                self._optional_int(payload.get("browser_profile_number"))
            ),
            tabs=tabs,
            expanded_category_ids=legacy_expanded_category_ids,
            categories=legacy_categories,
        )

    @staticmethod
    def _serialize(settings: AppSettings) -> dict[str, object]:
        tabs = normalize_workspace_tabs(
            settings.tabs,
            legacy_categories=settings.categories,
            legacy_expanded_category_ids=settings.expanded_category_ids,
        )
        payload: dict[str, object] = {
            "x": settings.window.x,
            "y": settings.window.y,
            "width": settings.window.width,
            "height": settings.window.height,
            "maximized": settings.window.maximized,
            "ui_scale_mode": settings.ui_scale.mode,
            "ui_scale_delta_percent": settings.ui_scale.delta_percent,
            "ui_scale_percent": settings.ui_scale.percent,
            "action_delay_ms": settings.action_delay.delay_ms,
            "post_paste_delay_ms": settings.action_delay.post_paste_delay_ms,
            "active_tab_id": normalize_active_tab_id(settings.active_tab_id, tabs=tabs),
            "browser_profile_number": normalize_browser_profile_number(
                settings.browser_profile_number
            ),
            "tabs": [
                {
                    "id": tab.id,
                    "title": tab.title,
                    "accordion_expanded_category_ids": tab.expanded_category_ids or [],
                    "categories": [
                        {
                            "id": category.id,
                            "name": category.name,
                            "buttons": [
                                {
                                    "id": button.id,
                                    "label": button.label,
                                    "search_text": button.search_text,
                                }
                                for button in category.buttons
                            ],
                        }
                        for category in tab.categories
                    ],
                }
                for tab in tabs
            ],
        }
        return payload

    @staticmethod
    def _deserialize_categories(value: object) -> list[Category]:
        categories: list[Category] = []
        if not isinstance(value, list):
            return categories

        for raw_category in value:
            if not isinstance(raw_category, dict):
                continue
            buttons: list[ActionButton] = []
            raw_buttons = raw_category.get("buttons")
            if isinstance(raw_buttons, list):
                for raw_button in raw_buttons:
                    if not isinstance(raw_button, dict):
                        continue
                    buttons.append(
                        ActionButton(
                            id=str(raw_button.get("id") or ""),
                            label=str(raw_button.get("label") or "").strip(),
                            search_text=str(raw_button.get("search_text") or "").strip(),
                        )
                    )
            categories.append(
                Category(
                    id=str(raw_category.get("id") or ""),
                    name=str(raw_category.get("name") or "").strip(),
                    buttons=[
                        button
                        for button in buttons
                        if button.id and button.label and button.search_text
                    ],
                )
            )
        return [
            category
            for category in categories
            if category.id and category.name
        ]

    def _deserialize_tabs(
        self,
        value: object,
        legacy_categories: list[Category],
        legacy_expanded_category_ids: list[str] | None,
    ) -> list[WorkspaceTab]:
        parsed_tabs: list[WorkspaceTab] = []
        if isinstance(value, list):
            for raw_tab in value:
                if not isinstance(raw_tab, dict):
                    continue
                parsed_tabs.append(
                    WorkspaceTab(
                        id=str(raw_tab.get("id") or ""),
                        title=str(raw_tab.get("title") or "").strip(),
                        categories=self._deserialize_categories(raw_tab.get("categories")),
                        expanded_category_ids=self._deserialize_expanded_category_ids(
                            raw_tab.get("accordion_expanded_category_ids")
                        ),
                    )
                )
        return normalize_workspace_tabs(
            parsed_tabs,
            legacy_categories=legacy_categories,
            legacy_expanded_category_ids=legacy_expanded_category_ids,
        )

    @staticmethod
    def _as_int(value: object, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _optional_int(value: object) -> int | None:
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_delta(value: int) -> int:
        return max(MIN_DELTA, min(MAX_DELTA, value))

    @staticmethod
    def _normalize_action_delay(value: int | None, default: int) -> int:
        if value is None:
            return default
        return max(MIN_ACTION_DELAY_MS, min(MAX_ACTION_DELAY_MS, value))

    @staticmethod
    def _deserialize_expanded_category_ids(value: object) -> list[str] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            return None

        expanded_ids: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            expanded_ids.append(normalized)
        return expanded_ids
