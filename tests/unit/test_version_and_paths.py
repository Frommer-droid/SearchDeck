from __future__ import annotations

import sys

from app.config import app_config
from app.version import __version__


def test_version_is_read_from_root_version_file():
    assert __version__ == (app_config.project_root() / "VERSION").read_text().strip()


def test_runtime_paths_use_project_root_in_dev_mode(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert app_config.runtime_root() == app_config.project_root()
    assert app_config.settings_path() == app_config.project_root() / "settings.json"
    assert app_config.log_path() == app_config.project_root() / "searchdeck.log"
    assert app_config.asset_icon_path("arrowup.png") == (
        app_config.project_root() / "assets" / "icons" / "arrowup.png"
    )


def test_runtime_paths_switch_to_executable_directory_in_frozen_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "SearchDeck.exe"), raising=False)

    assert app_config.runtime_root() == tmp_path
    assert app_config.settings_path() == tmp_path / "settings.json"
    assert app_config.log_path() == tmp_path / "searchdeck.log"
    assert app_config.icon_path() == tmp_path / "logo.ico"
    assert app_config.asset_icon_path("arrowdown.png") == tmp_path / "assets" / "icons" / "arrowdown.png"


def test_browser_path_uses_current_user_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    assert app_config.browser_user_data_path() == tmp_path / "Local" / "Yandex" / "YandexBrowser" / "User Data"
    assert app_config.build_browser_profile_path(3) == str(app_config.browser_user_data_path() / "Profile 3")
