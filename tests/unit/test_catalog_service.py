from __future__ import annotations

import pytest

from app.core.catalog_service import CatalogError, CatalogNotFoundError, CatalogService
from app.models.catalog import ActionButton, Category


def test_add_category_preserves_creation_order():
    service = CatalogService()
    categories = [Category(id="cat-1", name="Первая")]

    updated, category = service.add_category(categories, "Вторая")

    assert [item.name for item in updated] == ["Первая", "Вторая"]
    assert category.name == "Вторая"


def test_add_category_rejects_empty_name():
    service = CatalogService()

    with pytest.raises(CatalogError):
        service.add_category([], " ")


def test_add_category_rejects_duplicate_name_case_insensitive():
    service = CatalogService()
    categories = [Category(id="cat-1", name="Документы")]

    with pytest.raises(CatalogError):
        service.add_category(categories, "документы")


def test_rename_category_updates_name():
    service = CatalogService()
    categories = [Category(id="cat-1", name="Черновик")]

    updated = service.rename_category(categories, "cat-1", "Финал")

    assert updated[0].name == "Финал"


def test_delete_category_removes_nested_buttons():
    service = CatalogService()
    categories = [
        Category(
            id="cat-1",
            name="Документы",
            buttons=[ActionButton(id="btn-1", label="ИНН", search_text="ИНН")],
        )
    ]

    updated = service.delete_category(categories, "cat-1")

    assert updated == []


def test_add_button_requires_non_empty_fields():
    service = CatalogService()
    categories = [Category(id="cat-1", name="Документы")]

    with pytest.raises(CatalogError):
        service.add_button(categories, "cat-1", " ", "ИНН")
    with pytest.raises(CatalogError):
        service.add_button(categories, "cat-1", "ИНН", " ")


def test_add_update_and_delete_button():
    service = CatalogService()
    categories = [Category(id="cat-1", name="Документы")]

    categories, button = service.add_button(categories, "cat-1", "ИНН", "Идентификационный номер")
    categories = service.update_button(categories, "cat-1", button.id, "ИНН РФ", "Идентификатор")
    categories = service.delete_button(categories, "cat-1", button.id)

    assert categories[0].buttons == []


def test_duplicate_button_creates_new_id_and_preserves_order():
    service = CatalogService()
    categories = [
        Category(
            id="cat-1",
            name="Документы",
            buttons=[
                ActionButton(id="btn-1", label="ИНН", search_text="ИНН"),
                ActionButton(id="btn-2", label="СНИЛС", search_text="СНИЛС"),
            ],
        )
    ]

    updated, duplicated = service.duplicate_button(categories, "cat-1", "btn-1")

    assert duplicated.id != "btn-1"
    assert duplicated.label == "ИНН"
    assert duplicated.search_text == "ИНН"
    assert [button.label for button in updated[0].buttons] == ["ИНН", "ИНН", "СНИЛС"]


def test_move_button_transfers_to_another_category_and_preserves_payload():
    service = CatalogService()
    categories = [
        Category(
            id="cat-1",
            name="Документы",
            buttons=[
                ActionButton(id="btn-1", label="ИНН", search_text="ИНН"),
                ActionButton(id="btn-2", label="СНИЛС", search_text="СНИЛС"),
            ],
        ),
        Category(
            id="cat-2",
            name="Пациенты",
            buttons=[ActionButton(id="btn-3", label="ФИО", search_text="ФИО")],
        ),
    ]

    updated = service.move_button(categories, "cat-1", "btn-1", "cat-2")

    assert [button.id for button in updated[0].buttons] == ["btn-2"]
    assert [button.id for button in updated[1].buttons] == ["btn-3", "btn-1"]
    assert updated[1].buttons[-1].label == "ИНН"
    assert updated[1].buttons[-1].search_text == "ИНН"


def test_move_button_to_same_category_keeps_catalog_unchanged():
    service = CatalogService()
    categories = [
        Category(
            id="cat-1",
            name="Документы",
            buttons=[ActionButton(id="btn-1", label="ИНН", search_text="ИНН")],
        )
    ]

    updated = service.move_button(categories, "cat-1", "btn-1", "cat-1")

    assert updated == categories


def test_move_button_raises_for_missing_target_category():
    service = CatalogService()
    categories = [
        Category(
            id="cat-1",
            name="Документы",
            buttons=[ActionButton(id="btn-1", label="ИНН", search_text="ИНН")],
        )
    ]

    with pytest.raises(CatalogNotFoundError):
        service.move_button(categories, "cat-1", "btn-1", "missing")


def test_delete_unknown_category_raises():
    service = CatalogService()

    with pytest.raises(CatalogNotFoundError):
        service.delete_category([], "missing")


def test_sort_buttons_orders_buttons_alphabetically():
    service = CatalogService()
    categories = [
        Category(
            id="cat-1",
            name="Документы",
            buttons=[
                ActionButton(id="btn-1", label="Ярлык", search_text="1"),
                ActionButton(id="btn-2", label="анализы", search_text="2"),
                ActionButton(id="btn-3", label="Бланк", search_text="3"),
            ],
        )
    ]

    updated = service.sort_buttons(categories, "cat-1")

    assert [button.label for button in updated[0].buttons] == ["анализы", "Бланк", "Ярлык"]


def test_sort_categories_orders_categories_alphabetically():
    service = CatalogService()
    categories = [
        Category(id="cat-1", name="Ярлык"),
        Category(id="cat-2", name="анализы"),
        Category(id="cat-3", name="Бланк"),
    ]

    updated = service.sort_categories(categories)

    assert [category.name for category in updated] == ["анализы", "Бланк", "Ярлык"]


def test_reorder_button_moves_item_within_same_category():
    service = CatalogService()
    categories = [
        Category(
            id="cat-1",
            name="Документы",
            buttons=[
                ActionButton(id="btn-1", label="ИНН", search_text="ИНН"),
                ActionButton(id="btn-2", label="СНИЛС", search_text="СНИЛС"),
                ActionButton(id="btn-3", label="Паспорт", search_text="Паспорт"),
            ],
        )
    ]

    updated = service.reorder_button(categories, "cat-1", "btn-3", 0)

    assert [button.id for button in updated[0].buttons] == ["btn-3", "btn-1", "btn-2"]


def test_reorder_category_moves_item_within_list():
    service = CatalogService()
    categories = [
        Category(id="cat-1", name="Документы"),
        Category(id="cat-2", name="Пациенты"),
        Category(id="cat-3", name="Архив"),
    ]

    updated = service.reorder_category(categories, "cat-3", 0)

    assert [category.id for category in updated] == ["cat-3", "cat-1", "cat-2"]
