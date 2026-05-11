"""
Ventana principal rediseñada (Fase 2):
- Top bar + action bar.
- Tabla principal en MVC (QTableView + QAbstractTableModel + proxy).
- Panel de detalle con cards.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QDateTime, QEasingCurve, QPropertyAnimation, QRegularExpression, QSettings, QSortFilterProxyModel, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.data.repository import Repository
from app.models.costo import Costo
from app.models.material import Material
from app.models.regla_costo import ReglaCosto
from app.ui.costo_form import CostoForm
from app.ui.delegates import EspesorDelegate, EstadoDelegate, MoneyDelegate
from app.ui.formatting import formatear_money, formatear_pulgadas
from app.ui.icons import icon
from app.ui.material_form import MaterialForm
from app.ui.models import CostosTableModel, MaterialesTableModel
from app.ui.pdf_viewer_dialog import PdfViewerDialog
from app.ui.reporte_dialog import ReporteDialog
from app.ui.theme import TYPOGRAPHY, current_theme_mode, toggle_theme
from app.ui.widgets import Card, DangerButton, FormField, PrimaryButton, SecondaryButton, Toast
from app.ui.windows import ConfigWindow


TEXTO_VACIO = "Sin dato"
PASSWORD_ENV_VAR = "SISTEMA_COSTOS_PASSWORD"
HASH_VACIO_SHA256 = hashlib.sha256(b"").hexdigest()
PASSWORD_REQUERIDO_HASH = hashlib.sha256(
    os.getenv(PASSWORD_ENV_VAR, "").encode("utf-8")
).hexdigest()


class MaterialesProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tipo_filtro = "Todos"

    def set_tipo_filtro(self, tipo: str) -> None:
        self._tipo_filtro = (tipo or "Todos").strip()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        model = self.sourceModel()
        if model is None:
            return False

        if model.is_group_row(source_row):
            return self._group_has_visible_rows(source_row, source_parent)

        return self._data_row_passes(source_row, source_parent)

    def _data_row_passes(self, source_row: int, source_parent) -> bool:
        if not super().filterAcceptsRow(source_row, source_parent):
            return False
        tipo = self._tipo_filtro
        if not tipo or tipo == "Todos":
            return True
        model = self.sourceModel()
        idx = model.index(source_row, 0, source_parent)
        material = model.data(idx, MaterialesTableModel.ROLE_MATERIAL)
        if material is None:
            return False
        tipo_norm = tipo.casefold()
        return (
            (material.nombre or "").casefold() == tipo_norm
            or (material.tipo or "").casefold() == tipo_norm
        )

    def _group_has_visible_rows(self, group_source_row: int, source_parent) -> bool:
        model = self.sourceModel()
        total = len(model._rows)  # evita re-entrancia al override virtual rowCount()
        for i in range(group_source_row + 1, total):
            if model.is_group_row(i):
                break
            if self._data_row_passes(i, source_parent):
                return True
        return False


class MainWindow(QMainWindow):
    def __init__(self, repo: Repository):
        super().__init__()
        self.repo = repo
        self.setWindowTitle("Sistema de Costos - Logística")
        self._material_actual: Optional[Material] = None
        self._settings = QSettings("InnovaX", "SistemaCostos")
        self.config_window: Optional[ConfigWindow] = None
        self.pdf_viewer: Optional[PdfViewerDialog] = None
        self._form_nuevo: Optional[MaterialForm] = None
        self._form_editar: Optional[MaterialForm] = None
        self._form_costo: Optional[CostoForm] = None

        self._build_ui()
        self._configurar_shortcuts()
        self._cargar_tipos()
        self._restaurar_estado_ui()
        self._recargar_materiales()
        self._actualizar_reloj()

        # Animación crossfade del panel de detalle
        self._detalle_opacity = QGraphicsOpacityEffect(self.panel_detalle)
        self._detalle_opacity.setOpacity(1.0)
        self.panel_detalle.setGraphicsEffect(self._detalle_opacity)

        self._detalle_fade_out = QPropertyAnimation(self._detalle_opacity, b"opacity", self)
        self._detalle_fade_out.setDuration(120)
        self._detalle_fade_out.setStartValue(1.0)
        self._detalle_fade_out.setEndValue(0.0)
        self._detalle_fade_out.setEasingCurve(QEasingCurve.Type.InQuad)

        self._detalle_fade_in = QPropertyAnimation(self._detalle_opacity, b"opacity", self)
        self._detalle_fade_in.setDuration(200)
        self._detalle_fade_in.setStartValue(0.0)
        self._detalle_fade_in.setEndValue(1.0)
        self._detalle_fade_in.setEasingCurve(QEasingCurve.Type.OutQuad)

        self._pending_detail_material: Optional[Material] = None

    @staticmethod
    def _es_a36_placa(material: Material) -> bool:
        return material.nombre.strip().upper() == "A36" and material.forma.strip().upper() == "PLACA"

    def _build_ui(self) -> None:
        self._build_top_bar()
        self._build_action_bar()
        self._build_panel_central()
        self._build_status_bar()

    def _build_top_bar(self) -> None:
        self.top_bar = QToolBar("TopBar")
        self.top_bar.setObjectName("topBar")
        self.top_bar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.top_bar)

        lbl_titulo = QLabel("Sistema de Costos")
        lbl_titulo.setObjectName("appTitle")
        title_font = QFont()
        title_font.setPixelSize(TYPOGRAPHY.xl)
        title_font.setWeight(QFont.Weight.DemiBold)
        lbl_titulo.setFont(title_font)

        self.input_busqueda = QLineEdit()
        self.input_busqueda.setPlaceholderText("Buscar por código, material, forma o espesor")
        self.input_busqueda.setClearButtonEnabled(True)
        self.input_busqueda.setMinimumWidth(360)
        self.input_busqueda.textChanged.connect(self._on_filtros_cambio)
        self.input_busqueda.setAccessibleName("Campo de búsqueda de materiales")

        self.combo_tipo = QComboBox()
        self.combo_tipo.currentTextChanged.connect(self._on_filtros_cambio)
        self.combo_tipo.setMinimumWidth(180)
        self.combo_tipo.setAccessibleName("Filtro de tipo de material")

        self.btn_tema = QPushButton()
        self.btn_tema.setObjectName("btnTema")
        self.btn_tema.setFixedSize(32, 32)
        self.btn_tema.clicked.connect(self._conmutar_tema)
        self._refrescar_icono_tema()

        self.lbl_usuario_top = QLabel("Operador")
        self.lbl_usuario_top.setObjectName("lblUsuarioTop")

        self.top_bar.addWidget(lbl_titulo)
        self.top_bar.addSeparator()
        self.top_bar.addWidget(self.input_busqueda)
        self.top_bar.addWidget(self.combo_tipo)
        self.top_bar.addSeparator()
        self.top_bar.addWidget(self.btn_tema)
        self.top_bar.addWidget(self.lbl_usuario_top)

    def _build_action_bar(self) -> None:
        self.action_bar = QToolBar("ActionBar")
        self.action_bar.setObjectName("actionBar")
        self.action_bar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.action_bar)

        self.btn_nuevo = PrimaryButton("Nuevo")
        self.btn_nuevo.setIcon(icon("plus"))
        self.btn_nuevo.setToolTip("Nuevo material (Ctrl+N)")
        self.btn_nuevo.clicked.connect(self._nuevo_material)

        self.btn_editar = SecondaryButton("Editar")
        self.btn_editar.setIcon(icon("edit-2"))
        self.btn_editar.setToolTip("Editar material seleccionado (Ctrl+E)")
        self.btn_editar.clicked.connect(self._editar_material)

        self.btn_eliminar = DangerButton("Eliminar")
        self.btn_eliminar.setIcon(icon("trash-2"))
        self.btn_eliminar.setToolTip("Eliminar material seleccionado (Supr)")
        self.btn_eliminar.clicked.connect(self._eliminar_material)

        self.btn_reporte = SecondaryButton("Reporte")
        self.btn_reporte.setIcon(icon("download"))
        self.btn_reporte.setToolTip("Generar reporte PDF (Ctrl+R)")
        self.btn_reporte.clicked.connect(self._abrir_reporte_pdf)

        self.btn_configuracion = SecondaryButton("Configuración")
        self.btn_configuracion.setIcon(icon("settings"))
        self.btn_configuracion.setToolTip("Configuración de tarifas A36 (Ctrl+,)")
        self.btn_configuracion.clicked.connect(self._abrir_modulo_tarifas_a36)

        self.action_bar.addWidget(self.btn_nuevo)
        self.action_bar.addWidget(self.btn_editar)
        self.action_bar.addWidget(self.btn_eliminar)
        self.action_bar.addSeparator()
        self.action_bar.addWidget(self.btn_reporte)
        self.action_bar.addWidget(self.btn_configuracion)

    def _build_panel_central(self) -> None:
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)

        self._build_tabla_materiales()
        self._build_panel_detalle()

        self.splitter.addWidget(self.tabla_materiales)
        self.splitter.addWidget(self.panel_detalle)
        self.splitter.setSizes([744, 456])

        self._error_bar = QFrame()
        self._error_bar.setObjectName("errorBar")
        self._error_bar.hide()
        err_layout = QHBoxLayout(self._error_bar)
        err_layout.setContentsMargins(12, 6, 12, 6)
        self._error_bar_lbl = QLabel()
        self._error_bar_lbl.setWordWrap(True)
        btn_dismiss = QPushButton("✕")
        btn_dismiss.setFixedSize(20, 20)
        btn_dismiss.setObjectName("btnDismissError")
        btn_dismiss.setToolTip("Cerrar")
        btn_dismiss.clicked.connect(self._error_bar.hide)
        err_layout.addWidget(self._error_bar_lbl, 1)
        err_layout.addWidget(btn_dismiss)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self._error_bar)
        central_layout.addWidget(self.splitter, 1)
        self.setCentralWidget(central)

    def _mostrar_error_persistente(self, mensaje: str) -> None:
        self._error_bar_lbl.setText(mensaje)
        self._error_bar.show()

    def _build_tabla_materiales(self) -> None:
        self.model_materiales = MaterialesTableModel(self, espesor_display_resolver=self._texto_espesor_tabla)
        self.proxy_materiales = MaterialesProxyModel(self)
        self.proxy_materiales.setSourceModel(self.model_materiales)
        self.proxy_materiales.setFilterKeyColumn(-1)
        self.proxy_materiales.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.tabla_materiales = QTableView()
        self.tabla_materiales.setModel(self.proxy_materiales)
        self.tabla_materiales.setAlternatingRowColors(True)
        self.tabla_materiales.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_materiales.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla_materiales.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self.tabla_materiales.horizontalHeader()
        header.setMinimumSectionSize(92)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.resizeSection(0, 130)
        self.tabla_materiales.verticalHeader().setDefaultSectionSize(28)
        self.tabla_materiales.verticalHeader().setVisible(False)
        self.tabla_materiales.setSortingEnabled(False)
        self.tabla_materiales.setAccessibleName("Tabla principal de materiales")

        self.tabla_materiales.setItemDelegateForColumn(3, EspesorDelegate(self.tabla_materiales))
        self.tabla_materiales.setItemDelegateForColumn(4, MoneyDelegate(self.tabla_materiales))
        self.tabla_materiales.setItemDelegateForColumn(5, EstadoDelegate(self.tabla_materiales))

        self.tabla_materiales.selectionModel().currentRowChanged.connect(self._on_material_current_changed)
        self.tabla_materiales.doubleClicked.connect(self._on_material_double_clicked)

    def _build_panel_detalle(self) -> None:
        self.panel_detalle = QWidget()
        root = QVBoxLayout(self.panel_detalle)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        card_ident = Card()
        header_ident = QHBoxLayout()
        header_ident.setContentsMargins(0, 0, 0, 0)
        lbl_ident = QLabel("Identificación")
        lbl_ident.setProperty("section-title", True)
        self.btn_editar_inline = SecondaryButton("Editar")
        self.btn_editar_inline.setIcon(icon("edit-2"))
        self.btn_editar_inline.setToolTip("Editar material (Ctrl+E)")
        self.btn_editar_inline.setFixedHeight(26)
        self.btn_editar_inline.setEnabled(False)
        self.btn_editar_inline.clicked.connect(self._editar_material)
        header_ident.addWidget(lbl_ident)
        header_ident.addStretch(1)
        header_ident.addWidget(self.btn_editar_inline)
        card_ident.body.addLayout(header_ident)

        self.txt_det_codigo = self._readonly_input("txt_det_codigo")
        self.txt_det_material = self._readonly_input("txt_det_material")
        self.txt_det_forma = self._readonly_input("txt_det_forma")
        self.txt_det_espesor = self._readonly_input("txt_det_espesor")

        card_ident.body.addWidget(FormField("Código", self.txt_det_codigo))
        card_ident.body.addWidget(FormField("Material", self.txt_det_material))
        card_ident.body.addWidget(FormField("Forma", self.txt_det_forma))
        card_ident.body.addWidget(FormField("Espesor", self.txt_det_espesor))

        card_costo = Card()
        lbl_costo = QLabel("Costo vigente")
        lbl_costo.setProperty("section-title", True)
        card_costo.body.addWidget(lbl_costo)

        self.lbl_costo_actual = QLabel(TEXTO_VACIO)
        mono = QFont(TYPOGRAPHY.family_mono)
        mono.setPixelSize(TYPOGRAPHY._2xl)
        mono.setWeight(QFont.Weight.DemiBold)
        self.lbl_costo_actual.setFont(mono)

        self.lbl_costo_fecha = QLabel(TEXTO_VACIO)
        self.lbl_costo_fecha.setProperty("muted", True)

        card_costo.body.addWidget(self.lbl_costo_actual)
        card_costo.body.addWidget(self.lbl_costo_fecha)

        card_ficha = Card()
        lbl_ficha_title = QLabel("Ficha técnica")
        lbl_ficha_title.setProperty("section-title", True)
        card_ficha.body.addWidget(lbl_ficha_title)

        self.lbl_ficha_nombre = QLabel(TEXTO_VACIO)
        self.lbl_ficha_nombre.setProperty("muted", True)
        card_ficha.body.addWidget(self.lbl_ficha_nombre)

        self.empty_ficha = QWidget()
        empty_layout = QHBoxLayout(self.empty_ficha)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.setSpacing(8)
        self.lbl_empty_ficha = QLabel("No hay ficha técnica adjunta")
        self.lbl_empty_ficha.setProperty("muted", True)
        self.btn_adjuntar_ficha = PrimaryButton("Adjuntar ficha")
        self.btn_adjuntar_ficha.setIcon(icon("file-text"))
        self.btn_adjuntar_ficha.clicked.connect(self._adjuntar_ficha_pdf_material_actual)
        empty_layout.addWidget(self.lbl_empty_ficha)
        empty_layout.addWidget(self.btn_adjuntar_ficha)
        empty_layout.addStretch(1)
        card_ficha.body.addWidget(self.empty_ficha)

        ficha_btns = QHBoxLayout()
        self.btn_ver_ficha = SecondaryButton("Ver ficha")
        self.btn_ver_ficha.setIcon(icon("file-text"))
        self.btn_ver_ficha.clicked.connect(self._abrir_ficha_pdf_material_actual)
        self.btn_ver_ficha.setAccessibleName("Botón ver ficha técnica")

        self.btn_cambiar_ficha = SecondaryButton("Cambiar")
        self.btn_cambiar_ficha.clicked.connect(self._adjuntar_ficha_pdf_material_actual)
        self.btn_cambiar_ficha.setAccessibleName("Botón cambiar ficha técnica")

        self.btn_eliminar_ficha = DangerButton("Eliminar")
        self.btn_eliminar_ficha.setIcon(icon("trash-2"))
        self.btn_eliminar_ficha.clicked.connect(self._eliminar_ficha_pdf_material_actual)
        self.btn_eliminar_ficha.setAccessibleName("Botón eliminar ficha técnica")

        ficha_btns.addWidget(self.btn_ver_ficha)
        ficha_btns.addWidget(self.btn_cambiar_ficha)
        ficha_btns.addWidget(self.btn_eliminar_ficha)
        ficha_btns.addStretch(1)
        card_ficha.body.addLayout(ficha_btns)

        card_hist = Card()
        lbl_hist = QLabel("Historial de costos")
        lbl_hist.setProperty("section-title", True)
        card_hist.body.addWidget(lbl_hist)

        row_hist = QHBoxLayout()
        self.btn_add_costo = PrimaryButton("Agregar costo")
        self.btn_add_costo.setIcon(icon("plus"))
        self.btn_add_costo.clicked.connect(self._agregar_costo)
        self.btn_add_costo.setAccessibleName("Botón agregar costo")
        row_hist.addWidget(self.btn_add_costo)
        row_hist.addStretch(1)
        card_hist.body.addLayout(row_hist)

        self.model_costos = CostosTableModel(self)
        self.tabla_costos = QTableView()
        self.tabla_costos.setModel(self.model_costos)
        self.tabla_costos.setAlternatingRowColors(True)
        self.tabla_costos.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_costos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_costos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_costos.verticalHeader().setDefaultSectionSize(28)
        self.tabla_costos.verticalHeader().setVisible(False)
        self.tabla_costos.setItemDelegateForColumn(1, MoneyDelegate(self.tabla_costos))
        card_hist.body.addWidget(self.tabla_costos)

        root.addWidget(card_ident)
        root.addWidget(card_costo)
        root.addWidget(card_ficha)
        root.addWidget(card_hist, 1)

        self._limpiar_detalle()

    @staticmethod
    def _readonly_input(object_name: str) -> QLineEdit:
        field = QLineEdit()
        field.setObjectName(object_name)
        field.setReadOnly(True)
        field.setFrame(False)
        field.setFocusPolicy(Qt.NoFocus)
        field.setProperty("readonly-display", True)
        return field

    def _build_status_bar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)

        db_label = "Conectado a Pervasive"
        self.lbl_status_db = QLabel(db_label)
        self.lbl_status_count = QLabel("0 materiales")
        self.lbl_status_right = QLabel("")

        status.addWidget(self.lbl_status_db, 0)
        status.addWidget(self.lbl_status_count, 1)
        status.addPermanentWidget(self.lbl_status_right, 0)

        self.reloj_timer = QTimer(self)
        self.reloj_timer.timeout.connect(self._actualizar_reloj)
        self.reloj_timer.start(60_000)

    def _configurar_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.input_busqueda.setFocus)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._nuevo_material)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self._editar_material)
        QShortcut(QKeySequence("Delete"), self, activated=self._eliminar_material)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self._abrir_modulo_tarifas_a36)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=self._agregar_costo)
        QShortcut(QKeySequence("Ctrl+P"), self, activated=self._abrir_ficha_pdf_material_actual)
        QShortcut(QKeySequence("F5"), self, activated=self._recargar_materiales)
        QShortcut(QKeySequence("Ctrl+Shift+T"), self, activated=self._conmutar_tema)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self._abrir_reporte_pdf)

    def _restaurar_estado_ui(self) -> None:
        geometry = self._settings.value("main_window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

        sizes = self._settings.value("main_window/splitter_sizes")
        if isinstance(sizes, list) and len(sizes) == 2:
            try:
                self.splitter.setSizes([int(sizes[0]), int(sizes[1])])
            except (TypeError, ValueError):
                pass

        filtro_tipo = str(self._settings.value("main_window/filtro_tipo", "Todos"))
        idx = self.combo_tipo.findText(filtro_tipo)
        if idx >= 0:
            self.combo_tipo.setCurrentIndex(idx)

        busqueda = str(self._settings.value("main_window/busqueda", ""))
        self.input_busqueda.setText(busqueda)

    def _guardar_estado_ui(self) -> None:
        self._settings.setValue("main_window/geometry", self.saveGeometry())
        self._settings.setValue("main_window/splitter_sizes", self.splitter.sizes())
        self._settings.setValue("main_window/filtro_tipo", self.combo_tipo.currentText())
        self._settings.setValue("main_window/busqueda", self.input_busqueda.text())

    def closeEvent(self, event: QCloseEvent) -> None:
        self._guardar_estado_ui()
        super().closeEvent(event)

    def _on_filtros_cambio(self) -> None:
        texto = self.input_busqueda.text().strip()
        if texto:
            regex = QRegularExpression(
                QRegularExpression.escape(texto),
                QRegularExpression.CaseInsensitiveOption,
            )
            self.proxy_materiales.setFilterRegularExpression(regex)
        else:
            self.proxy_materiales.setFilterRegularExpression(QRegularExpression())

        self.proxy_materiales.set_tipo_filtro(self.combo_tipo.currentText())
        self._actualizar_status_contador()

    def _cargar_tipos(self) -> None:
        self.combo_tipo.blockSignals(True)
        self.combo_tipo.clear()
        tipos_catalogo = [item.nombre for item in self.repo.listar_catalogo_materiales()]
        tipos_bd = self.repo.tipos_material()
        tipos = ["Todos"] + tipos_catalogo + [t for t in tipos_bd if t not in tipos_catalogo]
        self.combo_tipo.addItems(tipos)
        self.combo_tipo.blockSignals(False)

    def _recargar_materiales(self) -> None:
        selected_id = self._material_actual.id if self._material_actual and self._material_actual.id else None

        self.lbl_status_count.setText("Cargando...")
        QApplication.processEvents()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            materiales = self.repo.listar_materiales(filtro_tipo="Todos", busqueda=None)
            filas: list[tuple[Material, Costo | None]] = [
                (m, self.repo.costo_actual(m.id) if m.id is not None else None)
                for m in materiales
            ]
            self.model_materiales.cargar(filas)
        except Exception as error:
            self._mostrar_error_persistente(f"Error al cargar materiales: {error}")
        finally:
            QApplication.restoreOverrideCursor()

        self._on_filtros_cambio()
        self._restaurar_seleccion(selected_id)
        self._actualizar_status_contador()
        self._refrescar_configuracion()

    def _refrescar_configuracion(self) -> None:
        if self.config_window is None:
            return
        refrescar = getattr(self.config_window, "refrescar_datos", None)
        if callable(refrescar):
            refrescar()

    def _restaurar_seleccion(self, material_id: int | None) -> None:
        if material_id is None:
            self._limpiar_detalle()
            return

        for row in range(self.model_materiales.rowCount()):
            if self.model_materiales.is_group_row(row):
                continue
            idx_source = self.model_materiales.index(row, 0)
            source_id = self.model_materiales.data(idx_source, Qt.UserRole)
            if source_id != material_id:
                continue
            idx_proxy = self.proxy_materiales.mapFromSource(idx_source)
            if not idx_proxy.isValid():
                continue
            self.tabla_materiales.selectRow(idx_proxy.row())
            self._mostrar_detalle(self.model_materiales.material_en_fila(row))
            return

        self._limpiar_detalle()

    def _material_desde_proxy_index(self, idx_proxy) -> Optional[Material]:
        if not idx_proxy.isValid():
            return None
        idx_source = self.proxy_materiales.mapToSource(idx_proxy)
        return self.model_materiales.material_en_fila(idx_source.row())

    def _on_material_current_changed(self, current, _previous) -> None:
        material = self._material_desde_proxy_index(current)
        if material is None:
            self._limpiar_detalle()
            return
        self._animar_cambio_detalle(material)

    def _animar_cambio_detalle(self, material: Material) -> None:
        """Crossfade: fade-out rápido → actualiza datos → fade-in."""
        if self._detalle_fade_out.state() == QPropertyAnimation.State.Running:
            self._detalle_fade_out.stop()
        if self._detalle_fade_in.state() == QPropertyAnimation.State.Running:
            self._detalle_fade_in.stop()

        self._pending_detail_material = material

        try:
            self._detalle_fade_out.finished.disconnect(self._on_detalle_fade_out_done)
        except RuntimeError:
            pass
        self._detalle_fade_out.finished.connect(self._on_detalle_fade_out_done)
        self._detalle_fade_out.start()

    def _on_detalle_fade_out_done(self) -> None:
        if self._pending_detail_material is not None:
            self._mostrar_detalle(self._pending_detail_material)
            self._pending_detail_material = None
        self._detalle_fade_in.start()

    def _on_material_double_clicked(self, idx_proxy) -> None:
        material = self._material_desde_proxy_index(idx_proxy)
        if material is None:
            return
        self._abrir_ficha_pdf_si_existe(material)

    def _mostrar_detalle(self, material: Optional[Material]) -> None:
        if material is None:
            self._limpiar_detalle()
            return

        self._material_actual = material
        costo_actual = self.repo.costo_actual(material.id) if material.id is not None else None

        self._set_line_value(self.txt_det_codigo, material.codigo)
        self._set_line_value(self.txt_det_material, material.nombre)
        self._set_line_value(self.txt_det_forma, material.forma)
        self._set_line_value(self.txt_det_espesor, self._texto_espesor_detalle(material))

        if costo_actual is None:
            self.lbl_costo_actual.setText(TEXTO_VACIO)
            self.lbl_costo_fecha.setText("Primer costo pendiente")
            self.lbl_costo_fecha.setProperty("muted", True)
        else:
            self.lbl_costo_actual.setText(formatear_money(costo_actual.precio_unitario))
            self.lbl_costo_fecha.setText(f"Actualizado: {costo_actual.fecha:%Y-%m-%d}")
            self.lbl_costo_fecha.setProperty("muted", True)

        if material.ficha_tecnica_pdf:
            self.lbl_ficha_nombre.setText(material.ficha_tecnica_pdf)
            self.lbl_ficha_nombre.setProperty("muted", False)
            self.empty_ficha.hide()
            self.btn_ver_ficha.setEnabled(True)
            self.btn_eliminar_ficha.setEnabled(True)
        else:
            self.lbl_ficha_nombre.setText(TEXTO_VACIO)
            self.lbl_ficha_nombre.setProperty("muted", True)
            self.empty_ficha.show()
            self.btn_ver_ficha.setEnabled(False)
            self.btn_eliminar_ficha.setEnabled(False)

        self.btn_add_costo.setEnabled(True)
        self.btn_editar_inline.setEnabled(True)
        self.btn_cambiar_ficha.setEnabled(True)

        if material.id is not None:
            self._cargar_costos(material.id)

    def _texto_espesor_tabla(self, material: Material) -> str:
        if material.espesor_pulgadas is None:
            return "Sin dato"

        espesor_txt = formatear_pulgadas(material.espesor_pulgadas)
        if not self._es_a36_placa(material):
            return espesor_txt

        rango = self._rango_tarifa_a36(material.espesor_pulgadas)
        return rango or espesor_txt

    def _texto_espesor_detalle(self, material: Material) -> str:
        if material.espesor_pulgadas is None:
            return ""

        espesor_txt = formatear_pulgadas(material.espesor_pulgadas)
        if not self._es_a36_placa(material):
            return espesor_txt

        rango = self._rango_tarifa_a36(material.espesor_pulgadas)
        if not rango:
            return espesor_txt

        return rango

    def _rango_tarifa_a36(self, espesor_pulgadas: float) -> str:
        tarifa = self.repo.buscar_precio_a36_placa(espesor_pulgadas)
        if tarifa is None:
            return ""
        return (tarifa.rango_label or "").strip()

    @staticmethod
    def _set_line_value(widget: QLineEdit, value: str | None) -> None:
        text = (value or "").strip()
        if not text:
            widget.setText(TEXTO_VACIO)
            widget.setProperty("empty", True)
        else:
            widget.setText(text)
            widget.setProperty("empty", False)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _limpiar_detalle(self) -> None:
        self._material_actual = None
        self._set_line_value(self.txt_det_codigo, "")
        self._set_line_value(self.txt_det_material, "")
        self._set_line_value(self.txt_det_forma, "")
        self._set_line_value(self.txt_det_espesor, "")

        self.lbl_costo_actual.setText(TEXTO_VACIO)
        self.lbl_costo_fecha.setText(TEXTO_VACIO)
        self.lbl_ficha_nombre.setText(TEXTO_VACIO)
        self.lbl_ficha_nombre.setProperty("muted", True)
        self.empty_ficha.show()

        self.model_costos.cargar([])

        self.btn_add_costo.setEnabled(False)
        self.btn_editar_inline.setEnabled(False)
        self.btn_ver_ficha.setEnabled(False)
        self.btn_eliminar_ficha.setEnabled(False)
        self.btn_cambiar_ficha.setEnabled(False)

    def _cargar_costos(self, material_id: int) -> None:
        costos = self.repo.listar_costos(material_id)
        self.model_costos.cargar(costos)

    def _actualizar_status_contador(self) -> None:
        total = self.model_materiales.data_row_count()
        visibles = sum(
            1 for i in range(self.proxy_materiales.rowCount())
            if not self.model_materiales.is_group_row(
                self.proxy_materiales.mapToSource(self.proxy_materiales.index(i, 0)).row()
            )
        )
        total_txt = "material" if total == 1 else "materiales"
        visibles_txt = "material" if visibles == 1 else "materiales"
        if visibles == total:
            self.lbl_status_count.setText(f"{total} {total_txt}")
        else:
            self.lbl_status_count.setText(f"{visibles} {visibles_txt} de {total} {total_txt}")

    def _actualizar_reloj(self) -> None:
        ahora = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm")
        self.lbl_status_right.setText(f"Usuario: {self.lbl_usuario_top.text()} · {ahora}")

    def _conmutar_tema(self) -> None:
        toggle_theme(QApplication.instance())
        self._refrescar_icono_tema()

    def _refrescar_icono_tema(self) -> None:
        # Modo actual: muestra el ícono del modo disponible para conmutar.
        self.btn_tema.setIcon(icon("moon") if current_theme_mode() == "light" else icon("sun"))

    def _toast(self, mensaje: str, variante: str = "info") -> None:
        Toast.show_toast(self, mensaje, variante)

    # ---- Acciones ------------------------------------------------------
    def _nuevo_material(self) -> None:
        if self._form_nuevo is not None:
            if self._form_nuevo.isVisible():
                self._form_nuevo.raise_()
                self._form_nuevo.activateWindow()
                return
            self._form_nuevo = None
        self._form_nuevo = MaterialForm(self.repo, self)
        self._form_nuevo.setAttribute(Qt.WA_DeleteOnClose, True)
        self._form_nuevo.guardado.connect(self._on_nuevo_material_guardado)
        self._form_nuevo.finished.connect(lambda _result: setattr(self, "_form_nuevo", None))
        self._form_nuevo.show()

    def _on_nuevo_material_guardado(self, nuevo: Material, costo_inicial) -> None:
        try:
            if costo_inicial is None:
                raise ValueError("El costo inicial es obligatorio para crear un material.")
            self.repo.crear_material_con_costo_inicial(nuevo, costo_inicial)
            self._upsert_regla_costo_desde_material(nuevo, float(costo_inicial.precio_unitario))
            self._cargar_tipos()
            self._recargar_materiales()
            self._toast(f"Material {nuevo.codigo} creado", "success")
        except Exception as error:
            self._toast(f"No se pudo crear: {error}", "error")

    def _upsert_regla_costo_desde_material(self, material: Material, precio_kg: float) -> None:
        material_nombre = (material.nombre or "").strip()
        forma_nombre = (material.forma or "").strip()
        if not material_nombre or not forma_nombre or precio_kg <= 0:
            return
        # A36 placa se gobierna por tarifas de espesor.
        if material_nombre.upper() == "A36" and forma_nombre.upper() == "PLACA":
            return

        reglas = self.repo.listar_reglas_costo()
        target = None
        for regla in reglas:
            if (regla.material_nombre or "").strip().upper() != material_nombre.upper():
                continue
            if (regla.forma_nombre or "").strip().upper() == forma_nombre.upper():
                target = regla
                break

        payload = ReglaCosto(
            id=target.id if target else None,
            material_nombre=material_nombre,
            forma_nombre=forma_nombre,
            precio_kg=float(precio_kg),
        )
        if target is None:
            self.repo.crear_regla_costo(payload)
        else:
            self.repo.actualizar_regla_costo(payload)

    def _editar_material(self) -> None:
        if self._material_actual is None:
            self._toast("Selecciona un material para editar", "info")
            return
        if self._form_editar is not None:
            if self._form_editar.isVisible():
                self._form_editar.raise_()
                self._form_editar.activateWindow()
                return
            self._form_editar = None
        self._form_editar = MaterialForm(self.repo, self, self._material_actual)
        self._form_editar.setAttribute(Qt.WA_DeleteOnClose, True)
        self._form_editar.guardado.connect(self._on_editar_material_guardado)
        self._form_editar.finished.connect(lambda _result: setattr(self, "_form_editar", None))
        self._form_editar.show()

    def _on_editar_material_guardado(self, actualizado: Material, _) -> None:
        if self._material_actual is not None:
            actualizado.id = self._material_actual.id
        try:
            self.repo.actualizar_material(actualizado)
            self._cargar_tipos()
            self._recargar_materiales()
            self._toast(f"Material {actualizado.codigo} actualizado", "success")
        except Exception as error:
            self._toast(f"No se pudo actualizar: {error}", "error")

    def _eliminar_material(self) -> None:
        if self._material_actual is None or self._material_actual.id is None:
            self._toast("Selecciona un material para eliminar", "info")
            return

        respuesta = QMessageBox.question(
            self,
            "Eliminar",
            f"Eliminar el material {self._material_actual.nombre}?\nSe borrará también su historial de costos.",
        )
        if respuesta != QMessageBox.Yes:
            return

        try:
            self.repo.eliminar_material(self._material_actual.id)
            self._recargar_materiales()
            self._toast("Material eliminado", "success")
        except Exception as error:
            self._toast(f"No se pudo eliminar: {error}", "error")

    def _agregar_costo(self) -> None:
        if self._material_actual is None or self._material_actual.id is None:
            self._toast("Selecciona un material para agregar costo", "info")
            return
        if self._form_costo is not None:
            if self._form_costo.isVisible():
                self._form_costo.raise_()
                self._form_costo.activateWindow()
                return
            self._form_costo = None

        precio_default = None
        nota_default = ""
        if self._es_a36_placa(self._material_actual) and self._material_actual.espesor_pulgadas is not None:
            tarifa = self.repo.buscar_precio_a36_placa(self._material_actual.espesor_pulgadas)
            if tarifa is not None:
                precio_default = tarifa.precio_kg
                nota_default = (
                    f'Tarifa A36 placa {tarifa.rango_label} '
                    f'para espesor {self._material_actual.espesor_pulgadas:.3f}"'
                )

        costo_vigente = self.repo.costo_actual(self._material_actual.id)
        proveedores_recientes = self.repo.listar_proveedores_historicos()

        self._form_costo = CostoForm(
            material=self._material_actual,
            costo_vigente=costo_vigente,
            proveedores_recientes=proveedores_recientes,
            parent=self,
            precio_default=precio_default,
            nota_default=nota_default,
        )
        self._form_costo.setAttribute(Qt.WA_DeleteOnClose, True)
        self._form_costo.guardado.connect(self._on_costo_guardado)
        self._form_costo.finished.connect(lambda _result: setattr(self, "_form_costo", None))
        self._form_costo.show()

    def _on_costo_guardado(self, costo: Costo) -> None:
        if self._material_actual is None or self._material_actual.id is None:
            return
        costo.material_id = self._material_actual.id
        try:
            self.repo.agregar_costo(costo)
            self._upsert_regla_costo_desde_material(self._material_actual, float(costo.precio_unitario))
            self._cargar_costos(self._material_actual.id)
            self._recargar_materiales()
            self._toast("Costo agregado", "success")
        except Exception as error:
            self._toast(f"No se pudo guardar: {error}", "error")

    def _abrir_ficha_pdf_si_existe(self, material: Material) -> None:
        if material.id is None:
            return

        ficha = self.repo.obtener_ficha_tecnica_pdf(material.id)
        if ficha is None:
            self._toast("Este material no tiene ficha técnica", "info")
            return

        nombre_archivo, contenido_pdf = ficha
        try:
            self.pdf_viewer = PdfViewerDialog(
                titulo=f"Ficha técnica - {material.codigo}",
                nombre_archivo=nombre_archivo,
                contenido_pdf=contenido_pdf,
                parent=self,
            )
            self.pdf_viewer.show()
            self.pdf_viewer.raise_()
            self.pdf_viewer.activateWindow()
        except Exception as error:
            self._toast(f"No se pudo abrir el PDF: {error}", "error")

    def _abrir_ficha_pdf_material_actual(self) -> None:
        if self._material_actual is None:
            self._toast("Selecciona un material", "info")
            return
        self._abrir_ficha_pdf_si_existe(self._material_actual)

    def _abrir_reporte_pdf(self) -> None:
        dlg = ReporteDialog(self.repo, self)
        dlg.exec()

    def _adjuntar_ficha_pdf(self, material: Material) -> None:
        if material.id is None:
            return

        ruta_pdf, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar ficha técnica PDF",
            "",
            "Archivos PDF (*.pdf)",
        )
        if not ruta_pdf:
            return

        try:
            with open(ruta_pdf, "rb") as file_obj:
                contenido_pdf = file_obj.read()
            if not contenido_pdf:
                raise ValueError("El PDF seleccionado está vacío.")

            nombre_archivo = os.path.basename(ruta_pdf)
            self.repo.actualizar_ficha_tecnica_pdf(material.id, nombre_archivo, contenido_pdf)
            refrescado = self.repo.obtener_material(material.id)
            if refrescado is not None:
                self._mostrar_detalle(refrescado)
            self._toast("Ficha técnica actualizada", "success")
        except Exception as error:
            self._toast(f"No se pudo guardar la ficha técnica: {error}", "error")

    def _adjuntar_ficha_pdf_material_actual(self) -> None:
        if self._material_actual is None:
            self._toast("Selecciona un material", "info")
            return
        self._adjuntar_ficha_pdf(self._material_actual)

    def _eliminar_ficha_pdf_material_actual(self) -> None:
        if self._material_actual is None or self._material_actual.id is None:
            self._toast("Selecciona un material", "info")
            return
        if not self._material_actual.ficha_tecnica_pdf:
            self._toast("Ese material no tiene ficha cargada", "info")
            return

        respuesta = QMessageBox.question(
            self,
            "Eliminar ficha técnica",
            f'Eliminar la ficha PDF de "{self._material_actual.nombre}"?',
        )
        if respuesta != QMessageBox.Yes:
            return

        password, ok = QInputDialog.getText(
            self,
            "Contraseña requerida",
            "Ingresa la contraseña para eliminar la ficha PDF:",
            QLineEdit.Password,
        )
        if not ok:
            return

        if PASSWORD_REQUERIDO_HASH == HASH_VACIO_SHA256:
            self._toast(f"No se encontró la variable de entorno {PASSWORD_ENV_VAR}", "error")
            return

        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if password_hash != PASSWORD_REQUERIDO_HASH:
            self._toast("Contraseña incorrecta", "error")
            return

        try:
            self.repo.eliminar_ficha_tecnica_pdf(self._material_actual.id)
            refrescado = self.repo.obtener_material(self._material_actual.id)
            if refrescado is not None:
                self._mostrar_detalle(refrescado)
            self._toast("Ficha técnica eliminada", "success")
        except Exception as error:
            self._toast(f"No se pudo eliminar la ficha técnica: {error}", "error")

    def _abrir_modulo_tarifas_a36(self) -> None:
        if self.config_window is None:
            self.config_window = ConfigWindow(self.repo, self)
            self.config_window.setAttribute(Qt.WA_DeleteOnClose, True)
            self.config_window.destroyed.connect(self._on_config_window_destroyed)
        self._refrescar_configuracion()
        self.config_window.show()
        self.config_window.raise_()
        self.config_window.activateWindow()

    def _on_config_window_destroyed(self) -> None:
        self.config_window = None
