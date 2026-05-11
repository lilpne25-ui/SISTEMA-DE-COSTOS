from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.models.precio_a36_placa import PrecioA36Placa


class TarifasA36Model(QAbstractTableModel):
    HEADERS = ["Rango", "Espesor mínimo", "Espesor máximo", "Precio /kg"]

    ROLE_ITEM = Qt.UserRole + 301

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[PrecioA36Placa] = []

    def cargar(self, filas: list[PrecioA36Placa]) -> None:
        self.beginResetModel()
        self._rows = list(filas)
        self.endResetModel()

    def item_en_fila(self, fila: int) -> PrecioA36Placa | None:
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
        if role == Qt.DisplayRole and orientation == Qt.Horizontal and 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        item = self._rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return item.rango_label
            if col == 1:
                return item.espesor_min_pulgadas
            if col == 2:
                return item.espesor_max_pulgadas
            if col == 3:
                return ""

        if role == Qt.TextAlignmentRole:
            if col in (1, 2, 3):
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        if role == Qt.UserRole and col == 3:
            return item.precio_kg

        if role == self.ROLE_ITEM:
            return item

        return None
