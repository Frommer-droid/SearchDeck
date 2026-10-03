from __future__ import annotations

from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication


class QtClipboardBridge:
    """Снимок и восстановление буфера обмена через Qt."""

    def capture(self) -> dict[str, bytes]:
        mime_data = QApplication.clipboard().mimeData()
        return {mime_type: bytes(mime_data.data(mime_type)) for mime_type in mime_data.formats()}

    def set_text(self, text: str) -> None:
        QApplication.clipboard().setText(text)

    def restore(self, snapshot: dict[str, bytes]) -> None:
        mime_data = QMimeData()
        for mime_type, payload in snapshot.items():
            mime_data.setData(mime_type, payload)
        QApplication.clipboard().setMimeData(mime_data)
