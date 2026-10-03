<p align="center"><img src="assets/brand/searchdeck-logo.png" width="128" alt="Иконка SearchDeck"></p>
<h1 align="center">SearchDeck</h1>
<p align="center">Частые фразы для поиска по странице — одним нажатием.</p>
<p align="center"><a href="README.en.md">English</a> · <a href="https://github.com/Frommer-droid/SearchDeck/releases/latest">Последний релиз</a></p>

SearchDeck хранит поисковые фразы как кнопки, сгруппированные по вкладкам и категориям. Нажатие активирует выбранный профиль Yandex Browser, открывает поиск по странице и вставляет фразу.

## Установка

Скачайте установщик со страницы [GitHub Releases](https://github.com/Frommer-droid/SearchDeck/releases/latest) и запустите его. При первом запуске появится пустая вкладка «Пример»: добавьте категорию и кнопки через контекстное меню.

## Возможности

- Вкладки и категории для разных наборов фраз.
- Левый клик ищет в текущей вкладке браузера; правый — в её копии.
- Ctrl + правый клик открывает меню редактирования кнопки.
- Перетаскивание кнопок и категорий, сортировка и переименование.
- Выбор профиля браузера кнопкой P1, P2 и далее.
- Настройка задержек поиска и масштаба интерфейса.
- Компактное окно поверх других окон, тема One Dark.

## Требования и настройки

Windows 10/11 x64 и Yandex Browser. Для запуска из исходников нужен Python 3.12.

Каталог браузера определяется из LOCALAPPDATA текущего пользователя. Номер профиля выбирается в приложении. Автоматизация других браузеров не заявлена.

Данные и геометрия окна сохраняются в settings.json рядом с EXE; при запуске из исходников — в корне проекта. Для этого каталог должен быть доступен на запись. Установщик не включает пользовательские настройки. [settings.example.json](settings.example.json) — нейтральный пример. Перед заменой portable-папки сохраните свой settings.json.

## Запуск из исходников

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\pythonw.exe main.py
```

## Разработка

```powershell
.\.venv\Scripts\python.exe -m ruff check . --no-cache
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe Build_Tools/build_release.py
```

Архитектура и проверки сборки описаны в [DEVELOPER.md](DEVELOPER.md), история — в [RELEASE_NOTES.md](RELEASE_NOTES.md).

## Автор

[Frommer-droid](https://github.com/Frommer-droid).

## Лицензия

Собственный код — [MIT](LICENSE). Qt/PySide6 и другие зависимости имеют отдельные лицензии: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Доступ к исходникам описан в [SOURCE_CODE_ACCESS.md](SOURCE_CODE_ACCESS.md).
