from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget


class Card(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("ui-card", True)

        container = QVBoxLayout(self)
        container.setContentsMargins(14, 14, 14, 14)
        container.setSpacing(8)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)
        container.addLayout(self.body)
