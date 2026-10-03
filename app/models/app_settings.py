from __future__ import annotations

from dataclasses import dataclass, field

from app.models.catalog import Category


DEFAULT_ACTION_DELAY_MS = 250
DEFAULT_POST_PASTE_DELAY_MS = 500
MIN_ACTION_DELAY_MS = 0
MAX_ACTION_DELAY_MS = 5000
DEFAULT_BROWSER_PROFILE_NUMBER = 1
MIN_BROWSER_PROFILE_NUMBER = 1
MAX_BROWSER_PROFILE_NUMBER = 999
EXAMPLE_TAB_ID = "example"
SPB_TAB_ID = "spb"
MOSCOW_TAB_ID = "moscow"
DEFAULT_ACTIVE_TAB_ID = EXAMPLE_TAB_ID
WORKSPACE_TAB_SPECS: tuple[tuple[str, str], ...] = (
    (EXAMPLE_TAB_ID, "Пример"),
)
LEGACY_WORKSPACE_TAB_SPECS: tuple[tuple[str, str], ...] = (
    ("spb", "СПб"),
    ("moscow", "Москва"),
)


@dataclass(slots=True)
class WindowGeometry:
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
    maximized: bool = False

    def is_valid(self) -> bool:
        return all(
            value is not None and value > 0
            for value in (self.width, self.height)
        )


@dataclass(slots=True)
class UiScaleSettings:
    mode: str = "auto"
    delta_percent: int = 0
    percent: int = 100


@dataclass(slots=True)
class ActionDelaySettings:
    delay_ms: int = DEFAULT_ACTION_DELAY_MS
    post_paste_delay_ms: int = DEFAULT_POST_PASTE_DELAY_MS


@dataclass(slots=True)
class WorkspaceTab:
    id: str
    title: str
    categories: list[Category] = field(default_factory=list)
    expanded_category_ids: list[str] | None = None


def build_default_workspace_tabs() -> list[WorkspaceTab]:
    return [
        WorkspaceTab(id=tab_id, title=title)
        for tab_id, title in WORKSPACE_TAB_SPECS
    ]


def normalize_browser_profile_number(value: int | None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return DEFAULT_BROWSER_PROFILE_NUMBER
    return max(MIN_BROWSER_PROFILE_NUMBER, min(MAX_BROWSER_PROFILE_NUMBER, number))


def normalize_active_tab_id(value: str | None, tabs: list[WorkspaceTab] | None = None) -> str:
    valid_tab_ids = [tab.id for tab in tabs or build_default_workspace_tabs() if tab.id]
    if value in valid_tab_ids:
        return value
    return valid_tab_ids[0] if valid_tab_ids else DEFAULT_ACTIVE_TAB_ID


def _clone_workspace_tab(tab: WorkspaceTab) -> WorkspaceTab:
    return WorkspaceTab(
        id=str(tab.id or "").strip(),
        title=str(tab.title or "").strip(),
        categories=list(tab.categories),
        expanded_category_ids=(
            list(tab.expanded_category_ids)
            if tab.expanded_category_ids is not None
            else None
        ),
    )


def _looks_like_placeholder_default_tabs(tabs: list[WorkspaceTab]) -> bool:
    return _looks_like_placeholder_tabs(tabs, WORKSPACE_TAB_SPECS) or _looks_like_placeholder_tabs(
        tabs,
        LEGACY_WORKSPACE_TAB_SPECS,
    )


def _looks_like_placeholder_tabs(
    tabs: list[WorkspaceTab],
    specs: tuple[tuple[str, str], ...],
) -> bool:
    if len(tabs) != len(specs):
        return False

    for tab, (default_id, default_title) in zip(tabs, specs):
        if tab.id != default_id or tab.title != default_title:
            return False
        if tab.categories or tab.expanded_category_ids is not None:
            return False
    return True


def normalize_workspace_tabs(
    tabs: list[WorkspaceTab] | None,
    legacy_categories: list[Category] | None = None,
    legacy_expanded_category_ids: list[str] | None = None,
) -> list[WorkspaceTab]:
    normalized_tabs: list[WorkspaceTab] = []
    seen_ids: set[str] = set()
    for tab in tabs or []:
        normalized_tab = _clone_workspace_tab(tab)
        if not normalized_tab.id or not normalized_tab.title:
            continue
        if normalized_tab.id in seen_ids:
            continue
        seen_ids.add(normalized_tab.id)
        normalized_tabs.append(normalized_tab)

    migrated_legacy_categories = list(legacy_categories or [])
    migrated_legacy_expanded_ids = (
        list(legacy_expanded_category_ids)
        if legacy_expanded_category_ids is not None
        else None
    )

    if normalized_tabs:
        if _looks_like_placeholder_default_tabs(normalized_tabs):
            default_tabs = build_default_workspace_tabs()
            if migrated_legacy_categories or migrated_legacy_expanded_ids is not None:
                default_tabs[0].categories = migrated_legacy_categories
                default_tabs[0].expanded_category_ids = migrated_legacy_expanded_ids
            return default_tabs
        return normalized_tabs

    default_tabs = build_default_workspace_tabs()
    if migrated_legacy_categories or migrated_legacy_expanded_ids is not None:
        default_tabs[0].categories = migrated_legacy_categories
        default_tabs[0].expanded_category_ids = migrated_legacy_expanded_ids
    return default_tabs


@dataclass(slots=True)
class AppSettings:
    window: WindowGeometry = field(default_factory=WindowGeometry)
    ui_scale: UiScaleSettings = field(default_factory=UiScaleSettings)
    action_delay: ActionDelaySettings = field(default_factory=ActionDelaySettings)
    active_tab_id: str = DEFAULT_ACTIVE_TAB_ID
    browser_profile_number: int = DEFAULT_BROWSER_PROFILE_NUMBER
    tabs: list[WorkspaceTab] = field(default_factory=build_default_workspace_tabs)
    expanded_category_ids: list[str] | None = None
    categories: list[Category] = field(default_factory=list)
