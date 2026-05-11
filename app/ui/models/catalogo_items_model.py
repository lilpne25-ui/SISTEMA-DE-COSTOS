from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.models.catalogo_item import CatalogoItem


@dataclass(slots=True)
class CatalogoItemRow:
    item: CatalogoItem
    usado_en: int


class CatalogoItemsModel(QAbstractTableModel):
    HEADERS = ["Nombre", "Prefijo código", "Tipo base", "Densidad kg/m³", "Usado en"]

    ROLE_ITEM = Qt.UserRole + 303

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[CatalogoItemRow] = []

    def cargar(self, filas: list[CatalogoItemRow]) -> None:
        self.beginResetModel()
        self._rows = list(filas)
        self.endResetModel()

    def item_en_fila(self, fila: int) -> CatalogoItem | None:
        if fila < 0 or fila >= len(self._rows):
            return None
        return self._rows[fila].item

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

        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return row.item.nombre
            if col == 1:
                return row.item.prefijo_codigo
            if col == 2:
                return (row.item.tipo_base or "").strip().upper()
            if col == 3:
                return "" if row.item.densidad_kg_m3 is None else f"{row.item.densidad_kg_m3:.3f}"
            if col == 4:
                return row.usado_en

        if role == Qt.TextAlignmentRole:
            if col in (3, 4):
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        if role == self.ROLE_ITEM:
            return row.item

        return None
