from __future__ import annotations

import logging
from pathlib import Path


class SessionLogManager:
    """Управляет lifecycle лог-файла текущей сессии."""

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        self._logger_name = f"browser_find_pad.{log_path.as_posix()}"
        self._logger = logging.getLogger(self._logger_name)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self._configure()

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def shutdown(self) -> None:
        for handler in list(self._logger.handlers):
            handler.flush()
            handler.close()
            self._logger.removeHandler(handler)

    def _configure(self) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        for handler in list(self._logger.handlers):
            handler.close()
            self._logger.removeHandler(handler)
        handler = logging.FileHandler(self._log_path, mode="w", encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        self._logger.addHandler(handler)
