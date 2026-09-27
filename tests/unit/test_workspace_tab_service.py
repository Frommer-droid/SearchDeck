from __future__ import annotations

import pytest

from app.core.workspace_tab_service import (
    WorkspaceTabError,
    WorkspaceTabNotFoundError,
    WorkspaceTabService,
)
from app.models.app_settings import WorkspaceTab


def test_add_tab_appends_to_end_and_preserves_existing_order():
    service = WorkspaceTabService()
    tabs = [
        WorkspaceTab(id="tab-1", title="СПб"),
        WorkspaceTab(id="tab-2", title="Москва"),
    ]

    updated, created = service.add_tab(tabs, "Архив")

    assert [tab.title for tab in updated] == ["СПб", "Москва", "Архив"]
    assert created.title == "Архив"
    assert created.id


def test_add_tab_rejects_duplicate_title_case_insensitively():
    service = WorkspaceTabService()
    tabs = [WorkspaceTab(id="tab-1", title="Москва")]

    with pytest.raises(WorkspaceTabError):
        service.add_tab(tabs, "москва")


def test_rename_tab_updates_title():
    service = WorkspaceTabService()
    tabs = [WorkspaceTab(id="tab-1", title="Черновик")]

    updated = service.rename_tab(tabs, "tab-1", "Финал")

    assert updated[0].title == "Финал"


def test_rename_tab_raises_for_missing_tab():
    service = WorkspaceTabService()

    with pytest.raises(WorkspaceTabNotFoundError):
        service.rename_tab([], "missing", "Новая")
