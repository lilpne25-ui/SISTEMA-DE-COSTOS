"""Diálogo para generar reporte PDF de costos por rango de fechas."""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from app.data.repository import Repository
from app.services.pdf_report_service import CostoReporte, EmpresaInfo, generar_reporte_costos_pdf
from app.ui.widgets import Card, ChipButton, FormField, PrimaryButton, SecondaryButton, Toast


class ReporteDialog(QDialog):
    """Diálogo para configurar y exportar reporte PDF de costos."""

    def __init__(self, repo: Repository, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.setWindowTitle("Generar reporte de costos")
        self.resize(520, 480)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ---- Card empresa ---------------------------------------------
        card_empresa = Card()
        lbl_emp = QLabel("Datos del encabezado")
        lbl_emp.setProperty("section-title", True)
        card_empresa.body.addWidget(lbl_emp)

        self.txt_empresa = QLineEdit("InnovaX Logística")
        self.txt_subtitulo = QLineEdit("Sistema de Gestión de Costos de Acero")
        self.txt_direccion = QLineEdit()
        self.txt_direccion.setPlaceholderText("Dirección (opcional)")
        self.txt_telefono = QLineEdit()
        self.txt_telefono.setPlaceholderText("Teléfono (opcional)")

        self.field_empresa = FormField("Nombre de empresa", self.txt_empresa)
        self.field_subtitulo = FormField("Subtítulo", self.txt_subtitulo)

        card_empresa.body.addWidget(self.field_empresa)
        card_empresa.body.addWidget(self.field_subtitulo)
        card_empresa.body.addWidget(FormField("Dirección", self.txt_direccion))
        card_empresa.body.addWidget(FormField("Teléfono", self.txt_telefono))
        root.addWidget(card_empresa)

        # ---- Card rango -----------------------------------------------
        card_rango = Card()
        lbl_rango = QLabel("Rango de fechas")
        lbl_rango.setProperty("section-title", True)
        card_rango.body.addWidget(lbl_rango)

        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDate(QDate.currentDate().addMonths(-1))

        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDate(QDate.currentDate())

        # Chips de rango rápido
        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)
        chip_mes = ChipButton("Último mes")
        chip_trimestre = ChipButton("Último trimestre")
        chip_anio = ChipButton("Último año")
        chip_todo = ChipButton("Todo")

        chip_mes.clicked.connect(lambda: self._set_rango_dias(30))
        chip_trimestre.clicked.connect(lambda: self._set_rango_dias(90))
        chip_anio.clicked.connect(lambda: self._set_rango_dias(365))
        chip_todo.clicked.connect(self._set_rango_todo)

        chips_row.addWidget(chip_mes)
        chips_row.addWidget(chip_trimestre)
        chips_row.addWidget(chip_anio)
        chips_row.addWidget(chip_todo)
        chips_row.addStretch(1)

        card_rango.body.addWidget(FormField("Desde", self.date_desde))
        card_rango.body.addWidget(FormField("Hasta", self.date_hasta))
        card_rango.body.addLayout(chips_row)

        # Filtro de material (reproduce lógica de MainWindow._cargar_tipos)
        self.cmb_filtro = QComboBox()
        tipos_catalogo = [item.nombre for item in repo.listar_catalogo_materiales()]
        tipos_bd = repo.tipos_material()
        tipos = ["Todos"] + tipos_catalogo + [t for t in tipos_bd if t not in tipos_catalogo]
        self.cmb_filtro.addItems(tipos)
        card_rango.body.addWidget(FormField("Filtrar por material", self.cmb_filtro))

        root.addWidget(card_rango)

        # ---- Preview info label ----------------------------------------
        self.lbl_preview = QLabel("")
        self.lbl_preview.setProperty("muted", True)
        self.lbl_preview.setWordWrap(True)
        root.addWidget(self.lbl_preview)

        # ---- Botones ---------------------------------------------------
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.btn_cancel = SecondaryButton("Cancelar")
        self.btn_generar = PrimaryButton("Generar PDF")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_generar.clicked.connect(self._generar)
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_generar)
        root.addLayout(buttons)

        # Actualizar preview al cambiar filtros
        self.date_desde.dateChanged.connect(self._actualizar_preview)
        self.date_hasta.dateChanged.connect(self._actualizar_preview)
        self.cmb_filtro.currentTextChanged.connect(self._actualizar_preview)
        self._actualizar_preview()

        QShortcut(QKeySequence("Escape"), self, activated=self.reject)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._generar)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._generar)

    def _qdate_to_date(self, qd: QDate) -> date:
        return date(qd.year(), qd.month(), qd.day())

    def _set_rango_dias(self, dias: int) -> None:
        self.date_hasta.setDate(QDate.currentDate())
        self.date_desde.setDate(QDate.currentDate().addDays(-dias))

    def _set_rango_todo(self) -> None:
        self.date_desde.setDate(QDate(2000, 1, 1))
        self.date_hasta.setDate(QDate.currentDate())

    def _contar_filas(self) -> int:
        filas = self._obtener_filas()
        return len(filas)

    def _actualizar_preview(self) -> None:
        total = self._contar_filas()
        desde = self._qdate_to_date(self.date_desde.date())
        hasta = self._qdate_to_date(self.date_hasta.date())
        filtro = self.cmb_filtro.currentText()
        self.lbl_preview.setText(
            f"{total} registro{'s' if total != 1 else ''} encontrado{'s' if total != 1 else ''} "
            f"del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}"
            + (f" · Filtro: {filtro}" if filtro != "Todos" else "")
        )

    def _obtener_filas(self) -> list[CostoReporte]:
        desde = self._qdate_to_date(self.date_desde.date())
        hasta = self._qdate_to_date(self.date_hasta.date())
        filtro = self.cmb_filtro.currentText()

        materiales = self.repo.listar_materiales(
            filtro_tipo=filtro if filtro != "Todos" else "Todos",
            busqueda=None,
        )

        filas: list[CostoReporte] = []
        for mat in materiales:
            if mat.id is None:
                continue
            costos = self.repo.listar_costos(mat.id)
            for c in costos:
                if c.fecha < desde or c.fecha > hasta:
                    continue
                filas.append(CostoReporte(
                    codigo=mat.codigo,
                    material=mat.nombre,
                    forma=mat.forma,
                    fecha=c.fecha,
                    precio_unitario=c.precio_unitario,
                    moneda=c.moneda,
                    unidad=c.unidad,
                    proveedor=c.proveedor,
                ))

        filas.sort(key=lambda r: (r.fecha, r.codigo))
        return filas

    def _generar(self) -> None:
        filas = self._obtener_filas()
        if not filas:
            Toast.show_toast(self, "No hay registros en el rango seleccionado", "info")
            return

        desde = self._qdate_to_date(self.date_desde.date())
        hasta = self._qdate_to_date(self.date_hasta.date())

        nombre_default = f"reporte_costos_{desde:%Y%m%d}_{hasta:%Y%m%d}.pdf"
        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte PDF",
            nombre_default,
            "Archivos PDF (*.pdf)",
        )
        if not ruta:
            return
        if not ruta.lower().endswith(".pdf"):
            ruta += ".pdf"

        empresa = EmpresaInfo(
            nombre=self.txt_empresa.text().strip() or "InnovaX Logística",
            subtitulo=self.txt_subtitulo.text().strip() or "Sistema de Gestión de Costos de Acero",
            direccion=self.txt_direccion.text().strip(),
            telefono=self.txt_telefono.text().strip(),
        )

        try:
            pdf_bytes = generar_reporte_costos_pdf(
                filas=filas,
                fecha_inicio=desde,
                fecha_fin=hasta,
                empresa=empresa,
                filtro_material=self.cmb_filtro.currentText(),
            )
            with open(ruta, "wb") as f:
                f.write(pdf_bytes)

            Toast.show_toast(self, f"Reporte exportado: {os.path.basename(ruta)}", "success")
            self.accept()
        except Exception as exc:
            Toast.show_toast(self, f"Error al generar el reporte: {exc}", "error")
