from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QFont

from app.models.costo import Costo
from app.ui.theme import TYPOGRAPHY


class CostosTableModel(QAbstractTableModel):
    HEADERS = ["Fecha", "Precio", "Moneda", "Unidad", "Proveedor"]

    ROLE_COSTO = Qt.UserRole + 201
    ROLE_PRECIO_RAW = Qt.UserRole + 202

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[Costo] = []
        self._mono_font = QFont(TYPOGRAPHY.family_mono)
        self._mono_font.setPixelSize(TYPOGRAPHY.md)

    def cargar(self, costos: list[Costo]) -> None:
        self.beginResetModel()
        self._rows = list(costos)
        self.endResetModel()

    def costo_en_fila(self, fila: int) -> Costo | None:
        if fila < 0 or fila >= len(self._rows):
            return None
        return self._rows[fila]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal and 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        costo = self._rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return costo.fecha.strftime("%Y-%m-%d")
            if col == 1:
                return ""
            if col == 2:
                return costo.moneda
            if col == 3:
                return costo.unidad
            if col == 4:
                return costo.proveedor or "Sin dato"
            return None

        if role == Qt.TextAlignmentRole:
            if col in (0, 1):
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        if role == Qt.FontRole and col in (0, 1):
            return self._mono_font

        if role == Qt.UserRole and col == 1:
            return costo.precio_unitario

        if role == self.ROLE_COSTO:
            return costo

        if role == self.ROLE_PRECIO_RAW:
            return costo.precio_unitario

        if role == Qt.ToolTipRole and col == 1:
            return f"{costo.moneda} {costo.precio_unitario:,.2f}/{costo.unidad}"

        return None
