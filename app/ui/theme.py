from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class ColorTokens:
    surface: str
    surface_raised: str
    surface_sunken: str
    border: str
    border_strong: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_soft: str
    danger: str
    danger_soft: str
    warning: str
    warning_soft: str
    success: str
    success_soft: str


@dataclass(frozen=True)
class Typography:
    family_ui: str = "Inter"
    family_mono: str = "JetBrains Mono"
    xs: int = 11
    sm: int = 12
    md: int = 13
    lg: int = 14
    xl: int = 16
    _2xl: int = 20
    _3xl: int = 24


@dataclass(frozen=True)
class Spacing:
    xs: int = 4
    sm: int = 6
    md: int = 8
    lg: int = 12
    xl: int = 16
    xxl: int = 24


@dataclass(frozen=True)
class Radius:
    sm: int = 4
    md: int = 6
    lg: int = 8


LIGHT = ColorTokens(
    surface="#F7F8FA",
    surface_raised="#FFFFFF",
    surface_sunken="#EEF1F5",
    border="#D9DEE6",
    border_strong="#C2CAD6",
    text_primary="#111827",
    text_secondary="#374151",
    text_muted="#6B7280",
    accent="#2563EB",
    accent_hover="#1D4ED8",
    accent_soft="#DBEAFE",
    danger="#DC2626",
    danger_soft="#FEE2E2",
    warning="#B45309",
    warning_soft="#FEF3C7",
    success="#15803D",
    success_soft="#DCFCE7",
)

DARK = ColorTokens(
    surface="#111318",
    surface_raised="#171A21",
    surface_sunken="#0D1015",
    border="#2A2F3A",
    border_strong="#394152",
    text_primary="#E5E7EB",
    text_secondary="#C3CAD5",
    text_muted="#9AA4B2",
    accent="#60A5FA",
    accent_hover="#3B82F6",
    accent_soft="#1E3A8A",
    danger="#F87171",
    danger_soft="#7F1D1D",
    warning="#FBBF24",
    warning_soft="#78350F",
    success="#4ADE80",
    success_soft="#14532D",
)

TYPOGRAPHY = Typography()
SPACING = Spacing()
RADIUS = Radius()

_tokens = LIGHT
_theme_mode = "light"
_settings = QSettings("InnovaX", "SistemaCostos")


def tokens() -> ColorTokens:
    return _tokens


def _registrar_fuentes() -> None:
    fonts_dir = Path(__file__).resolve().parent / "fonts"
    if not fonts_dir.exists():
        return

    for font_path in sorted(fonts_dir.glob("*.ttf")):
        try:
            QFontDatabase.addApplicationFont(str(font_path))
        except Exception:
            continue


