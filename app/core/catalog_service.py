from __future__ import annotations

from copy import deepcopy

from app.models.catalog import ActionButton, Category, generate_id


class CatalogError(ValueError):
    """Ошибка валидации каталога."""


class CatalogNotFoundError(LookupError):
    """Сущность каталога не найдена."""


class CatalogService:
    """CRUD-операции над категориями и кнопками."""

    def add_category(self, categories: list[Category], name: str) -> tuple[list[Category], Category]:
        normalized_name = self._normalize_name(name, "Название категории не может быть пустым.")
        self._ensure_unique_category_name(categories, normalized_name)
        updated = deepcopy(categories)
        category = Category(id=generate_id(), name=normalized_name, buttons=[])
        updated.append(category)
        return updated, category

    def rename_category(
        self,
        categories: list[Category],
        category_id: str,
        new_name: str,
    ) -> list[Category]:
        normalized_name = self._normalize_name(new_name, "Название категории не может быть пустым.")
        self._ensure_unique_category_name(categories, normalized_name, ignore_id=category_id)
        updated = deepcopy(categories)
        category = self._find_category(updated, category_id)
        category.name = normalized_name
        return updated

    def delete_category(self, categories: list[Category], category_id: str) -> list[Category]:
        updated = [deepcopy(category) for category in categories if category.id != category_id]
        if len(updated) == len(categories):
            raise CatalogNotFoundError("Категория не найдена.")
        return updated

    def add_button(
        self,
        categories: list[Category],
        category_id: str,
        label: str,
        search_text: str,
    ) -> tuple[list[Category], ActionButton]:
        normalized_label = self._normalize_name(label, "Название кнопки не может быть пустым.")
        normalized_search_text = self._normalize_name(
            search_text,
            "Текст поиска не может быть пустым.",
        )
        updated = deepcopy(categories)
        category = self._find_category(updated, category_id)
        button = ActionButton(
            id=generate_id(),
            label=normalized_label,
            search_text=normalized_search_text,
        )
        category.buttons.append(button)
        return updated, button

    def update_button(
        self,
        categories: list[Category],
        category_id: str,
        button_id: str,
        label: str,
        search_text: str,
    ) -> list[Category]:
        normalized_label = self._normalize_name(label, "Название кнопки не может быть пустым.")
        normalized_search_text = self._normalize_name(
            search_text,
            "Текст поиска не может быть пустым.",
        )
        updated = deepcopy(categories)
        button = self._find_button(updated, category_id, button_id)
        button.label = normalized_label
        button.search_text = normalized_search_text
        return updated

    def delete_button(
        self,
        categories: list[Category],
        category_id: str,
        button_id: str,
    ) -> list[Category]:
        updated = deepcopy(categories)
        category = self._find_category(updated, category_id)
        buttons = [button for button in category.buttons if button.id != button_id]
        if len(buttons) == len(category.buttons):
            raise CatalogNotFoundError("Кнопка не найдена.")
        category.buttons = buttons
        return updated

    def duplicate_button(
        self,
        categories: list[Category],
        category_id: str,
        button_id: str,
    ) -> tuple[list[Category], ActionButton]:
        updated = deepcopy(categories)
        category = self._find_category(updated, category_id)
        for index, button in enumerate(category.buttons):
            if button.id != button_id:
                continue
            duplicated = ActionButton(
                id=generate_id(),
                label=button.label,
                search_text=button.search_text,
            )
            category.buttons.insert(index + 1, duplicated)
            return updated, duplicated
        raise CatalogNotFoundError("Кнопка не найдена.")

    def move_button(
        self,
        categories: list[Category],
        source_category_id: str,
        button_id: str,
        target_category_id: str,
    ) -> list[Category]:
        updated = deepcopy(categories)
        source_category = self._find_category(updated, source_category_id)
        target_category = self._find_category(updated, target_category_id)
        if source_category.id == target_category.id:
            return updated

        for index, button in enumerate(source_category.buttons):
            if button.id != button_id:
                continue
            moved_button = source_category.buttons.pop(index)
            target_category.buttons.append(moved_button)
            return updated
        raise CatalogNotFoundError("Кнопка не найдена.")

    def sort_buttons(
        self,
        categories: list[Category],
        category_id: str,
    ) -> list[Category]:
        updated = deepcopy(categories)
        category = self._find_category(updated, category_id)
        category.buttons = sorted(
            category.buttons,
            key=lambda button: button.label.casefold(),
        )
        return updated

    def sort_categories(self, categories: list[Category]) -> list[Category]:
        return sorted(
            deepcopy(categories),
            key=lambda category: category.name.casefold(),
        )

    def reorder_button(
        self,
        categories: list[Category],
        category_id: str,
        button_id: str,
        target_index: int,
    ) -> list[Category]:
        updated = deepcopy(categories)
        category = self._find_category(updated, category_id)
        source_index = next(
            (index for index, button in enumerate(category.buttons) if button.id == button_id),
            None,
        )
        if source_index is None:
            raise CatalogNotFoundError("Кнопка не найдена.")

        moved_button = category.buttons.pop(source_index)
        normalized_target_index = max(0, min(target_index, len(category.buttons) + 1))
        if source_index < normalized_target_index:
            normalized_target_index -= 1
        normalized_target_index = max(0, min(normalized_target_index, len(category.buttons)))
        category.buttons.insert(normalized_target_index, moved_button)
        return updated

    def reorder_category(
        self,
        categories: list[Category],
        category_id: str,
        target_index: int,
    ) -> list[Category]:
        updated = deepcopy(categories)
        source_index = next(
            (index for index, category in enumerate(updated) if category.id == category_id),
            None,
        )
        if source_index is None:
            raise CatalogNotFoundError("Категория не найдена.")

        moved_category = updated.pop(source_index)
        normalized_target_index = max(0, min(target_index, len(updated) + 1))
        if source_index < normalized_target_index:
            normalized_target_index -= 1
        normalized_target_index = max(0, min(normalized_target_index, len(updated)))
        updated.insert(normalized_target_index, moved_category)
        return updated

    def _ensure_unique_category_name(
        self,
        categories: list[Category],
        normalized_name: str,
        ignore_id: str | None = None,
    ) -> None:
        lowered = normalized_name.casefold()
        for category in categories:
            if category.id == ignore_id:
                continue
            if category.name.casefold() == lowered:
                raise CatalogError("Категория с таким названием уже существует.")

    def _find_category(self, categories: list[Category], category_id: str) -> Category:
        for category in categories:
            if category.id == category_id:
                return category
        raise CatalogNotFoundError("Категория не найдена.")

    def _find_button(
        self,
        categories: list[Category],
        category_id: str,
        button_id: str,
    ) -> ActionButton:
        category = self._find_category(categories, category_id)
        for button in category.buttons:
            if button.id == button_id:
                return button
        raise CatalogNotFoundError("Кнопка не найдена.")

    @staticmethod
    def _normalize_name(value: str, message: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise CatalogError(message)
        return normalized
