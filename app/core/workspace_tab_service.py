from __future__ import annotations

from copy import deepcopy

from app.models.app_settings import WorkspaceTab
from app.models.catalog import generate_id


class WorkspaceTabError(ValueError):
    """Ошибка валидации вкладки."""


class WorkspaceTabNotFoundError(LookupError):
    """Вкладка не найдена."""


class WorkspaceTabService:
    """CRUD-операции над рабочими вкладками."""

    def add_tab(self, tabs: list[WorkspaceTab], title: str) -> tuple[list[WorkspaceTab], WorkspaceTab]:
        normalized_title = self._normalize_title(title)
        self._ensure_unique_title(tabs, normalized_title)
        updated = deepcopy(tabs)
        tab = WorkspaceTab(id=generate_id(), title=normalized_title)
        updated.append(tab)
        return updated, tab

    def rename_tab(
        self,
        tabs: list[WorkspaceTab],
        tab_id: str,
        new_title: str,
    ) -> list[WorkspaceTab]:
        normalized_title = self._normalize_title(new_title)
        self._ensure_unique_title(tabs, normalized_title, ignore_id=tab_id)
        updated = deepcopy(tabs)
        tab = self._find_tab(updated, tab_id)
        tab.title = normalized_title
        return updated

    def _ensure_unique_title(
        self,
        tabs: list[WorkspaceTab],
        normalized_title: str,
        ignore_id: str | None = None,
    ) -> None:
        lowered = normalized_title.casefold()
        for tab in tabs:
            if tab.id == ignore_id:
                continue
            if tab.title.casefold() == lowered:
                raise WorkspaceTabError("Вкладка с таким названием уже существует.")

    def _find_tab(self, tabs: list[WorkspaceTab], tab_id: str) -> WorkspaceTab:
        for tab in tabs:
            if tab.id == tab_id:
                return tab
        raise WorkspaceTabNotFoundError("Вкладка не найдена.")

    @staticmethod
    def _normalize_title(value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise WorkspaceTabError("Название вкладки не может быть пустым.")
        return normalized
