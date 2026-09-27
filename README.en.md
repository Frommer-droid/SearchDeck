<p align="center"><img src="assets/brand/searchdeck-logo.png" width="128" alt="SearchDeck icon"></p>
<h1 align="center">SearchDeck</h1>
<p align="center">Search a browser page for saved phrases with one click.</p>
<p align="center"><a href="README.md">Русский</a> · <a href="https://github.com/Frommer-droid/SearchDeck/releases/latest">Latest release</a></p>

SearchDeck stores phrases as buttons grouped into workspace tabs and categories. Clicking a button activates the selected Yandex Browser profile, opens Find on Page and inserts the phrase.

## Installation

Download and run the installer from [GitHub Releases](https://github.com/Frommer-droid/SearchDeck/releases/latest). The first launch creates an empty example tab. Use context menus to add a category and search buttons.

## Features

- Workspace tabs and categories for different phrase collections.
- Left click searches the current browser tab; right click searches a duplicate.
- Ctrl + right click opens a button editing menu.
- Drag buttons and categories, sort and rename entries.
- Select a browser profile with the P1, P2 and subsequent buttons.
- Configure search delays and interface scale.
- Compact always-on-top window with the One Dark theme.

## Requirements and settings

Windows 10/11 x64 and Yandex Browser. Running from source requires Python 3.12.

The browser data directory is resolved from the current user's LOCALAPPDATA. Select the profile number in the app. Other browsers are not supported by the automation workflow.

Data and window geometry are stored in settings.json beside the EXE, or in the repository root when running from source. This directory must be writable. The installer excludes user settings. [settings.example.json](settings.example.json) is a neutral example. Back up your settings.json before replacing a portable directory.

## Run from source

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\pythonw.exe main.py
```

## Development

```powershell
.\.venv\Scripts\python.exe -m ruff check . --no-cache
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe Build_Tools/build_release.py
```

See [DEVELOPER.md](DEVELOPER.md) for architecture and build checks, and [RELEASE_NOTES.md](RELEASE_NOTES.md) for the release history (Russian).

## Author

[Frommer-droid](https://github.com/Frommer-droid).

## License

Application code: [MIT](LICENSE). Qt/PySide6 and other dependencies retain separate licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). See [SOURCE_CODE_ACCESS.md](SOURCE_CODE_ACCESS.md) for source access information.
