from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QWidget


class ChipButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setProperty("chip", True)
        self.setCheckable(False)
        self.setMinimumHeight(28)
