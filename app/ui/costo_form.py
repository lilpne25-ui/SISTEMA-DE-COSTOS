from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
)

from app.models.costo import Costo
from app.models.material import Material
from app.ui.formatting import formatear_delta, formatear_money
from app.ui.widgets import Card, ChipButton, DeltaLabel, FormField, MoneyInput, PrimaryButton, SecondaryButton


class CostoForm(QDialog):
    guardado = Signal(object)  # Costo
    def __init__(
        self,
        parent=None,
        *,
        material: Optional[Material] = None,
        costo_vigente: Optional[Costo] = None,
        proveedores_recientes: Optional[list[str]] = None,
        precio_default: Optional[float] = None,
        nota_default: str = "",
    ):
        super().__init__(parent)
        self._material = material
        self._costo_vigente = costo_vigente

        self.setWindowTitle("Agregar costo")
        self.resize(540, 480)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ---- Card de contexto ------------------------------------------
        if material is not None:
            card_ctx = Card()
            espesor_txt = ""
            if material.espesor_pulgadas is not None:
                from app.ui.formatting import formatear_pulgadas
                espesor_txt = f" · {formatear_pulgadas(material.espesor_pulgadas)}"
            lbl_mat = QLabel(
                f"{material.codigo} · {material.nombre} {material.forma}{espesor_txt}"
            )
            lbl_mat.setProperty("section-title", True)
            card_ctx.body.addWidget(lbl_mat)

            if costo_vigente is not None:
                dias = (date.today() - costo_vigente.fecha).days
                hace_txt = f"hace {dias} día{'s' if dias != 1 else ''}" if dias > 0 else "hoy"
                lbl_vig = QLabel(
                    f"Costo vigente: {formatear_money(costo_vigente.precio_unitario)} ({hace_txt})"
                )
                lbl_vig.setProperty("muted", True)
                card_ctx.body.addWidget(lbl_vig)
            else:
                lbl_vig = QLabel("Primer costo registrado")
                lbl_vig.setProperty("muted", True)
                card_ctx.body.addWidget(lbl_vig)

            root.addWidget(card_ctx)

        # ---- Fecha con ChipButtons ------------------------------------
        self.date_fecha = QDateEdit()
        self.date_fecha.setCalendarPopup(True)
        self.date_fecha.setDate(QDate.currentDate())

        fecha_row = QHBoxLayout()
        fecha_row.setSpacing(6)
        fecha_row.addWidget(self.date_fecha, 1)

        chip_hoy = ChipButton("Hoy")
        chip_ayer = ChipButton("Ayer")
        chip_semana = ChipButton("-1 sem")
        chip_hoy.clicked.connect(lambda: self.date_fecha.setDate(QDate.currentDate()))
        chip_ayer.clicked.connect(
            lambda: self.date_fecha.setDate(QDate.currentDate().addDays(-1))
        )
        chip_semana.clicked.connect(
            lambda: self.date_fecha.setDate(QDate.currentDate().addDays(-7))
        )
        fecha_row.addWidget(chip_hoy)
        fecha_row.addWidget(chip_ayer)
        fecha_row.addWidget(chip_semana)

        fecha_container = QVBoxLayout()
        fecha_container.setContentsMargins(0, 0, 0, 0)
        fecha_container.setSpacing(4)
        lbl_fecha_titulo = QLabel("Fecha")
        fecha_container.addWidget(lbl_fecha_titulo)
        fecha_container.addLayout(fecha_row)
        self.field_fecha_error = QLabel("")
        self.field_fecha_error.setProperty("field-error", True)
        self.field_fecha_error.hide()
        fecha_container.addWidget(self.field_fecha_error)

        # ---- Precio + DeltaLabel en vivo -------------------------------
        self.spn_precio = MoneyInput()
        self.delta_label = DeltaLabel()
        self.spn_precio.valueChanged.connect(self._on_precio_changed)
        self.field_precio = FormField("Precio unitario (MXN/kg)", self.spn_precio)

        # ---- Proveedor con QCompleter ----------------------------------
        self.cmb_proveedor = QComboBox()
        self.cmb_proveedor.setEditable(True)
        self.cmb_proveedor.setInsertPolicy(QComboBox.NoInsert)
        self.cmb_proveedor.addItem("")
        for proveedor in proveedores_recientes or []:
            if proveedor and self.cmb_proveedor.findText(proveedor) < 0:
                self.cmb_proveedor.addItem(proveedor)

        completer = QCompleter(
            [p for p in (proveedores_recientes or []) if p], self
        )
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.cmb_proveedor.setCompleter(completer)

        # ---- Nota ------------------------------------------------------
        self.txt_nota = QTextEdit()
        self.txt_nota.setPlaceholderText(
            "Nota opcional (ejemplo: ajuste de proveedor, tarifa, observaciones)"
        )
        self.txt_nota.setFixedHeight(60)

        self.field_proveedor = FormField("Proveedor", self.cmb_proveedor)
        self.field_nota = FormField("Nota", self.txt_nota)

        root.addLayout(fecha_container)
        root.addWidget(self.field_precio)
        root.addWidget(self.delta_label)
        root.addWidget(self.field_proveedor)
        root.addWidget(self.field_nota)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.btn_cancel = SecondaryButton("Cancelar")
        self.btn_guardar = PrimaryButton("Guardar")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_guardar.clicked.connect(self._validate)
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_guardar)
        root.addLayout(buttons)

        if precio_default is not None and precio_default > 0:
            self.spn_precio.setValue(float(precio_default))
        if material is not None and material.proveedor:
            self.cmb_proveedor.setCurrentText(material.proveedor)
        if nota_default:
            self.txt_nota.setPlainText(nota_default)

        self._on_precio_changed(self.spn_precio.value())
        self.spn_precio.setFocus()
        self._config_shortcuts()

    def _on_precio_changed(self, nuevo: float) -> None:
        if self._costo_vigente is None:
            self.delta_label.set_delta("Primer registro", "flat")
            return
        texto, signo = formatear_delta(nuevo, self._costo_vigente.precio_unitario)
        self.delta_label.set_delta(
            f"Δ {texto} vs costo vigente", signo
        )

    def _config_shortcuts(self) -> None:
        QShortcut(QKeySequence("Escape"), self, activated=self.reject)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._validate)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._validate)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._validate)
        QShortcut(QKeySequence("Alt+H"), self, activated=lambda: self.date_fecha.setDate(QDate.currentDate()))
        QShortcut(QKeySequence("Alt+A"), self, activated=lambda: self.date_fecha.setDate(QDate.currentDate().addDays(-1)))

    def _validate(self) -> None:
        self.field_precio.clear_error()

        if self.spn_precio.value() <= 0:
            self.field_precio.set_error("El precio debe ser mayor a 0.")
            return

        self.guardado.emit(self.obtener_costo())
        self.accept()

    def obtener_costo(self) -> Costo:
        qdate = self.date_fecha.date()
        fecha = date(qdate.year(), qdate.month(), qdate.day())

        proveedor = self.cmb_proveedor.currentText().strip()
        nota = self.txt_nota.toPlainText().strip()

        return Costo(
            id=None,
            material_id=self._material.id if self._material and self._material.id else 0,
            fecha=fecha,
            precio_unitario=float(self.spn_precio.value()),
            moneda="MXN",
            unidad="kg",
            proveedor=proveedor,
            nota=nota,
        )
