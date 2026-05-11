from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.icons import icon
from app.ui.theme import TYPOGRAPHY
from app.ui.widgets.card import Card
from app.ui.widgets.secondary_button import SecondaryButton


class RuleCard(Card):
    def __init__(self, titulo: str = "Regla de costo", parent: QWidget | None = None):
        super().__init__(parent)

        self.lbl_titulo = QLabel(titulo)
        self.lbl_valor = QLabel("Sin dato")
        value_font = QFont(TYPOGRAPHY.family_mono)
        value_font.setPixelSize(TYPOGRAPHY._2xl)
        value_font.setWeight(QFont.Weight.DemiBold)
        self.lbl_valor.setFont(value_font)

        self.lbl_hint = QLabel("")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setProperty("muted", True)

        self.row_empty = QWidget()
        row_layout = QHBoxLayout(self.row_empty)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        self.lbl_alert_icon = QLabel()
        self.lbl_alert_icon.setPixmap(icon("alert-circle").pixmap(16, 16))
        self.lbl_alert = QLabel("Sin regla de costo disponible")
        self.lbl_alert.setProperty("warning", True)

        self.btn_configurar = SecondaryButton("Configurar tarifas")
        self.btn_configurar.setIcon(icon("settings"))
        row_layout.addWidget(self.lbl_alert_icon)
        row_layout.addWidget(self.lbl_alert)
        row_layout.addStretch(1)
        row_layout.addWidget(self.btn_configurar)

        self.body.addWidget(self.lbl_titulo)
        self.body.addWidget(self.lbl_valor)
        self.body.addWidget(self.lbl_hint)
        self.body.addWidget(self.row_empty)

        self.show_value("Sin dato", "")

    def show_value(self, valor: str, hint: str = "") -> None:
        self.lbl_valor.setText(valor)
        self.lbl_hint.setText(hint)
        self.row_empty.hide()

    def show_empty(self, mensaje: str) -> None:
        self.lbl_valor.setText("Sin regla")
        self.lbl_hint.setText(mensaje)
        self.row_empty.show()
