"""Visor interno de PDF rediseñado (no modal)."""

from __future__ import annotations

import shutil
import tempfile
from contextlib import ExitStack
from pathlib import Path

from PySide6.QtCore import QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QKeySequence, QPainter, QShortcut
from PySide6.QtPdf import QPdfDocument, QPdfSearchModel
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.icons import icon_colored
from app.ui.theme import DARK, TYPOGRAPHY


class PdfViewerDialog(QDialog):
    def __init__(self, titulo: str, nombre_archivo: str, contenido_pdf: bytes, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(1020, 740)
        self.setModal(False)

        self._nombre_archivo = nombre_archivo
        self._contenido_pdf = contenido_pdf
        self._zoom_percent = 100
        self._search_index = -1
        self._cleaned = False
        self._toolbar_icon_color = DARK.text_primary
        self._toolbar_icon_size = QSize(18, 18)

        self._stack = ExitStack()
        self._tmp_dir = Path(
            self._stack.enter_context(
                tempfile.TemporaryDirectory(prefix="sistema_costos_pdf_", ignore_cleanup_errors=True)
            )
        )
        self._pdf_path = self._tmp_dir / self._sanitize_pdf_name(nombre_archivo)
        self._pdf_path.write_bytes(contenido_pdf)

        self._pdf_document = QPdfDocument(self)
        self._pdf_view = QPdfView(self)
        self._pdf_view.setDocument(self._pdf_document)
        self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

        self._search_model = QPdfSearchModel(self)
        self._search_model.setDocument(self._pdf_document)
        self._search_model.searchStringChanged.connect(self._on_search_string_changed)

        self._error_widget = self._build_error_widget()

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self.toolbar = self._build_toolbar()
        root.addWidget(self.toolbar)
        root.addWidget(self._pdf_view, 1)
        root.addWidget(self._error_widget)

        self.footer = QLabel()
        root.addWidget(self.footer)

        self._apply_forced_dark_theme()
        self._bind_events()
        self._load_pdf()
        self._update_footer()
        self._update_page_controls()
        self._setup_shortcuts()
        QTimer.singleShot(0, self._sync_toolbar_overflow_button)

    def _cleanup_resources(self) -> None:
        if self._cleaned:
            return
        self._cleaned = True
        try:
            self._pdf_view.setDocument(None)
            self._pdf_document.close()
        except Exception as exc:
            print(f"[PdfViewerDialog] cierre de documento fallido: {exc}")
        try:
            self._stack.close()
        except Exception as exc:
            print(f"[PdfViewerDialog] limpieza temporal fallida: {exc}")

    @staticmethod
    def _sanitize_pdf_name(nombre_archivo: str) -> str:
        base = "".join(ch for ch in nombre_archivo if ch.isalnum() or ch in ("_", "-", ".")).strip(".")
        if not base.lower().endswith(".pdf"):
            base = (base or "ficha_tecnica") + ".pdf"
        return base

    def _build_error_widget(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(icon_colored("alert-triangle", DARK.warning, 18).pixmap(18, 18))
        self.lbl_error = QLabel("No se pudo cargar el documento PDF.")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setProperty("error-inline", True)

        layout.addWidget(lbl_icon)
        layout.addWidget(self.lbl_error, 1)
        widget.hide()
        return widget

    def _build_toolbar(self) -> QToolBar:
        bar = QToolBar("PDF Tools", self)
        bar.setMovable(False)
        bar.setIconSize(self._toolbar_icon_size)

        self.btn_prev = self._tool_button("chevron-left", "Página anterior", self._prev_page)
        self.btn_next = self._tool_button("chevron-right", "Página siguiente", self._next_page)
        bar.addWidget(self.btn_prev)
        bar.addWidget(self.btn_next)

        self.input_page = QLineEdit("1")
        self.input_page.setFixedWidth(48)
        self.input_page.setAlignment(Qt.AlignCenter)
        self.input_page.returnPressed.connect(self._jump_to_page)
        self.lbl_total_pages = QLabel("/ 0")

        bar.addWidget(self.input_page)
        bar.addWidget(self.lbl_total_pages)
        bar.addSeparator()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar en el documento")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.addAction(icon_colored("search", self._toolbar_icon_color, 18), QLineEdit.LeadingPosition)
        self.search_input.textChanged.connect(self._on_search_changed)
        bar.addWidget(self.search_input)
        bar.addSeparator()

        self.btn_zoom_out = self._tool_button("minus", "Reducir zoom", self.zoom_out)
        self.btn_zoom_in = self._tool_button("plus", "Aumentar zoom", self.zoom_in)
        self.btn_fit = self._tool_button("maximize", "Ajustar ancho", self.zoom_fit_width)

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setFixedWidth(52)
        self.lbl_zoom.setAlignment(Qt.AlignCenter)

        bar.addWidget(self.btn_zoom_out)
        bar.addWidget(self.lbl_zoom)
        bar.addWidget(self.btn_zoom_in)
        bar.addWidget(self.btn_fit)
        bar.addSeparator()

        self.btn_save = self._tool_button("download", "Guardar como", self.guardar_como)
        self.btn_print = self._tool_button("printer", "Imprimir", self.imprimir)
        bar.addWidget(self.btn_save)
        bar.addWidget(self.btn_print)

        return bar

    def _tool_button(self, icon_name: str, tooltip: str, slot) -> QToolButton:
        btn = QToolButton()
        btn.setIcon(icon_colored(icon_name, self._toolbar_icon_color, 18))
        btn.setIconSize(self._toolbar_icon_size)
        btn.setToolTip(tooltip)
        btn.clicked.connect(slot)
        btn.setAutoRaise(False)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _sync_toolbar_overflow_button(self) -> None:
        ext_btn = self.toolbar.findChild(QToolButton, "qt_toolbar_ext_button")
        if ext_btn is None:
            return
        ext_btn.setText("⋯")
        ext_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        ext_btn.setAutoRaise(False)
        ext_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ext_btn.setToolTip("Más acciones")

    def _apply_forced_dark_theme(self) -> None:
        t = DARK
        self.setStyleSheet(
            f"""
            QWidget {{
                background: {t.surface};
                color: {t.text_primary};
                font-size: {TYPOGRAPHY.md}px;
            }}
            QToolBar {{
                background: {t.surface_raised};
                border: 1px solid {t.border};
                spacing: 8px;
                padding: 8px;
            }}
            QToolButton {{
                background: {t.surface_raised};
                color: {t.text_primary};
                border: 1px solid {t.border_strong};
                border-radius: 6px;
                min-width: 34px;
                min-height: 34px;
                max-width: 34px;
                max-height: 34px;
                padding: 4px;
            }}
            QToolButton:hover {{
                border-color: {t.accent};
                background: {t.accent_soft};
            }}
            QToolButton:pressed {{
                border-color: {t.accent_hover};
                background: {t.surface_sunken};
            }}
            QToolBar QToolButton#qt_toolbar_ext_button {{
                color: {t.text_primary};
                font-size: {TYPOGRAPHY.xl}px;
                font-weight: 700;
                letter-spacing: 1px;
                text-align: center;
            }}
            QLineEdit {{
                background: {t.surface_raised};
                border: 1px solid {t.border};
                border-radius: 6px;
                min-height: 32px;
                padding: 4px 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {t.accent};
                outline: 2px solid {t.accent};
            }}
            QLabel[error-inline="true"] {{
                color: {t.warning};
            }}
            """
        )

    def _bind_events(self) -> None:
        nav = self._pdf_view.pageNavigator()
        nav.currentPageChanged.connect(self._on_current_page_changed)
        self._pdf_view.zoomFactorChanged.connect(self._on_zoom_changed)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl++"), self, activated=self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, activated=self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self.zoom_fit_width)
        QShortcut(QKeySequence("Ctrl+1"), self, activated=self.zoom_real)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.search_input.setFocus)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.guardar_como)
        QShortcut(QKeySequence("Ctrl+P"), self, activated=self.imprimir)
        QShortcut(QKeySequence("PgDown"), self, activated=self._next_page)
        QShortcut(QKeySequence("PgUp"), self, activated=self._prev_page)
        QShortcut(QKeySequence("F3"), self, activated=self._search_next)
        QShortcut(QKeySequence("Shift+F3"), self, activated=self._search_prev)
        QShortcut(QKeySequence("Escape"), self, activated=self.close)

    def _load_pdf(self) -> None:
        error = self._pdf_document.load(str(self._pdf_path))
        if error != QPdfDocument.Error.None_:
            self._error_widget.show()
            self._pdf_view.hide()
            self.lbl_error.setText(f"No se pudo cargar el PDF ({error.name}).")
            return

        self._error_widget.hide()
        self._pdf_view.show()
        self.lbl_total_pages.setText(f"/ {self._pdf_document.pageCount()}")
        self._update_page_controls()

    def _on_current_page_changed(self, page: int) -> None:
        self.input_page.setText(str(page + 1))

    def _jump_to_page(self) -> None:
        try:
            page = int(self.input_page.text().strip()) - 1
        except Exception:
            return

        if page < 0 or page >= self._pdf_document.pageCount():
            return
        self._pdf_view.pageNavigator().jump(page, QPointF(0, 0))

    def _next_page(self) -> None:
        page = self._pdf_view.pageNavigator().currentPage()
        if page + 1 < self._pdf_document.pageCount():
            self._pdf_view.pageNavigator().jump(page + 1, QPointF(0, 0))

    def _prev_page(self) -> None:
        page = self._pdf_view.pageNavigator().currentPage()
        if page - 1 >= 0:
            self._pdf_view.pageNavigator().jump(page - 1, QPointF(0, 0))

    def _on_zoom_changed(self, factor: float) -> None:
        self._zoom_percent = int(round(factor * 100))
        self.lbl_zoom.setText(f"{self._zoom_percent}%")

    def _set_zoom(self, value: float) -> None:
        self._pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        self._pdf_view.setZoomFactor(max(0.1, min(value, 8.0)))

    def zoom_in(self) -> None:
        self._set_zoom(self._pdf_view.zoomFactor() * 1.15)

    def zoom_out(self) -> None:
        self._set_zoom(self._pdf_view.zoomFactor() / 1.15)

    def zoom_fit_width(self) -> None:
        self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    def zoom_real(self) -> None:
        self._set_zoom(1.0)

    def _on_search_string_changed(self, _text: str = "") -> None:
        self._search_index = -1

    def _on_search_changed(self, text: str) -> None:
        self._search_model.setSearchString(text)
        self._search_index = -1

    def _search_next(self) -> None:
        total = self._search_model.rowCount()
        if total <= 0:
            return
        self._search_index = (self._search_index + 1) % total
        self._jump_search_result(self._search_index)

    def _search_prev(self) -> None:
        total = self._search_model.rowCount()
        if total <= 0:
            return
        self._search_index = (self._search_index - 1) % total
        self._jump_search_result(self._search_index)

    def _jump_search_result(self, row: int) -> None:
        idx = self._search_model.index(row, 0)
        if not idx.isValid():
            return
        link = self._search_model.resultAtIndex(idx)
        self._pdf_view.pageNavigator().jump(link)

    def guardar_como(self) -> None:
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar PDF como",
            self._nombre_archivo,
            "Archivos PDF (*.pdf)",
        )
        if not target:
            return
        if not target.lower().endswith(".pdf"):
            target += ".pdf"

        shutil.copy(str(self._pdf_path), target)

    def imprimir(self) -> None:
        if self._pdf_document.status() != QPdfDocument.Status.Ready:
            return

        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QDialog.Accepted:
            return

        painter = QPainter(printer)
        try:
            page_count = self._pdf_document.pageCount()
            for page in range(page_count):
                if page > 0:
                    printer.newPage()
                viewport = painter.viewport()
                img = self._pdf_document.render(page, viewport.size())
                painter.drawImage(viewport, img)
        finally:
            painter.end()

    def _update_page_controls(self) -> None:
        page = self._pdf_view.pageNavigator().currentPage()
        self.input_page.setText(str(page + 1 if page >= 0 else 1))
        self.lbl_total_pages.setText(f"/ {self._pdf_document.pageCount()}")

    def _update_footer(self) -> None:
        size = len(self._contenido_pdf)
        if size < 1024 * 1024:
            size_txt = f"{size / 1024:.1f} KB"
        else:
            size_txt = f"{size / (1024 * 1024):.2f} MB"
        self.footer.setText(
            f"{self._nombre_archivo} · {size_txt} · {self._pdf_document.pageCount()} páginas"
        )

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._sync_toolbar_overflow_button()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._cleanup_resources()
        super().closeEvent(event)
