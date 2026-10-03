from __future__ import annotations

import os
import sys
from pathlib import Path

from app.models.app_settings import (
    DEFAULT_BROWSER_PROFILE_NUMBER,
    normalize_browser_profile_number,
)
from app.version import __version__

APP_NAME = "SearchDeck"
APP_USER_MODEL_ID = "frommer.searchdeck.searchdeck.1"
ORGANIZATION_NAME = "Frommer"

TARGET_BROWSER_PROCESS = "browser.exe"
def browser_user_data_path() -> Path:
    """Каталог браузера текущего пользователя, без привязки к владельцу."""
    local_app_data = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return local_app_data / "Yandex" / "YandexBrowser" / "User Data"


TARGET_BROWSER_USER_DATA_PATH = browser_user_data_path()


def build_browser_profile_path(profile_number: int) -> str:
    normalized_number = normalize_browser_profile_number(profile_number)
    return str(browser_user_data_path() / f"Profile {normalized_number}")


TARGET_BROWSER_PROFILE_PATH = build_browser_profile_path(DEFAULT_BROWSER_PROFILE_NUMBER)

SETTINGS_FILE_NAME = "settings.json"
LOG_FILE_NAME = "searchdeck.log"
WINDOW_TITLE = f"{APP_NAME} v{__version__}"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return project_root()


def settings_path() -> Path:
    return runtime_root() / SETTINGS_FILE_NAME


def log_path() -> Path:
    return runtime_root() / LOG_FILE_NAME


def icon_path() -> Path:
    return runtime_root() / "logo.ico"


def asset_icon_path(file_name: str) -> Path:
    return runtime_root() / "assets" / "icons" / file_name
