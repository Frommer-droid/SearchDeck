from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.config.app_config import (
    APP_NAME,
    APP_USER_MODEL_ID,
    ORGANIZATION_NAME,
    TARGET_BROWSER_PROCESS,
    TARGET_BROWSER_PROFILE_PATH,
    WINDOW_TITLE,
    icon_path,
    log_path,
    settings_path,
)
from app.core.catalog_service import CatalogService
from app.core.find_action_service import FindActionService
from app.services.clipboard_service import QtClipboardBridge
from app.services.logging_service import SessionLogManager
from app.services.scancode_sender import ScancodeKeyboardSender
from app.services.settings_service import SettingsService
from app.services.window_locator import BrowserWindowLocator, WindowActivator
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def _install_qt_translator(app: QApplication) -> None:
    translator = QTranslator(app)
    translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(QLocale("ru_RU"), "qtbase", "_", translations_path):
        app.installTranslator(translator)
        app._searchdeck_qt_translator = translator  # type: ignore[attr-defined]


def main() -> int:
    _set_windows_app_id()

    app = QApplication(sys.argv)
    apply_theme(app)
    _install_qt_translator(app)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setWindowIcon(QIcon(str(icon_path())))

    log_manager = SessionLogManager(log_path())
    logger = log_manager.logger
    logger.info("Запуск приложения %s", APP_NAME)

    settings_service = SettingsService(settings_path(), logger=logger)
    settings = settings_service.load()

    window = MainWindow(
        settings_service=settings_service,
        catalog_service=CatalogService(),
        find_action_service=FindActionService(
            locator=BrowserWindowLocator(
                process_name=TARGET_BROWSER_PROCESS,
                profile_path=TARGET_BROWSER_PROFILE_PATH,
            ),
            activator=WindowActivator(),
            clipboard=QtClipboardBridge(),
            keyboard=ScancodeKeyboardSender(),
        ),
        initial_settings=settings,
        logger=logger,
    )
    window.setWindowTitle(WINDOW_TITLE)
    window.show()

    exit_code = app.exec()
    logger.info("Завершение приложения %s", APP_NAME)
    log_manager.shutdown()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
