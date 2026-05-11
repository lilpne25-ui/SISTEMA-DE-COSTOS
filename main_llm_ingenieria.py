"""
App de Ingenieria - LLM SOLID -> GLOBAL SHOP
Ejecutar: python main_llm_ingenieria.py
"""
from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.ui.theme import apply_theme
from app.ui.windows.config_window import ConfigWindow
from main import build_repository


LLM_SECTION_INDEX = 4


def main() -> int:
    try:
        app = QApplication(sys.argv)
        apply_theme(app)
        app.setApplicationName("LLM SOLID -> GLOBAL SHOP")

        repo = build_repository()
        window = ConfigWindow(repo)
        window.setWindowTitle("LLM SOLID -> GLOBAL SHOP - Ingenieria")
        window.resize(1240, 760)

        # App separada de Ingenieria: muestra unicamente el modulo LLM.
        if hasattr(window, "nav"):
            window.nav.hide()
        if hasattr(window, "stack") and window.stack.count() > LLM_SECTION_INDEX:
            window.stack.setCurrentIndex(LLM_SECTION_INDEX)

        window.show()
        return app.exec()
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "Error de inicio", str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
