from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QBrush, QColor, QFont

from app.models.costo import Costo
from app.models.material import Material
from app.ui.formatting import formatear_money, formatear_pulgadas
from app.ui.theme import TYPOGRAPHY


@dataclass(slots=True)
class MaterialRow:
    material: Material
    costo_vigente: Costo | None
    espesor_display: str


@dataclass(slots=True)
class GroupRow:
    nombre: str


_Row = MaterialRow | GroupRow


class MaterialesTableModel(QAbstractTableModel):
    HEADERS = ["Código", "Material", "Forma", "Espesor", "Costo vigente", "Actualizado"]

    ROLE_MATERIAL = Qt.UserRole + 101
    ROLE_COSTO = Qt.UserRole + 102
    ROLE_ESPESOR_RAW = Qt.UserRole + 103
    ROLE_PRECIO_RAW = Qt.UserRole + 104
    ROLE_FECHA_COSTO = Qt.UserRole + 105

    def __init__(self, parent=None, espesor_display_resolver: Callable[[Material], str] | None = None):
        self._rows: list[_Row] = []
        self._data_count: int = 0
        self._espesor_display_resolver = espesor_display_resolver
        super().__init__(parent)
        self._mono_font = QFont(TYPOGRAPHY.family_mono)
        self._mono_font.setPixelSize(TYPOGRAPHY.md)
        self._group_font = QFont(TYPOGRAPHY.family_ui)
        self._group_font.setPixelSize(TYPOGRAPHY.xs)
        self._group_font.setWeight(QFont.Weight.DemiBold)

    def cargar(self, filas: list[tuple[Material, Costo | None]]) -> None:
        self.beginResetModel()
        sorted_filas = sorted(filas, key=lambda x: (x[0].nombre or "").casefold())
        self._rows = []
        self._data_count = len(sorted_filas)
        prev_nombre: str | None = None
        for m, c in sorted_filas:
            nombre = (m.nombre or "").strip()
            if nombre != prev_nombre:
                self._rows.append(GroupRow(nombre=nombre))
                prev_nombre = nombre
            espesor_display = ""
            if self._espesor_display_resolver is not None:
                try:
                    espesor_display = (self._espesor_display_resolver(m) or "").strip()
                except Exception:
                    espesor_display = ""
            if not espesor_display:
                espesor_display = (
                    formatear_pulgadas(m.espesor_pulgadas)
                    if m.espesor_pulgadas is not None
                    else "Sin dato"
                )
            self._rows.append(
                MaterialRow(material=m, costo_vigente=c, espesor_display=espesor_display)
            )
        self.endResetModel()

    def is_group_row(self, source_row: int) -> bool:
        if source_row < 0 or source_row >= len(self._rows):
            return False
        return isinstance(self._rows[source_row], GroupRow)

    def data_row_count(self) -> int:
        return self._data_count

    def material_en_fila(self, fila: int) -> Material | None:
        if fila < 0 or fila >= len(self._rows):
            return None
        row = self._rows[fila]
        if isinstance(row, GroupRow):
            return None
        return row.material

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

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        if self.is_group_row(index.row()):
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        col = index.column()

        if isinstance(row, GroupRow):
            if role == Qt.DisplayRole:
                return row.nombre if col == 0 else ""
            if role == Qt.FontRole and col == 0:
                return self._group_font
            if role == Qt.ForegroundRole:
                from app.ui.theme import tokens
                return QBrush(QColor(tokens().text_muted))
            if role == Qt.BackgroundRole:
                from app.ui.theme import tokens
                return QBrush(QColor(tokens().surface_sunken))
            if role == Qt.TextAlignmentRole:
                return int(Qt.AlignLeft | Qt.AlignVCenter)
            return None

        material = row.material
        costo = row.costo_vigente

        if role == Qt.DisplayRole:
            if col == 0:
                return material.codigo
            if col == 1:
                return material.nombre
            if col == 2:
                return material.forma or "Sin dato"
            if col == 3:
                return row.espesor_display
            if col == 4:
                return ""
            if col == 5:
                return self._texto_actualizado(costo)
            return None

        if role == Qt.TextAlignmentRole:
            if col in (3, 4, 5):
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        if role == Qt.FontRole and col in (0, 3, 4):
            return self._mono_font

        if role == Qt.UserRole:
            if col == 0:
                return material.id
            if col == 4:
                return costo.precio_unitario if costo else None

        if role == self.ROLE_MATERIAL:
            return material

        if role == self.ROLE_COSTO:
            return costo

        if role == self.ROLE_ESPESOR_RAW:
            return material.espesor_pulgadas

        if role == self.ROLE_PRECIO_RAW:
            return costo.precio_unitario if costo else None

        if role == self.ROLE_FECHA_COSTO:
            return costo.fecha if costo else None

        if role == Qt.ToolTipRole:
            if col == 4:
                return formatear_money(costo.precio_unitario) if costo else "Sin costo registrado"
            if col == 5:
                return self._tooltip_actualizado(costo)

        return None

    @staticmethod
    def _texto_actualizado(costo: Costo | None) -> str:
        if costo is None:
            return "Sin costo"
        dias = (date.today() - costo.fecha).days
        if dias <= 0:
            return "Hoy"
        if dias == 1:
            return "Hace 1 día"
        return f"Hace {dias} días"

    @staticmethod
    def _tooltip_actualizado(costo: Costo | None) -> str:
        if costo is None:
            return "No hay costo vigente"
        dias = (date.today() - costo.fecha).days
        if dias <= 0:
            return "Costo actualizado hoy"
        return f"Última actualización hace {dias} días ({costo.fecha:%Y-%m-%d})"
