from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


def generate_id() -> str:
    return uuid4().hex


@dataclass(slots=True)
class ActionButton:
    id: str
    label: str
    search_text: str


@dataclass(slots=True)
class Category:
    id: str
    name: str
    buttons: list[ActionButton] = field(default_factory=list)
