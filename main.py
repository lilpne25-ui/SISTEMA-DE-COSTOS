"""
Sistema de Costos - Punto de entrada
Ejecutar:  python main.py
"""
import os
import sys
from PySide6.QtWidgets import QApplication, QMessageBox

from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme
from app.data.repository import Repository
from app.data.pervasive_repository import PervasiveRepository


_PV_SERVER = "192.168.1.168"
_PV_DBQ = r"C:\USERS\TI\DESKTOP"
_PV_USER = "Master"
_PV_PASSWORD = "COSTPP"


def build_repository() -> Repository:
    backend = os.getenv("SISTEMA_COSTOS_DB_BACKEND", "pervasive").strip().lower()
    if backend and backend not in {"pervasive", "psql", "zen", "actian"}:
        raise RuntimeError(
            f"Backend no soportado: '{backend}'. Usa SISTEMA_COSTOS_DB_BACKEND=pervasive"
        )

    server = os.getenv("SISTEMA_COSTOS_PERVASIVE_SERVER", _PV_SERVER).strip()
    dbq = os.getenv("SISTEMA_COSTOS_PERVASIVE_DBQ", _PV_DBQ).strip()
    user = os.getenv("SISTEMA_COSTOS_PERVASIVE_USER", _PV_USER).strip()
    pwd = os.getenv("SISTEMA_COSTOS_PERVASIVE_PASSWORD", _PV_PASSWORD).strip()
    repo = PervasiveRepository(server=server, dbq=dbq, user=user, password=pwd)
    repo.precargar_catalogo_materiales()
    return repo


def main() -> int:
    try:
        app = QApplication(sys.argv)
        apply_theme(app)
        app.setApplicationName("Sistema de Costos")

        repo = build_repository()
        window = MainWindow(repo)
        window.resize(1200, 720)
        window.show()
        return app.exec()
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        # Error amigable de inicio para despliegues productivos.
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "Error de inicio", str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())



