from __future__ import annotations

from app.models.ui_scale import ScreenMetrics
from app.services.ui_scale_service import (
    calculate_auto_percent,
    calculate_final_percent,
    calculate_scale_state,
    calculate_target_window_height,
)


def test_calculate_auto_percent_uses_reference_resolution():
    metrics = ScreenMetrics(width=2560, height=1440, dpi=96.0)

    assert calculate_auto_percent(metrics) == 100


def test_calculate_final_percent_applies_delta_and_rounding():
    assert calculate_final_percent(100, 13) == 115


def test_calculate_final_percent_uses_minimum_manual_reference():
    assert calculate_final_percent(70, 50) == 120


def test_calculate_target_window_height_uses_delta_limits():
    assert calculate_target_window_height(1000, 400, 50) == 950


def test_calculate_scale_state_normalizes_delta():
    state = calculate_scale_state(ScreenMetrics(width=2560, height=1440, dpi=96), 80)

    assert state.delta_percent == 50
