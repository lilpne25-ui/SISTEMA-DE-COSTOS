from __future__ import annotations

from PySide6.QtCore import QRegularExpression, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QLineEdit


class MoneyInput(QLineEdit):
    """QLineEdit para valores monetarios: solo dígitos, formatea al perder foco."""

    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"[0-9]*\.?[0-9]{0,4}")
        ))
        self.setPlaceholderText("0.0000")
        self.editingFinished.connect(self._on_editing_finished)
        self.textChanged.connect(self._emit_value)

    def value(self) -> float:
        try:
            return float(self.text().strip())
        except ValueError:
            return 0.0

    def setValue(self, val: float) -> None:
        self.blockSignals(True)
        self.setText(f"{val:.4f}" if val > 0 else "")
        self.blockSignals(False)
        self.valueChanged.emit(val if val > 0 else 0.0)

    def setReadOnly(self, ro: bool) -> None:
        super().setReadOnly(ro)
        self.setProperty("readonly-display", ro)
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_editing_finished(self) -> None:
        text = self.text().strip()
        if not text:
            return
        try:
            val = float(text)
            formatted = f"{val:.4f}"
            if formatted != text:
                self.blockSignals(True)
                self.setText(formatted)
                self.blockSignals(False)
        except ValueError:
            self.setText("")

    def _emit_value(self, text: str) -> None:
        try:
            self.valueChanged.emit(float(text) if text.strip() else 0.0)
        except ValueError:
            pass
