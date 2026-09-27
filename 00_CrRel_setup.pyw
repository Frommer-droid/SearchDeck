from __future__ import annotations

import ctypes
import subprocess
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


APP_NAME = "SearchDeck"
PUBLISHER = "Frommer-droid"
APP_EXE = f"{APP_NAME}.exe"


def project_root() -> Path:
    return Path(__file__).resolve().parent


def app_dir() -> Path:
    return project_root() / APP_NAME


def version() -> str:
    return (project_root() / "VERSION").read_text(encoding="utf-8").strip()


def desktop_dir() -> Path:
    if sys.platform == "win32":
        buffer = ctypes.create_unicode_buffer(32768)
        # CSIDL_DESKTOPDIRECTORY; Windows resolves redirection and shell policy.
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buffer) == 0:
            return Path(buffer.value)
    return Path.home() / "Desktop"


def fixed_drives() -> list[str]:
    drives: list[str] = []
    if sys.platform != "win32":
        return drives
    get_drive_type = ctypes.windll.kernel32.GetDriveTypeW
    for code in range(ord("A"), ord("Z") + 1):
        root = f"{chr(code)}:\\"
        if get_drive_type(root) == 3:
            drives.append(root)
    return drives


def default_install_dir() -> str:
    if Path("D:/").exists():
        return rf"D:\Apps\{APP_NAME}"
    for drive in fixed_drives():
        if not drive.upper().startswith("C:"):
            return str(Path(drive) / "Apps" / APP_NAME)
    return rf"C:\Apps\{APP_NAME}"


def find_iscc() -> Path | None:
    candidates = [
        Path(r"D:\dev\tools\Inno Setup 6\ISCC.exe"),
        Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def show_message(title: str, message: str, is_error: bool = False) -> None:
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        if is_error:
            messagebox.showerror(title, message, parent=root)
        else:
            messagebox.showinfo(title, message, parent=root)
        root.destroy()
    except tk.TclError:
        print(f"{title}: {message}")


def validate_source() -> None:
    source = app_dir()
    if not source.exists():
        raise FileNotFoundError(f"Не найдена собранная папка: {source}")
    if not (source / APP_EXE).exists():
        raise FileNotFoundError(f"Не найден исполняемый файл: {source / APP_EXE}")
    if not (source / "logo.ico").exists():
        raise FileNotFoundError(f"Не найдена иконка приложения: {source / 'logo.ico'}")
    if not (source / "VERSION").exists():
        raise FileNotFoundError(f"Не найден VERSION в собранной папке: {source / 'VERSION'}")


def create_iss_file(path: Path) -> None:
    source = app_dir()
    output_dir = desktop_dir()
    app_version = version()
    default_dir = default_install_dir()
    iss = f"""
#define AppName "{APP_NAME}"
#define AppVersion "{app_version}"
#define AppPublisher "{PUBLISHER}"
#define AppExeName "{APP_EXE}"

[Setup]
AppId={{{{B69D7D8E-6F39-46E4-9C2D-58B3E7718E34}}}}
AppName={{#AppName}}
AppVersion={{#AppVersion}}
AppPublisher={{#AppPublisher}}
DefaultDirName={default_dir}
UsePreviousAppDir=no
DefaultGroupName={{#AppName}}
DisableProgramGroupPage=yes
OutputDir={output_dir}
OutputBaseFilename={APP_NAME}_v{app_version}_Setup
SetupIconFile={source}\\logo.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={{app}}\\{{#AppExeName}}

[Files]
Source: "{source}\\*"; DestDir: "{{app}}"; Excludes: "*.log,settings.json"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{{#AppName}}"; Filename: "{{app}}\\{{#AppExeName}}"
Name: "{{autodesktop}}\\{{#AppName}}"; Filename: "{{app}}\\{{#AppExeName}}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные ярлыки:"

[Run]
Filename: "{{app}}\\{{#AppExeName}}"; Description: "Запустить SearchDeck"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{{cmd}}"; Parameters: "/C taskkill /F /IM {APP_EXE}"; Flags: runhidden; RunOnceId: "Stop{APP_NAME}"

[UninstallDelete]
Type: filesandordirs; Name: "{{app}}"
"""
    path.write_text(iss.strip() + "\n", encoding="utf-8")


def build_installer() -> Path:
    validate_source()
    iscc = find_iscc()
    if iscc is None:
        raise FileNotFoundError("Не найден Inno Setup 6 ISCC.exe")

    with tempfile.TemporaryDirectory(prefix="searchdeck_inno_") as temp_dir:
        iss_path = Path(temp_dir) / f"{APP_NAME}.iss"
        create_iss_file(iss_path)
        subprocess.run([str(iscc), str(iss_path)], check=True)

    return desktop_dir() / f"{APP_NAME}_v{version()}_Setup.exe"


def main() -> int:
    try:
        installer = build_installer()
    except Exception as error:
        show_message("Ошибка сборки установщика SearchDeck", str(error), is_error=True)
        return 1

    show_message(
        "Установщик SearchDeck готов",
        f"Создан установщик:\n{installer}\n\nАвтозапуск приложения отключен.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
