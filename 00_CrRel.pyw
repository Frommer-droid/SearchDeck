import shutil
import os
import time
import subprocess
import tkinter as tk
import stat

# =================================================================================
# �️ НАСТРОЙКИ (ИЗМЕНИТЕ ТОЛЬКО ЭТУ СЕКЦИЮ)
# =================================================================================

# 1. Имя вашего приложения
# ВАЖНО: Замените "REPLACE_WITH_APP_NAME" на точное имя папки/проекта.
APP_NAME = "SearchDeck"

# =================================================================================
# 🚀 АВТОМАТИКА (НЕ МЕНЯЙТЕ НИЧЕГО НИЖЕ, ЕСЛИ НЕ УВЕРЕНЫ)
# =================================================================================

# Путь к архиватору WinRAR
WINRAR_PATH = r"C:\Program Files\WinRAR\WinRAR.exe"

# Папки
PORTABLE_SOFT_DIR = r"D:\Portable_soft"
DESKTOP_DIR = r"D:\Desktop"

# Автоматическое определение путей
SOURCE_DIR = os.path.join(PORTABLE_SOFT_DIR, APP_NAME)
WORK_DIR = os.path.join(DESKTOP_DIR, APP_NAME)
EXE_NAME = f"{APP_NAME}.exe"