def _build_qss(t: ColorTokens) -> str:
    return f"""
    QMainWindow, QDialog, QWidget {{
        background: {t.surface};
        color: {t.text_primary};
        selection-background-color: {t.accent};
        selection-color: #FFFFFF;
        font-size: {TYPOGRAPHY.md}px;
    }}

    QToolBar {{
        background: {t.surface_raised};
        border: 1px solid {t.border};
        spacing: {SPACING.sm}px;
        padding: {SPACING.sm}px;
    }}

    QToolBar#topBar {{
        border-bottom: 1px solid {t.border};
    }}

    QToolBar#actionBar {{
        border-top: 0;
        border-bottom: 1px solid {t.border};
    }}

    QListWidget#configNav {{
        background: {t.surface_raised};
        border: 1px solid {t.border};
        border-radius: {RADIUS.md}px;
        padding: {SPACING.sm}px;
    }}

    QListWidget#configNav::item {{
        border-radius: {RADIUS.md}px;
        padding: {SPACING.sm}px {SPACING.md}px;
        color: {t.text_secondary};
    }}

    QListWidget#configNav::item:selected {{
        background: {t.accent_soft};
        color: {t.accent};
    }}

    QToolBar::separator {{
        background: {t.border};
        width: 1px;
        margin: {SPACING.xs}px {SPACING.sm}px;
    }}

    QStatusBar {{
        background: {t.surface_raised};
        border-top: 1px solid {t.border};
    }}

    QFrame#errorBar {{
        background: {t.danger_soft};
        border-bottom: 1px solid {t.danger};
    }}
    QFrame#errorBar QLabel {{
        color: {t.danger};
        font-size: {TYPOGRAPHY.sm}px;
    }}
    QPushButton#btnDismissError {{
        background: transparent;
        border: none;
        color: {t.danger};
        font-size: {TYPOGRAPHY.md}px;
        font-weight: bold;
        padding: 0;
    }}
    QPushButton#btnDismissError:hover {{
        color: {t.text_primary};
    }}

    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QDateEdit,
    QTextEdit {{
        background: {t.surface_raised};
        border: 1px solid {t.border};
        border-radius: {RADIUS.md}px;
        padding: {SPACING.md}px {SPACING.lg}px;
        color: {t.text_primary};
    }}

    QLineEdit[readonly-display="true"] {{
        background: {t.surface_sunken};
    }}

    QLineEdit[empty="true"] {{
        color: {t.text_muted};
    }}

    QLineEdit:disabled,
    QComboBox:disabled,
    QDoubleSpinBox:disabled,
    QDateEdit:disabled,
    QTextEdit:disabled {{
        background: {t.surface_sunken};
        color: {t.text_muted};
    }}

    QLineEdit:focus,
    QComboBox:focus,
    QDoubleSpinBox:focus,
    QDateEdit:focus,
    QTextEdit:focus,
    QPushButton:focus,
    QTableView:focus,
    QTabBar::tab:focus {{
        border: 1px solid {t.accent};
        outline: 2px solid {t.accent};
    }}

    QPushButton {{
        background: {t.surface_raised};
        border: 1px solid {t.border};
        border-radius: {RADIUS.md}px;
        color: {t.text_primary};
        padding: {SPACING.sm}px {SPACING.lg}px;
    }}

    QPushButton#btnTema {{
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
        padding: 2px;
    }}

    QPushButton[chip="true"] {{
        border-radius: {RADIUS.lg}px;
        padding: {SPACING.sm}px {SPACING.md}px;
        background: {t.surface_sunken};
        border-color: {t.border};
        color: {t.text_secondary};
    }}

    QPushButton:hover {{
        background: {t.surface_sunken};
        border-color: {t.border_strong};
    }}

    QPushButton:pressed {{
        background: {t.surface_sunken};
    }}

    QPushButton[role="primary"] {{
        background: {t.accent};
        border: 1px solid {t.accent};
        color: #FFFFFF;
    }}

    QPushButton[role="primary"]:hover {{
        background: {t.accent_hover};
        border-color: {t.accent_hover};
    }}

    QPushButton[role="danger"] {{
        background: {t.danger};
        border: 1px solid {t.danger};
        color: #FFFFFF;
    }}

    QPushButton[role="danger"]:hover {{
        background: #B91C1C;
        border-color: #B91C1C;
    }}

    QTableView {{
        background: {t.surface_raised};
        alternate-background-color: {t.surface};
        border: 1px solid {t.border};
        gridline-color: {t.border};
    }}

    QTableView::item {{
        padding: 0 {SPACING.md}px;
        height: 28px;
    }}

    QHeaderView::section {{
        background: {t.surface_sunken};
        color: {t.text_secondary};
        border: 0;
        border-bottom: 1px solid {t.border};
        border-right: 1px solid {t.border};
        padding: {SPACING.sm}px {SPACING.md}px;
    }}

    QSplitter::handle {{
        background: {t.border};
    }}

    QTabWidget::pane {{
        border: 1px solid {t.border};
        border-radius: {RADIUS.md}px;
        top: -1px;
        background: {t.surface_raised};
    }}

    QTabBar::tab {{
        background: {t.surface};
        border: 1px solid {t.border};
        border-bottom: 0;
        border-top-left-radius: {RADIUS.md}px;
        border-top-right-radius: {RADIUS.md}px;
        padding: {SPACING.sm}px {SPACING.lg}px;
        margin-right: {SPACING.xs}px;
        color: {t.text_secondary};
    }}

    QTabBar::tab:selected {{
        background: {t.surface_raised};
        color: {t.text_primary};
        border-color: {t.border_strong};
    }}

    QGroupBox {{
        border: 1px solid {t.border};
        border-radius: {RADIUS.lg}px;
        margin-top: {SPACING.xl}px;
        padding: {SPACING.md}px;
        background: {t.surface_raised};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: {SPACING.md}px;
        padding: 0 {SPACING.xs}px;
        color: {t.text_secondary};
    }}

    QScrollBar:vertical {{
        background: {t.surface};
        width: 12px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical {{
        background: {t.border_strong};
        min-height: 28px;
        border-radius: {RADIUS.sm}px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {t.text_muted};
    }}

    QScrollBar:horizontal {{
        background: {t.surface};
        height: 12px;
        margin: 2px;
    }}

    QScrollBar::handle:horizontal {{
        background: {t.border_strong};
        min-width: 28px;
        border-radius: {RADIUS.sm}px;
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal,
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal,
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: none;
        border: none;
    }}

    QLabel[field-error="true"] {{
        color: {t.danger};
        font-size: {TYPOGRAPHY.sm}px;
    }}

    QLabel[muted="true"] {{
        color: {t.text_muted};
    }}

    QLabel[section-title="true"] {{
        color: {t.text_secondary};
        font-size: {TYPOGRAPHY.lg}px;
        font-weight: 600;
    }}

    QLabel[role="page-title"] {{
        color: {t.text_primary};
        font-size: {TYPOGRAPHY.xl}px;
        font-weight: 600;
    }}

    QLabel[role="page-subtitle"] {{
        color: {t.text_muted};
        font-size: {TYPOGRAPHY.md}px;
    }}

    QLabel[warning="true"] {{
        color: {t.warning};
    }}

    QLabel[code-preview="true"] {{
        color: {t.accent};
    }}

    QLabel[delta="success"] {{
        color: {t.success};
    }}

    QLabel[delta="warning"] {{
        color: {t.warning};
    }}

    QLabel[delta="flat"] {{
        color: {t.text_muted};
    }}

    QWidget[ui-card="true"] {{
        background: {t.surface_raised};
        border: 1px solid {t.border};
        border-radius: {RADIUS.lg}px;
    }}

    QWidget[toast="true"] {{
        background: {t.surface_raised};
        border: 1px solid {t.border};
        border-radius: {RADIUS.md}px;
        padding: {SPACING.md}px {SPACING.lg}px;
    }}

    QWidget[toast="true"][variant="success"] {{
        background: {t.success_soft};
        border-color: {t.success};
    }}

    QWidget[toast="true"][variant="error"] {{
        background: {t.danger_soft};
        border-color: {t.danger};
    }}

    QWidget[toast="true"][variant="info"] {{
        background: {t.accent_soft};
        border-color: {t.accent};
    }}
    """


