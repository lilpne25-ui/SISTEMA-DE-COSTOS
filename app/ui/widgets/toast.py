from __future__ import annotations

from typing import Literal

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    QTimer,
    Qt,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget


class Toast(QWidget):
    def __init__(
        self,
        parent: QWidget,
        texto: str,
        variante: Literal["success", "error", "info"] = "info",
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setProperty("toast", True)
        self.setProperty("variant", variante)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(0)

        self.lbl_texto = QLabel(texto)
        self.lbl_texto.setWordWrap(True)
        layout.addWidget(self.lbl_texto)

        # ---- Fade in/out con QPropertyAnimation -----------------------
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_in = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_in.setDuration(250)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_out.setDuration(400)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self._on_fade_out_done)

        parent.installEventFilter(self)
        self.adjustSize()
        self._reposicionar()

        # Arranca fade-out después de 3.6s (total visible ~4s con fade-in)
        QTimer.singleShot(3600, self._iniciar_fade_out)

    def _iniciar_fade_out(self) -> None:
        if self.isVisible():
            self._fade_out.start()

    def _on_fade_out_done(self) -> None:
        self.close()
        self.deleteLater()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._fade_in.start()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.parent() and event.type() in (QEvent.Resize, QEvent.Move):
            self._reposicionar()
        return super().eventFilter(watched, event)

    def _reposicionar(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        margin = 16
        global_pos = parent.mapToGlobal(parent.rect().bottomRight())
        x = global_pos.x() - self.width() - margin
        y = global_pos.y() - self.height() - margin
        self.move(max(0, x), max(0, y))

    @staticmethod
    def show_toast(parent: QWidget, texto: str, variante: Literal["success", "error", "info"] = "info") -> None:
        toast = Toast(parent, texto, variante)
        toast.show()
        toast.raise_()