def kill_process_smart(process_name, path_filter=None):
    """
    Завершает процесс.
    Если передан path_filter, убивает только тот процесс, который запущен из указанной папки.
    Если path_filter=None, убивает все процессы с таким именем.
    """
    print(f"--- Проверка и завершение процесса: {process_name} ---")
    
    process_name_no_ext = process_name.replace(".exe", "")
    
    # Попытка убить процесс несколько раз для надежности
    for i in range(3):
        if path_filter:
            # PowerShell: Найти -> Проверить путь -> Убить
            ps_command = (
                f"powershell -Command \"Get-Process -Name '{process_name_no_ext}' -ErrorAction SilentlyContinue | "
                f"Where-Object {{$_.Path -match '{path_filter}'}} | "
                f"Stop-Process -Force\""
            )
            try:
                subprocess.run(ps_command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        else:
            # Просто убить по имени
            try:
                subprocess.run(f"taskkill /F /IM {process_name}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        
        time.sleep(0.5) # Небольшая пауза между попытками
    
    print("Команда завершения отправлена (если процесс был).")

def remove_readonly(func, path, _):
    """Обработчик ошибок для удаления файлов с атрибутом 'Только чтение'."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        print(f"Не удалось удалить {path}: {e}")

def show_popup(message, is_error=False):
    """Показывает всплывающее окно."""
    try:
        root = tk.Tk()
        root.attributes("-topmost", True)
        
        if is_error:
            root.title("Ошибка")
            bg_color = '#ffcccc'
        else:
            root.overrideredirect(True)
            bg_color = '#e6ffe6'
        
        root.configure(bg=bg_color) 

        width = 500 if is_error else 400
        height = 200 if is_error else 150
        
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        
        root.geometry(f"{width}x{height}+{x}+{y}")

        label = tk.Label(root, text=message, font=("Arial", 12), bg=bg_color, wraplength=width-20)
        label.pack(expand=True, padx=20, pady=20)

        if is_error:
            btn = tk.Button(root, text="Закрыть", command=root.destroy, font=("Arial", 10, "bold"))
            btn.pack(pady=10)
        else:
            root.after(3000, root.destroy)
            root.bind("<Button-1>", lambda e: root.destroy())
            label.bind("<Button-1>", lambda e: root.destroy())

        root.mainloop()
    except Exception as e:
        print(f"Не удалось показать окно: {e}")


def ask_app_name_dialog(title, prompt):
    """Запрашивает имя приложения с явной поддержкой буфера обмена."""
    result = {"value": None}

    root = tk.Tk()
    root.title(title)
    root.attributes("-topmost", True)
    root.resizable(False, False)

    frame = tk.Frame(root, padx=16, pady=14)
    frame.pack(fill="both", expand=True)

    label = tk.Label(frame, text=prompt, justify="left", anchor="w", wraplength=420)
    label.pack(fill="x", pady=(0, 10))

    entry = tk.Entry(frame, width=48)
    entry.pack(fill="x", pady=(0, 12))

    buttons = tk.Frame(frame)
    buttons.pack(fill="x")

    def close_with(value):
        result["value"] = value
        root.destroy()

    def on_ok(event=None):
        close_with(entry.get())

    def on_cancel(event=None):
        close_with(None)

    def replace_selection(text):
        try:
            start = entry.index("sel.first")
            end = entry.index("sel.last")
            entry.delete(start, end)
            entry.insert(start, text)
        except tk.TclError:
            entry.insert(tk.INSERT, text)

    def on_paste(event=None):
        try:
            clipboard_text = root.clipboard_get()
        except tk.TclError:
            return "break"
        replace_selection(clipboard_text)
        return "break"

    def on_copy(event=None):
        try:
            selected_text = entry.selection_get()
        except tk.TclError:
            return "break"
        root.clipboard_clear()
        root.clipboard_append(selected_text)
        return "break"

    def on_cut(event=None):
        on_copy()
        try:
            entry.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        return "break"

    def on_control_key(event):
        # Фолбэк для раскладок, где Tk не распознаёт Ctrl+V/C/X как латиницу.
        if event.keycode == 86:
            return on_paste()
        if event.keycode == 67:
            return on_copy()
        if event.keycode == 88:
            return on_cut()
        return None

    for sequence in ("<Control-v>", "<Control-V>", "<Control-Insert>", "<Shift-Insert>", "<<Paste>>"):
        entry.bind(sequence, on_paste)
    for sequence in ("<Control-c>", "<Control-C>", "<<Copy>>"):
        entry.bind(sequence, on_copy)
    for sequence in ("<Control-x>", "<Control-X>", "<<Cut>>"):
        entry.bind(sequence, on_cut)
    entry.bind("<Control-KeyPress>", on_control_key, add="+")
    entry.bind("<Return>", on_ok)
    entry.bind("<Escape>", on_cancel)

    ok_btn = tk.Button(buttons, text="OK", width=10, command=on_ok)
    ok_btn.pack(side="right", padx=(8, 0))
    cancel_btn = tk.Button(buttons, text="Отмена", width=10, command=on_cancel)
    cancel_btn.pack(side="right")

    root.protocol("WM_DELETE_WINDOW", on_cancel)
    root.update_idletasks()
    width = max(460, root.winfo_reqwidth())
    height = root.winfo_reqheight()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.lift()
    root.focus_force()
    entry.focus_set()
    root.mainloop()
    return result["value"]

def prepare_release_folder(source, destination):
    """
    Подготавливает папку для релиза:
    1. Полное копирование исходной папки.
    2. Удаление всех папок, кроме _internal.
    3. Удаление .log и .json файлов в корне.
    """
    print(f"--- Подготовка релиза из {source} ---")
    
    # 1. Полное копирование
    if os.path.exists(destination):
        try:
            shutil.rmtree(destination, onerror=remove_readonly)
        except Exception:
            pass
            
    print(f"Копирование всех файлов в {destination}...")
    try:
        shutil.copytree(source, destination)
    except Exception as e:
        print(f"Ошибка копирования: {e}")
        return False

    # 2. Очистка
    print("Очистка лишних файлов и папок...")
    for item in os.listdir(destination):
        item_path = os.path.join(destination, item)
        
        if os.path.isdir(item_path):
            # Удаляем все папки кроме _internal
            if item.lower() != "_internal":
                try:
                    shutil.rmtree(item_path, onerror=remove_readonly)
                    print(f"Удалена папка: {item}")
                except Exception:
                    subprocess.run(f'rmdir /s /q "{item_path}"', shell=True)
            else:
                print(f"Оставлена папка: {item}")
                
        else:
            # Удаляем .log и .json в корне
            if item.lower().endswith(('.log', '.json')):
                try:
                    os.remove(item_path)
                    print(f"Удален файл: {item}")
                except Exception:
                    pass
            else:
                print(f"Оставлен файл: {item}")
    return True

def main():
    global APP_NAME, SOURCE_DIR, WORK_DIR, EXE_NAME
    
    # --- Интерактивная настройка ---
    if "REPLACE_WITH" in APP_NAME:
        print("Скрипт не настроен. Запрос имени приложения...")
        new_name = ask_app_name_dialog(
            "Настройка скрипта релиза",
            "Введите имя приложения (имя папки в Portable_soft):\nНапример: MySuperApp",
        )
        
        if new_name and new_name.strip():
            try:
                with open(__file__, 'r', encoding='utf-8') as f:
                    content = f.read()
                new_content = content.replace('APP_NAME = "REPLACE_WITH_APP_NAME"', f'APP_NAME = "{new_name}"')
                with open(__file__, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(">>> Скрипт настроен и сохранен!")
                show_popup(f"Скрипт настроен для '{new_name}'!\nЗапустите его еще раз для создания релиза.")
                return
            except Exception as e:
                show_popup(f"Ошибка настройки: {e}", is_error=True)
                return
        else:
            return

    print("--- Начало создания релиза ---")

    # 1. Проверки
    if not os.path.exists(WINRAR_PATH):
        show_popup(f"Не найден WinRAR:\n{WINRAR_PATH}", is_error=True)
        return
        
    if not os.path.exists(SOURCE_DIR):
        show_popup(f"Исходная папка не найдена:\n{SOURCE_DIR}", is_error=True)
        return

    # 2. Завершение процесса
    kill_process_smart(EXE_NAME, path_filter=PORTABLE_SOFT_DIR)
    time.sleep(1)

    # 3. Подготовка папки (Копирование -> Очистка)
    if not prepare_release_folder(SOURCE_DIR, WORK_DIR):
        show_popup("Ошибка при подготовке файлов!", is_error=True)
        return

    # 4. Получение версии (если есть файл VERSION рядом со скриптом)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(script_dir, "VERSION")
    version = "0.0.0"
    if os.path.exists(version_file):
        with open(version_file, 'r', encoding='utf-8') as f:
            version = f.read().strip()

    # 7. Архивация
    rar_name = f"{APP_NAME}_v{version}.rar"
    rar_path = os.path.join(DESKTOP_DIR, rar_name)
    print(f"Создание архива: {rar_path}")
    
    # WinRAR команда: a (add), -r (recursive), -ep1 (exclude base dir path)
    # Теперь, когда папка очищена, мы просто архивируем всё содержимое
    cmd = [WINRAR_PATH, 'a', '-r', '-ep1', rar_path, os.path.join(WORK_DIR, '*')]
    
    try:
        # Запускаем из рабочей папки
        subprocess.run(cmd, cwd=WORK_DIR, check=True)
        print("Архив создан успешно.")
    except subprocess.CalledProcessError as e:
        show_popup(f"Ошибка WinRAR:\n{e}", is_error=True)
        return

    # 8. Финальная уборка
    print("Удаление временных файлов...")
    try:
        shutil.rmtree(WORK_DIR, onerror=remove_readonly)
    except Exception:
        subprocess.run(f'rmdir /s /q "{WORK_DIR}"', shell=True)

    show_popup(f"Релиз готов!\n{rar_name}")

if __name__ == "__main__":
    main()
