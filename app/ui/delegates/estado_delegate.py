from __future__ import annotations

from datetime import date

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from app.ui.theme import tokens


class EstadoDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        value = index.data(Qt.DisplayRole)
        if value in (None, ""):
            super().paint(painter, option, index)
            return

        texto = str(value)
        token = tokens()

        fecha = self._parse_fecha(index.data(Qt.UserRole + 105))
        bg, fg = self._resolver_colores(fecha, token)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        chip_rect = QRect(option.rect)
        chip_rect.setLeft(option.rect.left() + 8)
        chip_rect.setRight(option.rect.right() - 8)
        chip_rect.setTop(option.rect.top() + 5)
        chip_rect.setBottom(option.rect.bottom() - 5)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(chip_rect, 6, 6)

        painter.setPen(QColor(fg))
        painter.drawText(chip_rect, Qt.AlignCenter, texto)
        painter.restore()

    @staticmethod
    def _parse_fecha(value) -> date | None:
        if isinstance(value, date):
            return value
        return None

    @staticmethod
    def _resolver_colores(fecha: date | None, t):
        if fecha is None:
            return t.surface_sunken, t.text_muted
        dias = (date.today() - fecha).days
        if dias <= 0:
            return t.success_soft, t.success
        if dias <= 7:
            return t.warning_soft, t.warning
        return t.surface_sunken, t.text_muted
