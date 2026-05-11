"""Compatibilidad legacy.

Módulo deprecado en Fase 3: se mantiene para imports antiguos, pero la
configuración ahora vive en app.ui.windows.config_window.ConfigWindow.
"""

from __future__ import annotations

import warnings

from app.ui.windows.config_window import A36PriceForm, CatalogoItemForm, ConfigWindow, ReglaCostoForm


class A36PriceManagerDialog(ConfigWindow):
    def __init__(self, repo, parent=None):
        warnings.warn(
            "A36PriceManagerDialog está deprecado; usa ConfigWindow.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(repo=repo, parent=parent)

    def exec(self) -> int:
        # Compatibilidad con llamadas legacy tipo dialog.exec().
        self.show()
        self.raise_()
        self.activateWindow()
        return 0


__all__ = [
    "ConfigWindow",
    "A36PriceManagerDialog",
    "CatalogoItemForm",
    "ReglaCostoForm",
    "A36PriceForm",
]
