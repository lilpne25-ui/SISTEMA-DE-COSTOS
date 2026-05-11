from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import QApplication, QStyledItemDelegate, QStyle, QStyleOptionViewItem

from app.ui.formatting import formatear_money
from app.ui.theme import TYPOGRAPHY, tokens


class MoneyDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._font = QFont(TYPOGRAPHY.family_mono)
        self._font.setPixelSize(TYPOGRAPHY.md)

    def initStyleOption(self, option: QStyleOptionViewItem, index) -> None:
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignRight | Qt.AlignVCenter
        option.font = self._font

    def paint(self, painter, option: QStyleOptionViewItem, index) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""

        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)

        value = index.data(Qt.UserRole)
        if value is None:
            value = index.data(Qt.DisplayRole)

        if value is None:
            text = "Sin dato"
        else:
            try:
                amount = float(value)
                text = formatear_money(amount)
            except (TypeError, ValueError):
                text = str(value)

        text_rect = opt.rect.adjusted(8, 0, -8, 0)
        painter.save()
        painter.setPen(opt.palette.color(QPalette.Text))
        painter.setFont(opt.font)
        painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, text)
        painter.restore()
