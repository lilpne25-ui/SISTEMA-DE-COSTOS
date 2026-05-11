"""Formulario profesional para crear/editar materiales."""

from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QVBoxLayout,
)

from app.data.repository import Repository
from app.models.costo import Costo
from app.models.material import Material
from app.ui.formatting import formatear_money
from app.ui.windows import ConfigWindow
from app.ui.widgets import Card, CodePreview, FormField, MoneyInput, RuleCard


class MaterialForm(QDialog):
    guardado = Signal(object, object)  # (Material, Costo | None)
    def __init__(
        self,
        repo: Repository,
        parent=None,
        material: Optional[Material] = None,
    ):
        super().__init__(parent)
        self.repo = repo
        self._material_original = material
        self._prefijos_material: dict[str, str] = {}
        self._prefijos_forma: dict[str, str] = {}
        self._densidades_material: dict[str, float] = {}
        self._tipos_base_material: dict[str, str] = {}

        self.setWindowTitle("Nuevo material" if material is None else "Editar material")
        self.resize(720, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root.addWidget(self._build_identificacion_card())
        root.addWidget(self._build_especificacion_card())

        if self._material_original is None:
            root.addWidget(self._build_costo_inicial_card())
        else:
            self.field_costo = None
            self.spn_costo = None

        self.btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.btns.button(QDialogButtonBox.Save).setText("Guardar")
        self.btns.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.btns.accepted.connect(self._validar_y_aceptar)
        self.btns.rejected.connect(self.reject)
        root.addWidget(self.btns)

        self._cargar_catalogos()
        if material is not None:
            self._cargar(material)
        self._actualizar_contexto()

        self._configurar_shortcuts()

    def _build_identificacion_card(self) -> Card:
        card = Card()
        card_title = FormField("Identificación", QComboBox())
        card_title.hide()

        self.cmb_forma = QComboBox()
        self.cmb_forma.setEditable(True)
        self.cmb_forma.setInsertPolicy(QComboBox.NoInsert)
        self.cmb_forma.currentTextChanged.connect(self._actualizar_contexto)

        self.cmb_material = QComboBox()
        self.cmb_material.setEditable(True)
        self.cmb_material.setInsertPolicy(QComboBox.NoInsert)
        self.cmb_material.currentTextChanged.connect(self._actualizar_contexto)
        self.cmb_material.currentTextChanged.connect(self._auto_tipo_densidad)

        self.cmb_tipo = QComboBox()
        self.cmb_tipo.setEditable(True)
        self.cmb_tipo.setInsertPolicy(QComboBox.NoInsert)

        self.code_preview = CodePreview()

        self.field_forma = FormField("Forma", self.cmb_forma)
        self.field_material = FormField("Material (grado)", self.cmb_material)
        self.field_tipo = FormField("Tipo", self.cmb_tipo)
        self.field_codigo = FormField("Código autogenerado", self.code_preview)

        card.body.addWidget(self.field_forma)
        card.body.addWidget(self.field_material)
        card.body.addWidget(self.field_tipo)
        card.body.addWidget(self.field_codigo)
        return card

    def _build_especificacion_card(self) -> Card:
        card = Card()

        self.spn_espesor = QDoubleSpinBox()
        self.spn_espesor.setRange(0, 12)
        self.spn_espesor.setDecimals(3)
        self.spn_espesor.setSingleStep(0.125)
        self.spn_espesor.setSuffix(' "')
        self.spn_espesor.valueChanged.connect(self._actualizar_contexto)
        self.field_espesor = FormField("Espesor (pulgadas)", self.spn_espesor)

        self.spn_densidad = QDoubleSpinBox()
        self.spn_densidad.setRange(0, 25000)
        self.spn_densidad.setDecimals(3)
        self.spn_densidad.setSingleStep(0.001)
        self.spn_densidad.setSuffix(" kg/m³")
        self.spn_densidad.setSpecialValueText("Sin dato")
        self.field_densidad = FormField("Densidad", self.spn_densidad)

        self.rule_card = RuleCard("Regla de costo")
        self.rule_card.btn_configurar.clicked.connect(self._abrir_configurar_tarifas)

        card.body.addWidget(self.field_espesor)
        card.body.addWidget(self.field_densidad)
        card.body.addWidget(self.rule_card)
        return card

    def _build_costo_inicial_card(self) -> Card:
        card = Card()
        self.spn_costo = MoneyInput()
        self.field_costo = FormField("Costo inicial (MXN/kg)", self.spn_costo)
        card.body.addWidget(self.field_costo)
        return card

    def _configurar_shortcuts(self) -> None:
        QShortcut(QKeySequence("Escape"), self, activated=self.reject)
        QShortcut(QKeySequence("Return"), self, activated=self._validar_y_aceptar)
        QShortcut(QKeySequence("Enter"), self, activated=self._validar_y_aceptar)
        QShortcut(QKeySequence("Ctrl+C"), self, activated=self._atajo_copiar_codigo)

    def _atajo_copiar_codigo(self) -> None:
        fw = self.focusWidget()
        if fw is self.code_preview or fw is self.code_preview.btn_copy or fw is self.code_preview.lbl_codigo:
            self.code_preview.copy_code()

    def _cargar_catalogos(self) -> None:
        materiales = self.repo.listar_catalogo_materiales()
        formas = self.repo.listar_catalogo_formas()
        existentes = self.repo.listar_materiales("Todos", None)

        self._prefijos_material = {item.nombre: item.prefijo_codigo for item in materiales}
        self._prefijos_forma = {item.nombre: item.prefijo_codigo for item in formas}
        self._densidades_material = {
            item.nombre.strip().upper(): float(item.densidad_kg_m3)
            for item in materiales
            if item.densidad_kg_m3 is not None and float(item.densidad_kg_m3) > 0
        }
        self._tipos_base_material = {
            item.nombre.strip().upper(): (item.tipo_base or "").strip().upper()
            for item in materiales
            if (item.tipo_base or "").strip()
        }

        tipos_disponibles: set[str] = {
            (item.tipo_base or "").strip().upper()
            for item in materiales
            if (item.tipo_base or "").strip()
        }
        for m in existentes:
            key = (m.nombre or "").strip().upper()
            categoria = (m.tipo or "").strip().upper()
            if key and categoria and key not in self._tipos_base_material:
                self._tipos_base_material[key] = categoria
            if categoria:
                tipos_disponibles.add(categoria)

        tipo_actual = self.cmb_tipo.currentText().strip()
        self.cmb_tipo.blockSignals(True)
        self.cmb_tipo.clear()
        self.cmb_tipo.addItems(sorted(tipos_disponibles))
        if tipo_actual:
            if self.cmb_tipo.findText(tipo_actual, Qt.MatchFixedString) < 0:
                self.cmb_tipo.addItem(tipo_actual)
            self.cmb_tipo.setCurrentText(tipo_actual)
        self.cmb_tipo.blockSignals(False)

        self.cmb_material.blockSignals(True)
        self.cmb_forma.blockSignals(True)
        self.cmb_material.clear()
        self.cmb_forma.clear()
        self.cmb_material.addItems([item.nombre for item in materiales])
        self.cmb_forma.addItems([item.nombre for item in formas])
        self.cmb_material.blockSignals(False)
        self.cmb_forma.blockSignals(False)

        self._configurar_completer(self.cmb_material)
        self._configurar_completer(self.cmb_forma)

    @staticmethod
    def _configurar_completer(combo: QComboBox) -> None:
        completer = combo.completer()
        if completer is None:
            completer = QCompleter(combo.model(), combo)
            combo.setCompleter(completer)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)

    @staticmethod
    def _asegurar_valor_combo(combo: QComboBox, valor: str) -> None:
        texto = valor.strip()
        if not texto:
            return
        if combo.findText(texto, Qt.MatchFixedString) < 0:
            combo.addItem(texto)

    @staticmethod
    def _normalizar_prefijo(valor: str, fallback: str) -> str:
        base = (valor or "").strip().upper()
        if not base:
            base = fallback.strip().upper()
        base = "".join(ch for ch in base if ch.isalnum())
        return (base or "GEN")[:8]

    def _prefijo_material_actual(self) -> str:
        material = self.cmb_material.currentText().strip()
        prefijo = self._prefijos_material.get(material, material)
        return self._normalizar_prefijo(prefijo, "MAT")

    def _prefijo_forma_actual(self) -> str:
        forma = self.cmb_forma.currentText().strip()
        prefijo = self._prefijos_forma.get(forma, forma)
        return self._normalizar_prefijo(prefijo, "FOR")

    def _es_a36_placa(self) -> bool:
        return (
            self.cmb_material.currentText().strip().upper() == "A36"
            and self.cmb_forma.currentText().strip().upper() == "PLACA"
        )

    def _cargar(self, material: Material) -> None:
        self._asegurar_valor_combo(self.cmb_forma, material.forma or "")
        self._asegurar_valor_combo(self.cmb_material, material.nombre or "")
        self.cmb_forma.setCurrentText(material.forma or "")
        self.cmb_material.setCurrentText(material.nombre or "")
        if material.tipo:
            self.cmb_tipo.setCurrentText(material.tipo)
        if material.espesor_pulgadas is not None:
            self.spn_espesor.setValue(material.espesor_pulgadas)
        if material.densidad is not None:
            self.spn_densidad.setValue(float(material.densidad))
        self.code_preview.set_code(material.codigo)

    def _actualizar_contexto(self) -> None:
        self._actualizar_codigo_preview()
        self._actualizar_regla_costo()

    def _actualizar_codigo_preview(self) -> None:
        if self._material_original is not None:
            self.code_preview.set_code(self._material_original.codigo)
            return

        if not self.cmb_material.currentText().strip() or not self.cmb_forma.currentText().strip():
            self.code_preview.set_code("MAT-FOR-####")
            return

        self.code_preview.set_code(
            f"{self._prefijo_material_actual()}-{self._prefijo_forma_actual()}-####"
        )

    def _actualizar_regla_costo(self) -> None:
        es_a36 = self._es_a36_placa()
        en_creacion = self._material_original is None

        self.spn_espesor.setEnabled(True)

        if es_a36:
            espesor = float(self.spn_espesor.value())
            if espesor <= 0:
                self.rule_card.show_empty("Captura espesor para buscar tarifa A36 por rango.")
                if en_creacion and self.spn_costo is not None:
                    self.spn_costo.setValue(0)
                    self.spn_costo.setReadOnly(True)
                return

            tarifa = self.repo.buscar_precio_a36_placa(espesor)
            if tarifa is None:
                self.rule_card.show_empty("No existe tarifa A36 configurada para este espesor.")
                if en_creacion and self.spn_costo is not None:
                    self.spn_costo.setValue(0)
                    self.spn_costo.setReadOnly(True)
                return

            self.rule_card.show_value(
                formatear_money(tarifa.precio_kg),
                f"Regla A36 placa ({tarifa.rango_label})",
            )
            if en_creacion and self.spn_costo is not None:
                self.spn_costo.setValue(tarifa.precio_kg)
                self.spn_costo.setReadOnly(True)
            return

        regla = self.repo.buscar_regla_costo(
            self.cmb_material.currentText().strip(),
            self.cmb_forma.currentText().strip(),
        )
        if regla is None:
            self.rule_card.show_empty("Sin regla de costo base. Captura costo inicial manual.")
            if en_creacion and self.spn_costo is not None:
                self.spn_costo.setReadOnly(False)
            return

        forma_label = regla.forma_nombre or "Todas las formas"
        self.rule_card.show_value(
            formatear_money(regla.precio_kg),
            f"Regla de costo {regla.material_nombre} / {forma_label}",
        )
        if en_creacion and self.spn_costo is not None:
            self.spn_costo.setValue(regla.precio_kg)
            self.spn_costo.setReadOnly(False)

    def _auto_tipo_densidad(self, texto: str = "") -> None:
        material_key = (texto or "").strip().upper()

        # tipo/categoría configurable por catálogo
        categoria = self._tipos_base_material.get(material_key)
        if categoria is not None:
            self.cmb_tipo.setCurrentText(categoria)

        # densidad — leer desde catálogo/configuración (sin hardcode)
        current_material = self.cmb_material.currentText().strip().upper()
        original_material = (self._material_original.nombre if self._material_original else "").strip().upper()
        if self._material_original is not None and self.spn_densidad.value() > 0 and current_material == original_material:
            return
        densidad = self._densidades_material.get(current_material)
        if densidad is not None:
            self.spn_densidad.setValue(densidad)

    def _abrir_configurar_tarifas(self) -> None:
        if not hasattr(self, "_config_window") or self._config_window is None:
            self._config_window = ConfigWindow(self.repo, self)
            self._config_window.destroyed.connect(lambda: setattr(self, "_config_window", None))
        self._config_window.show()
        self._config_window.raise_()
        self._config_window.activateWindow()
        self._cargar_catalogos()
        self._actualizar_contexto()

    def _limpiar_errores(self) -> None:
        self.field_forma.clear_error()
        self.field_material.clear_error()
        self.field_espesor.clear_error()
        if self.field_costo is not None:
            self.field_costo.clear_error()

    def _validar_y_aceptar(self) -> None:
        self._limpiar_errores()
        hay_error = False

        if not self.cmb_forma.currentText().strip():
            self.field_forma.set_error("La forma del material es obligatoria.")
            hay_error = True
        if not self.cmb_material.currentText().strip():
            self.field_material.set_error("El material es obligatorio.")
            hay_error = True

        if self._es_a36_placa():
            if self.spn_espesor.value() <= 0:
                self.field_espesor.set_error("El espesor es obligatorio para placas A36.")
                hay_error = True

        if self._material_original is None and self.spn_costo is not None and self.spn_costo.value() <= 0:
            self.field_costo.set_error("El costo inicial debe ser mayor a 0.")
            hay_error = True

        if hay_error:
            return
        self.guardado.emit(self.obtener_material(), self.obtener_costo_inicial())
        self.accept()

    def _generar_codigo(self) -> str:
        if self._material_original is not None:
            return self._material_original.codigo
        return self.repo.generar_codigo_material(
            self.cmb_material.currentText().strip(),
            self.cmb_forma.currentText().strip(),
        )

    def obtener_material(self) -> Material:
        base = self._material_original
        material_nombre = self.cmb_material.currentText().strip()
        forma = self.cmb_forma.currentText().strip()
        espesor = float(self.spn_espesor.value()) if self.spn_espesor.value() > 0 else None
        return Material(
            id=base.id if base else None,
            codigo=self._generar_codigo(),
            nombre=material_nombre,
            tipo=self.cmb_tipo.currentText().strip(),
            forma=forma,
            espesor_pulgadas=espesor,
            descripcion=base.descripcion if base else "",
            norma=base.norma if base else "",
            unidad_medida=base.unidad_medida if base else "kg",
            densidad=float(self.spn_densidad.value()) if self.spn_densidad.value() > 0 else None,
            dureza=base.dureza if base else "",
            resistencia_tensil=base.resistencia_tensil if base else None,
            proveedor=base.proveedor if base else "",
            observaciones=base.observaciones if base else "",
            ficha_tecnica_pdf=base.ficha_tecnica_pdf if base else "",
        )

    def obtener_costo_inicial(self) -> Optional[Costo]:
        if self._material_original is not None:
            return None

        nota = "Costo inicial"
        if self._es_a36_placa():
            nota = f'Tarifa A36 placa por espesor {self.spn_espesor.value():.3f}"'
        else:
            regla = self.repo.buscar_regla_costo(
                self.cmb_material.currentText().strip(),
                self.cmb_forma.currentText().strip(),
            )
            if regla is not None:
                forma_label = regla.forma_nombre or "todas las formas"
                nota = f"Regla de costo base {regla.material_nombre} / {forma_label}"

        return Costo(
            id=None,
            material_id=0,
            fecha=date.today(),
            precio_unitario=float(self.spn_costo.value()) if self.spn_costo is not None else 0.0,
            moneda="MXN",
            unidad="kg",
            proveedor="",
            nota=nota,
        )
