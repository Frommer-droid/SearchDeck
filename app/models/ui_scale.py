from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ScreenMetrics:
    width: int
    height: int
    dpi: float


@dataclass(slots=True, frozen=True)
class UiScaleState:
    auto_percent: int
    delta_percent: int
    final_percent: int

    @property
    def scale_factor(self) -> float:
        return self.final_percent / 100.0
