from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget


class DeltaLabel(QLabel):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("delta", "flat")
        self.setText("Sin variación")

    def set_delta(self, texto: str, signo: str) -> None:
        self.setProperty("delta", signo)
        self.setText(texto)
        self.style().unpolish(self)
        self.style().polish(self)
