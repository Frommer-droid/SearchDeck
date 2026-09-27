# THIRD_PARTY_NOTICES

Этот файл фиксирует сторонние зависимости, которые используются в `SearchDeck` на момент подготовки релиза `0.5.1`.

## Runtime-зависимости

| Пакет | Версия | Лицензия | Источник |
|---|---:|---|---|
| `PySide6` | `6.10.2` | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | <https://pyside.org> |
| `PySide6_Addons` | `6.10.2` | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | <https://pyside.org> |
| `PySide6_Essentials` | `6.10.2` | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | <https://pyside.org> |
| `shiboken6` | `6.10.2` | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | <https://pyside.org> |

## Dev и release tooling

Эти пакеты нужны для локальной разработки, тестов и подготовки сборки, но не являются частью пользовательского runtime-сценария приложения:

| Пакет | Версия | Лицензия | Источник |
|---|---:|---|---|
| `PyInstaller` | `6.13.0` | `GPLv2-or-later` с special exception | <https://www.pyinstaller.org/> |
| `pytest` | `9.0.3` | `MIT` | <https://docs.pytest.org/en/latest/> |
| `pytest-qt` | `4.5.0` | `MIT` | <https://github.com/pytest-dev/pytest-qt> |

## Замечания по распространению

1. Основной риск лицензирования связан с `PySide6` и связанными пакетами Qt for Python.
2. При распространении бинарных релизов необходимо соблюдать условия выбранной модели лицензирования Qt for Python.
3. Для текущей подготовки релиза создан также файл `SOURCE_CODE_ACCESS.md`.
4. Собственный код SearchDeck — MIT (LICENSE); это не меняет лицензий Qt/PySide6.
5. Тексты LGPL-3.0-only и GPL-3.0-only находятся в assets/licenses и копируются в поставку. Qt используется динамически, без модификации его исходников. Доступ к оригинальным исходникам указан в SOURCE_CODE_ACCESS.md.
