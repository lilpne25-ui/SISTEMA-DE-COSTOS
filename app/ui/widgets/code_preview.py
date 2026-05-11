from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.ui.icons import icon
from app.ui.theme import TYPOGRAPHY
from app.ui.widgets.secondary_button import SecondaryButton


class CodePreview(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.lbl_codigo = QLabel("---")
        font = QFont(TYPOGRAPHY.family_mono)
        font.setPixelSize(TYPOGRAPHY.lg)
        self.lbl_codigo.setFont(font)
        self.lbl_codigo.setProperty("code-preview", True)

        self.btn_copy = SecondaryButton("Copiar")
        self.btn_copy.setIcon(icon("copy"))
        self.btn_copy.setMaximumWidth(96)
        self.btn_copy.clicked.connect(self.copy_code)

        layout.addWidget(self.lbl_codigo, 1)
        layout.addWidget(self.btn_copy, 0)

    def set_code(self, codigo: str) -> None:
        self.lbl_codigo.setText(codigo)

    def code(self) -> str:
        return self.lbl_codigo.text().strip()

    def copy_code(self) -> None:
        code = self.code()
        if not code or code == "---":
            return
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(code)
