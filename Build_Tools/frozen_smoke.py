"""Изолированная проверка GUI/native runtime без настроек владельца."""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

import main
from app.config.app_config import runtime_root
from app.core.catalog_service import CatalogService
from app.models.app_settings import AppSettings
from app.models.catalog import ActionButton, Category
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow
from app.ui.dialogs import SettingsDialog
from app.ui.theme import apply_theme
from app.version import __version__


def run() -> None:
    app = QApplication([])
    # Windows offscreen не перечисляет системные шрифты автоматически.
    for name in ("tahoma.ttf", "tahomabd.ttf"):
        font = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts" / name
        if font.exists():
            QFontDatabase.addApplicationFont(str(font))
    apply_theme(app)
    main._install_qt_translator(app)
    root = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else runtime_root()
    icon = QIcon(str(root / "logo.ico"))
    assert not icon.isNull(), "App icon could not be loaded"
    app.setWindowIcon(icon)
    with tempfile.TemporaryDirectory(prefix="searchdeck-smoke-") as temporary:
        window = MainWindow(
            SettingsService(Path(temporary) / "settings.json"), CatalogService(), None,
            AppSettings(categories=[Category("example", "Пример", [
                ActionButton("example", "Поиск", "пример")])]), logging.getLogger("smoke"),
        )
        window.show()
        app.processEvents()
        assert not window.grab().isNull()
        assert not window.windowIcon().isNull()
        assert "#282C34" in window.styleSheet()
        screenshot = os.environ.get("SEARCHDECK_SCREENSHOT")
        if screenshot:
            assert window.grab().save(screenshot)
        dialog = SettingsDialog(parent=window)
        dialog.show()
        app.processEvents()
        assert not dialog.grab().isNull()
        dialog.close()
        window.close()
        app.processEvents()
    print(json.dumps({"status": "ok", "version": __version__,
                      "frozen": bool(getattr(sys, "frozen", False)),
                      "icon": True, "window_rendered": True}), flush=True)


if __name__ == "__main__":
    run()
