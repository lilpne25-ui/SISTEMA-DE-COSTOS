from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from app.ui.formatting import formatear_pulgadas


class EspesorDelegate(QStyledItemDelegate):
    def initStyleOption(self, option: QStyleOptionViewItem, index) -> None:
        super().initStyleOption(option, index)
        raw_value = index.data(Qt.DisplayRole)
        if raw_value in (None, "", "Sin dato"):
            option.text = "Sin dato"
            return

        try:
            option.text = formatear_pulgadas(float(raw_value))
        except (TypeError, ValueError):
            option.text = str(raw_value)
