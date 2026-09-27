from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


from app.ui.theme import THEME_COLORS, build_global_stylesheet


@dataclass(slots=True, frozen=True)
class ThemeMetrics:
    font_pt: int
    small_font_pt: int
    spacing: int
    radius: int
    control_height: int
    small_control_height: int
    action_button_height: int
    title_bar_height: int
    sidebar_width: int
    minimum_width: int
    minimum_height: int


def _scale(value: int, scale_factor: float) -> int:
    return max(1, round(value * scale_factor))


def build_theme_metrics(scale_factor: float) -> ThemeMetrics:
    return ThemeMetrics(
        font_pt=max(9, round(12 * scale_factor)),
        small_font_pt=max(8, round(10 * scale_factor)),
        spacing=_scale(6, scale_factor),
        radius=_scale(8, scale_factor),
        control_height=_scale(32, scale_factor),
        small_control_height=_scale(26, scale_factor),
        action_button_height=_scale(32, scale_factor),
        title_bar_height=_scale(26, scale_factor),
        sidebar_width=_scale(330, scale_factor),
        minimum_width=_scale(300, scale_factor),
        minimum_height=_scale(240, scale_factor),
    )


def build_stylesheet(metrics: ThemeMetrics, icon_dir: Path | None = None) -> str:
    # Дополнение эталонного ядра: только специфичные элементы SearchDeck.
    c = THEME_COLORS
    scale = metrics.control_height / 32
    core = build_global_stylesheet(c, scale_factor=scale, base_font_size=12)
    radius = min(10, max(6, metrics.radius))
    up = (icon_dir / "arrowup.png").as_posix() if icon_dir else ""
    down = (icon_dir / "arrowdown.png").as_posix() if icon_dir else ""
    return core + f"""
    QWidget#panelRoot {{ border: 1px solid {c['border']}; border-radius: {radius}px; }}
    QWidget#topBar {{ background: {c['surface']}; border-radius: {radius}px; }}
    QLabel#accentLabel {{ color: {c['accent']}; font-weight: 700; }}
    QLabel#emptyCategoryLabel {{ color: {c['muted']}; padding: {metrics.spacing}px; }}
    QTabBar#workspaceTabBar {{ background: transparent; }}
    QTabBar#workspaceTabBar::tab {{
        background: {c['surface']}; color: {c['text_strong']};
        border: 1px solid {c['border']}; border-bottom: none;
        border-top-left-radius: {radius}px; border-top-right-radius: {radius}px;
        min-height: {metrics.control_height}px; padding: 0 {metrics.spacing + 4}px;
        margin-right: 2px; font-weight: 700;
    }}
    QTabBar#workspaceTabBar::tab:selected {{ background: {c['accent']}; color: {c['on_accent']}; }}
    QTabBar#workspaceTabBar::tab:hover:!selected {{ background: {c['surface_hover']}; }}
    QTabBar#workspaceTabBar::tab:disabled {{ background: {c['disabled_background']}; color: {c['disabled_text']}; }}
    QPushButton#browserProfileButton {{
        min-height: {metrics.title_bar_height}px; max-height: {metrics.title_bar_height}px;
        min-width: {metrics.title_bar_height + 18}px; padding: 0 {metrics.spacing}px;
        font-size: {metrics.small_font_pt}pt;
    }}
    QToolButton#categoryHeader {{
        text-align: left; padding: 0 {metrics.spacing}px;
        min-height: {metrics.control_height}px; border-radius: {radius}px;
        background: {c['surface_hover']}; color: {c['text_strong']};
    }}
    QToolButton#categoryHeader:hover {{ background: {c['primary_hover']}; }}
    QToolButton#categoryHeader:checked {{ background: {c['primary']}; }}
    QToolButton#categoryHeader:pressed {{ background: {c['surface_pressed']}; }}
    QToolButton#categoryHeader:disabled {{ background: {c['disabled_background']}; color: {c['disabled_text']}; }}
    QPushButton#actionButton {{
        text-align: left; font-weight: 700; min-height: {metrics.action_button_height}px;
        background: {c['accent']}; color: {c['on_accent']};
    }}
    QPushButton#actionButton:hover {{ background: {c['accent_hover']}; }}
    QPushButton#actionButton:checked {{ background: {c['accent_pressed']}; }}
    QPushButton#actionButton:pressed {{ background: {c['accent_pressed']}; }}
    QPushButton#actionButton:disabled {{ background: {c['disabled_background']}; color: {c['disabled_text']}; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width: {max(28, metrics.control_height)}px; }}
    QSpinBox {{ padding-right: {max(28, metrics.control_height) + metrics.spacing}px; }}
    QSpinBox::up-arrow {{ image: url({up}); width: 9px; height: 6px; }}
    QSpinBox::down-arrow {{ image: url({down}); width: 9px; height: 6px; }}
    QFrame#dropIndicator {{ background: {c['accent']}; border: none; }}
    QWidget#categoryBody, QScrollArea {{ background: transparent; border: none; }}
    QSpinBox {{
        background: {c['surface_alt']}; color: {c['text_strong']};
        border: 1px solid {c['border']}; border-radius: {radius}px;
        min-height: {metrics.control_height}px;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        background: {c['surface_hover']}; border-left: 1px solid {c['border']};
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: {c['primary_hover']}; }}
    QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{ background: {c['surface_pressed']}; }}
    QSpinBox::up-button:disabled, QSpinBox::down-button:disabled {{ background: {c['disabled_background']}; }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ border-color: {c['primary_hover']}; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {c['focus']}; }}
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QPlainTextEdit:disabled {{
        color: {c['disabled_text']}; background: {c['disabled_background']}; border-color: {c['disabled_border']};
    }}
    QPushButton:checked {{ background: {c['primary']}; }}
    QMenu::item:disabled {{ color: {c['disabled_text']}; }}
    QCheckBox::indicator:hover {{ border-color: {c['focus']}; }}
    QCheckBox::indicator:pressed {{ background: {c['surface_pressed']}; }}
    QCheckBox:disabled {{ color: {c['disabled_text']}; }}
    QCheckBox::indicator:disabled {{ background: {c['disabled_background']}; border-color: {c['disabled_border']}; }}
    QScrollBar::handle:vertical:hover {{ background: {c['accent_hover']}; }}
    QScrollBar::handle:vertical:pressed {{ background: {c['accent_pressed']}; }}
    """
