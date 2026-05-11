from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


@lru_cache(maxsize=512)
def _colored_icon_cache(name: str, color: str, size: int) -> QIcon:
    svg_path = Path(__file__).resolve().parent / "icons" / f"{name}.svg"
    if not svg_path.exists():
        return QIcon()

    svg_text = svg_path.read_text(encoding="utf-8")
    tinted = svg_text.replace("currentColor", color)

    renderer = QSvgRenderer(QByteArray(tinted.encode("utf-8")))
    if not renderer.isValid():
        return QIcon(str(svg_path))

    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    return QIcon(pix)


def icon(name: str) -> QIcon:
    svg_path = Path(__file__).resolve().parent / "icons" / f"{name}.svg"
    if not svg_path.exists():
        return QIcon()
    return QIcon(str(svg_path))


def icon_colored(name: str, color: str, size: int = 20) -> QIcon:
    return _colored_icon_cache(name, color, size)
