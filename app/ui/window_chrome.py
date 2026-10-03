from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QWidget


class TopBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("topBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addStretch(1)

        self.profile_button = QPushButton("P1")
        self.profile_button.setObjectName("browserProfileButton")
        self.profile_button.setToolTip("Профиль браузера")
        layout.addWidget(self.profile_button)
