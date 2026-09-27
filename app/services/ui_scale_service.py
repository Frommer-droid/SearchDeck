from __future__ import annotations

from app.models.ui_scale import ScreenMetrics, UiScaleState


BASE_LOGICAL_DPI = 96.0
REFERENCE_WIDTH = 2560
REFERENCE_HEIGHT = 1440
MIN_AUTO_UI_SCALE_PERCENT = 70
MAX_AUTO_UI_SCALE_PERCENT = 200
AUTO_STEP = 10

MIN_FINAL_UI_SCALE_PERCENT = 35
MAX_FINAL_UI_SCALE_PERCENT = 300
FINAL_STEP = 5
MIN_MANUAL_SCALE_REFERENCE_PERCENT = 100

BASE_WINDOW_HEIGHT_PERCENT = 80
MIN_WINDOW_HEIGHT_PERCENT = 40
MAX_WINDOW_HEIGHT_PERCENT = 95
MAX_CONTENT_WINDOW_HEIGHT_PERCENT = 90


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def round_to_step(value: float, step: int) -> int:
    return int(round(value / step) * step)


def normalize_delta_percent(value: int) -> int:
    return clamp(value, -50, 50)


def calculate_auto_percent(metrics: ScreenMetrics) -> int:
    normalized_width = metrics.width * (metrics.dpi / BASE_LOGICAL_DPI)
    normalized_height = metrics.height * (metrics.dpi / BASE_LOGICAL_DPI)
    ratio = min(normalized_width / REFERENCE_WIDTH, normalized_height / REFERENCE_HEIGHT)
    raw_auto = ratio * 100
    return clamp(round_to_step(raw_auto, AUTO_STEP), MIN_AUTO_UI_SCALE_PERCENT, MAX_AUTO_UI_SCALE_PERCENT)


def calculate_final_percent(auto_percent: int, delta_percent: int) -> int:
    delta = normalize_delta_percent(delta_percent)
    delta_reference = max(auto_percent, MIN_MANUAL_SCALE_REFERENCE_PERCENT)
    raw_final = auto_percent + (delta_reference * delta / 100)
    return clamp(round_to_step(raw_final, FINAL_STEP), MIN_FINAL_UI_SCALE_PERCENT, MAX_FINAL_UI_SCALE_PERCENT)


def calculate_scale_state(metrics: ScreenMetrics, delta_percent: int) -> UiScaleState:
    auto_percent = calculate_auto_percent(metrics)
    final_percent = calculate_final_percent(auto_percent, delta_percent)
    return UiScaleState(
        auto_percent=auto_percent,
        delta_percent=normalize_delta_percent(delta_percent),
        final_percent=final_percent,
    )


def calculate_target_window_height(
    available_height: int,
    minimum_height: int,
    delta_percent: int,
) -> int:
    height_percent = clamp(
        round(BASE_WINDOW_HEIGHT_PERCENT * (1 + normalize_delta_percent(delta_percent) / 100)),
        MIN_WINDOW_HEIGHT_PERCENT,
        MAX_WINDOW_HEIGHT_PERCENT,
    )
    return clamp(round(available_height * height_percent / 100), minimum_height, available_height)


def clamp_content_window_height(
    content_height: int,
    minimum_height: int,
    available_height: int,
) -> int:
    max_height = max(
        minimum_height,
        round(available_height * MAX_CONTENT_WINDOW_HEIGHT_PERCENT / 100),
    )
    return clamp(content_height, minimum_height, max_height)