def apply_theme(app: QApplication, mode: str = "") -> None:
    global _tokens, _theme_mode

    requested_mode = (mode or "").strip().lower()
    if requested_mode not in {"light", "dark"}:
        requested_mode = str(_settings.value("theme/mode", "light")).strip().lower()
        if requested_mode not in {"light", "dark"}:
            requested_mode = "light"

    _theme_mode = requested_mode
    _settings.setValue("theme/mode", _theme_mode)

    _tokens = DARK if _theme_mode == "dark" else LIGHT
    _registrar_fuentes()

    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(_tokens.surface))
    pal.setColor(QPalette.WindowText, QColor(_tokens.text_primary))
    pal.setColor(QPalette.Base, QColor(_tokens.surface_raised))
    pal.setColor(QPalette.AlternateBase, QColor(_tokens.surface))
    pal.setColor(QPalette.ToolTipBase, QColor(_tokens.surface_raised))
    pal.setColor(QPalette.ToolTipText, QColor(_tokens.text_primary))
    pal.setColor(QPalette.Text, QColor(_tokens.text_primary))
    pal.setColor(QPalette.Button, QColor(_tokens.surface_raised))
    pal.setColor(QPalette.ButtonText, QColor(_tokens.text_primary))
    pal.setColor(QPalette.BrightText, QColor("#FFFFFF"))
    pal.setColor(QPalette.Highlight, QColor(_tokens.accent))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.Link, QColor(_tokens.accent))
    pal.setColor(QPalette.PlaceholderText, QColor(_tokens.text_muted))
    app.setPalette(pal)

    default_font = QFont(TYPOGRAPHY.family_ui)
    default_font.setPixelSize(TYPOGRAPHY.md)
    app.setFont(default_font)
    app.setStyleSheet(_build_qss(_tokens))


def current_theme_mode() -> str:
    return _theme_mode


def toggle_theme(app: QApplication | None = None) -> str:
    target = "dark" if _theme_mode == "light" else "light"
    instance = app or QApplication.instance()
    if instance is not None:
        apply_theme(instance, target)
    else:
        _settings.setValue("theme/mode", target)
    return target
