from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class FormField(QWidget):
    def __init__(self, titulo: str, input_widget: QWidget, parent: QWidget | None = None):
        super().__init__(parent)
        self.input_widget = input_widget

        self.lbl_titulo = QLabel(titulo)
        self.lbl_error = QLabel("")
        self.lbl_error.setProperty("field-error", True)
        self.lbl_error.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.lbl_titulo)
        layout.addWidget(self.input_widget)
        layout.addWidget(self.lbl_error)

    def set_error(self, msg: str) -> None:
        self.lbl_error.setText(msg)
        self.lbl_error.setVisible(bool(msg.strip()))

    def clear_error(self) -> None:
        self.lbl_error.setText("")
        self.lbl_error.hide()
