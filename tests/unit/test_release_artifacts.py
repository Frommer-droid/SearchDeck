from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_developer_file_exists():
    assert (ROOT / "DEVELOPER.md").exists()
    assert (ROOT / "README.md").exists()
    assert (ROOT / "THIRD_PARTY_NOTICES.md").exists()
    assert (ROOT / "SOURCE_CODE_ACCESS.md").exists()
    assert (ROOT / "requirements.txt").exists()
    assert (ROOT / "requirements-dev.txt").exists()


def test_readme_contains_author_and_license_sections():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "## Автор" in readme
    assert "Frommer-droid" in readme
    assert "## Лицензия" in readme


def test_gitignore_contains_required_release_rules():
    content = (ROOT / ".gitignore").read_text(encoding="utf-8")

    for expected in (
        ".agents/",
        "*_template.pyw",
        "*_GUIDE.md",
        "SearchDeck/",
    ):
        assert expected in content


def test_release_notes_uses_required_headers_and_bom():
    release_notes = (ROOT / "RELEASE_NOTES.md").read_bytes()
    assert release_notes.startswith(b"\xef\xbb\xbf")
    text = release_notes.decode("utf-8-sig")
    assert "### ✨ Новые возможности" in text
    assert "### 🐛 Исправления ошибок" in text
    assert "### 🛠 Улучшения" in text


def test_requirements_manifest_contains_runtime_and_dev_entries():
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")

    assert "PySide6==" in runtime
    assert "-r requirements.txt" in dev
    assert "PyInstaller==" in dev
    assert "pytest==" in dev


def test_build_tools_files_are_configured():
    spec_content = (ROOT / "Build_Tools" / "SearchDeck.spec").read_text(encoding="utf-8")
    post_build_content = (ROOT / "Build_Tools" / "post_build.py").read_text(encoding="utf-8")
    compiler_content = (ROOT / "Build_Tools" / "SpecCompiler.pyw").read_text(encoding="utf-8")
    move_content = (ROOT / "00_Move.pyw").read_text(encoding="utf-8")
    setup_content = (ROOT / "00_CrRel_setup.pyw").read_text(encoding="utf-8")
    archive_content = (ROOT / "00_CrRel.pyw").read_text(encoding="utf-8")

    assert "SearchDeck" in spec_content
    assert "VERSION" in spec_content
    assert 'APP_NAME = "SearchDeck"' in post_build_content
    assert '("logo.ico", "logo.ico")' in post_build_content
    assert '("VERSION", "VERSION")' in post_build_content
    assert '("assets", "assets")' in post_build_content
    assert 'glob("*.json")' not in post_build_content
    assert "subprocess.Popen" not in post_build_content
    assert "os.startfile" not in post_build_content
    assert "build_release.py" in compiler_content
    assert 'APP_NAME = "SearchDeck"' in move_content
    assert 'DESTINATION_ROOT = Path(r"D:\\Portable_soft")' in move_content
    assert "shutil.copytree(source, destination)" in move_content
    assert "Автозапуск приложения отключен." in move_content
    assert "os.startfile" not in move_content
    assert 'APP_NAME = "SearchDeck"' in setup_content
    assert 'Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe"' in setup_content
    assert 'SetupIconFile={source}\\\\logo.ico' in setup_content
    assert 'Excludes: "*.log,settings.json"' in setup_content
    assert "Не найдена иконка приложения" in setup_content
    assert "UsePreviousAppDir=no" in setup_content
    assert "[UninstallDelete]" in setup_content
    assert "[Run]" in setup_content
    assert "skipifsilent" in setup_content
    assert "os.startfile" not in setup_content
    assert "WINRAR_PATH" in archive_content
    assert ".rar" in archive_content


def test_build_tool_templates_are_removed():
    assert not (ROOT / "Build_Tools" / "project_name.spec.template").exists()
    assert not (ROOT / "Build_Tools" / "post_build_template.py").exists()
