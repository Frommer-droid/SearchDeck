# Разработка SearchDeck

Python 3.12, PySide6 6.10.2, Windows 10/11 x64. Все команды выполняются из корня с проектной .venv. Полное проверенное окружение зафиксировано в requirements-lock.txt и подключается из requirements-dev.txt.

## Архитектура

main.py создаёт QApplication, применяет One Dark, русскую Qt-локализацию и связывает сервисы с MainWindow. app/core содержит сценарии поиска и CRUD, app/models — состояние, app/services — persistence, clipboard, WinAPI и локатор браузера. UI расположен в app/ui; эталон темы — в app/ui/theme, дополнения приложения и существующие масштабные метрики — в app/config/theme.py.

Каталог Yandex User Data вычисляется из LOCALAPPDATA текущего пользователя. Номер профиля сохраняется в settings.json. При изменении масштаба пересчитываются шрифты, размеры и QSS; кнопки сохраняют ширину не меньше высоты.

settings.json — локальный файл, исключён из Git. Формат не менялся; пример settings.example.json создаётся сериализатором SettingsService. При первом запуске без настроек используется пустая вкладка «Пример».

## Окружение и проверки

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m ruff check . --no-cache
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
osv-scanner -r .
```

VS Code: открыть корень, выбрать .venv/Scripts/python.exe. launch.json закрепляет этот interpreter; состояние Pylance проверяется в IDE отдельно.

## Сборка и проверки DLL

```powershell
.\.venv\Scripts\python.exe Build_Tools/build_release.py
```

CLI требует проектную .venv. До PyInstaller удаляет точно определённые старые SearchDeck, Build_Tools/build и Build_Tools/dist; сохраните нужные данные до запуска. settings.json из старой сборки сохраняется в игнорируемый Build_Tools/verification/previous-build-settings.json. GUI SpecCompiler делегирует сборку этому CLI.

PATH полностью заменяется списком PySide6, shiboken6, .venv/Scripts, выбранного Python, его DLLs и System32. native_policy.py проверяет все источники Analysis.binaries; посторонний источник прерывает сборку. Полный комплект concrt140, msvcp140*, vcruntime140* берётся из PySide6, версии обязаны совпадать. Доверенные старые Python runtime заменяются на Qt runtime только после проверки всех исходных записей.

Собираются основное приложение и консольный SearchDeckSmoke тем же spec и DLL policy. До post-build проверяются COLLECT-00.toc, MSVC SHA256 и версии. Изолированный smoke импортирует main/GUI/native сервисы, создаёт и рисует окно offscreen с временными настройками, проверяет иконку, stdout/stderr и exit code; timeout 30 секунд.

Доказательства сохраняются в Build_Tools/verification: TOC обеих сборок, build logs и native-verification.json. Эта папка исключена из Git. Work/build и smoke-поставка удаляются только после последних проверок; отчёты сохраняются для handoff.

post_build.py создаёт корневую SearchDeck, копирует только явный список документации/ресурсов и создаёт SHA256SUMS.json. Локальный settings.json в чистую поставку не копируется. EXE содержит version resource из VERSION. Автозапуска приложения нет.

## Installer и portable

00_CrRel_setup.pyw создаёт SearchDeck_vX.Y.Z_Setup.exe на Desktop с Inno Setup. settings.json и логи исключены; запуск после установки предлагается отдельной галочкой и пропускается при тихой установке. Основной компилятор этой машины — установленный Inno Setup 6; далее проверяются стандартные пути.

Для автоматизации без GUI импортируйте build_installer() из этого скрипта. Для ручного запуска используйте .venv/Scripts/pythonw.exe. Установка предлагает D:/Apps/SearchDeck, затем другой fixed drive, затем C:/Apps/SearchDeck. UsePreviousAppDir=no. Деинсталляция завершает приложение и удаляет каталог установки.

00_Move.pyw обновляет portable-поставку, сохраняя существующий settings.json целевой папки. Пользовательские настройки имеют приоритет над чистой поставкой. Скрипт не запускает приложение. Архив 00_CrRel.pyw создаётся только по прямой просьбе.

## Релиз

Версия — в VERSION, заметки — в RELEASE_NOTES.md. После тестов фиксируются локальные release commit, vX.Y.Z и очередной числовой tag. Перед отправкой выполняется private backup и штатный orphan dry-run. Боевой push и изменение видимости требуют отдельного подтверждения после предъявления готового результата. Старые assets и релизы сохраняются, если их удаление не поручено отдельно.

Карточка ShareMyApp использует только подтверждённый GitHub Release и asset. Версия 0.5.1 опубликована; карточка синхронизирована с ней. CI выполняет lint, тесты offscreen и безопасную Windows-сборку.

## Компилятор установщика

Для нестандартного расположения Inno Setup задайте INNO_SETUP_ISCC полным путём к ISCC.exe. Иначе используются стандартные каталоги установки и доступный компилятор из PATH.
