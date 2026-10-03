from __future__ import annotations

import os
import shutil
import stat
import subprocess
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


APP_NAME = "SearchDeck"
DESTINATION_ROOT = Path(r"D:\Portable_soft")


def project_root() -> Path:
    return Path(__file__).resolve().parent


def source_dir() -> Path:
    return project_root() / APP_NAME


def destination_dir() -> Path:
    return DESTINATION_ROOT / APP_NAME


def remove_readonly(func, path, _exc_info) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError as error:
        print(f"Не удалось удалить {path}: {error}")


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


def kill_running_app(app_dir: Path) -> None:
    exe_name = f"{APP_NAME}.exe"
    ps_script = (
        "$target = [IO.Path]::GetFullPath($args[0]); "
        "Get-Process -Name $args[1] -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and [IO.Path]::GetFullPath($_.Path).StartsWith($target, [StringComparison]::OrdinalIgnoreCase) } | "
        "Stop-Process -Force"
    )
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            ps_script,
            str(app_dir),
            Path(exe_name).stem,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    time.sleep(0.5)


def copy_release_folder(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Не найдена собранная папка: {source}")
    if not (source / f"{APP_NAME}.exe").exists():
        raise FileNotFoundError(f"Не найден исполняемый файл: {source / f'{APP_NAME}.exe'}")

    if (destination.is_symlink() or destination.is_junction()
            or DESTINATION_ROOT.is_symlink() or DESTINATION_ROOT.is_junction()):
        raise RuntimeError("Portable-папка не должна быть ссылкой")
    destination = destination.resolve()
    if destination != (DESTINATION_ROOT / APP_NAME).resolve():
        raise RuntimeError("Неверный каталог portable-поставки")
    settings = destination / "settings.json"
    existing_settings = settings.read_bytes() if settings.exists() else None
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination, onerror=remove_readonly)
    shutil.copytree(source, destination)
    if existing_settings is not None:
        settings.write_bytes(existing_settings)


def main() -> int:
    src = source_dir()
    dst = destination_dir()
    print(f"Перенос {src} -> {dst}")

    try:
        kill_running_app(dst)
        copy_release_folder(src, dst)
    except Exception as error:
        show_message("Ошибка переноса SearchDeck", str(error), is_error=True)
        return 1

    show_message(
        "SearchDeck перенесен",
        f"Готовая папка обновлена:\n{dst}\n\nАвтозапуск приложения отключен.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
