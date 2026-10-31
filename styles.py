"""Thèmes clair/sombre inspirés de Fluent (Windows 11) via QSS + icône générée par code."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from string import Template

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap


@dataclass(frozen=True)
class Palette:
    bg: str
    surface: str
    text: str
    subtext: str
    border: str
    accent: str
    accent_text: str
    hover: str


DARK = Palette("#202020", "#2b2b2b", "#f3f3f3", "#a8a8a8", "#3d3d3d", "#60cdff", "#000000", "#363636")
LIGHT = Palette("#f3f3f3", "#ffffff", "#1b1b1b", "#6b6b6b", "#dcdcdc", "#0067c0", "#ffffff", "#ececec")

_QSS = Template("""
QWidget { background: $bg; color: $text; font-family: "Segoe UI Variable Text", "Segoe UI"; font-size: 14px; }
QLabel { background: transparent; }
QLabel#Caption { color: $subtext; font-size: 12px; }
#PopupRoot { background: transparent; }
QPlainTextEdit, QTextBrowser, QLineEdit, QListWidget, QComboBox, QKeySequenceEdit {
    background: $surface; border: 1px solid $border; border-radius: 8px; padding: 8px;
    selection-background-color: $accent; selection-color: $accent_text; }
QPlainTextEdit { font-size: 16px; }
QPlainTextEdit:focus, QLineEdit:focus { border-bottom: 2px solid $accent; }
QComboBox { padding: 5px 10px; }
QComboBox QAbstractItemView { background: $surface; border: 1px solid $border; selection-background-color: $hover; selection-color: $text; }
QListWidget::item { padding: 6px; border-radius: 6px; }
QListWidget::item:selected, QListWidget::item:hover { background: $hover; color: $text; }
QPushButton { background: $surface; border: 1px solid $border; border-radius: 6px; padding: 6px 14px; }
QPushButton:hover { background: $hover; }
QPushButton:disabled { color: $subtext; }
QPushButton#Primary { background: $accent; color: $accent_text; border: none; font-weight: 600; }
QPushButton#Flat { background: transparent; border: none; color: $subtext; padding: 4px 8px; }
QPushButton#Flat:hover { color: $text; background: $hover; }
QTabWidget::pane { border: 1px solid $border; border-radius: 8px; top: -1px; }
QTabBar::tab { padding: 7px 16px; background: transparent; color: $subtext; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: $text; border-bottom: 2px solid $accent; }
QProgressBar { border: none; border-radius: 4px; background: $border; max-height: 8px; text-align: center; color: transparent; }
QProgressBar::chunk { background: $accent; border-radius: 4px; }
QMenu { background: $surface; border: 1px solid $border; padding: 4px; }
QMenu::item { padding: 6px 22px; border-radius: 4px; }
QMenu::item:selected { background: $hover; }
QFrame#PopupCard { background: $surface; border: 1px solid $border; border-radius: 12px; }
QFrame#PopupCard QTextBrowser { background: transparent; border: none; padding: 0; }
QScrollBar:vertical { width: 10px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: $border; border-radius: 4px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: transparent; }
QToolTip { background: $surface; color: $text; border: 1px solid $border; padding: 4px; }
""")


def build_qss(p: Palette) -> str:
    return _QSS.substitute(asdict(p))


def make_icon() -> QIcon:
    pm = QPixmap(128, 128)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#0067c0"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(8, 8, 112, 112), 26, 26)
    painter.setPen(QColor("white"))
    painter.setFont(QFont("Segoe UI", 54, QFont.Weight.Bold))
    painter.drawText(QRectF(8, 8, 112, 112), Qt.AlignmentFlag.AlignCenter, "A↔F")
    painter.end()
    return QIcon(pm)
