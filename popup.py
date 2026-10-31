"""Infobulle flottante près du curseur : se ferme au clic extérieur (Qt.Popup) ou avec Échap."""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton,
                               QTextBrowser, QVBoxLayout, QWidget)

from .render import dictionary_html
from .styles import DARK

TEXT_W = 432


class TranslationPopup(QWidget):
    open_in_window = Signal(str)   # texte source

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("PopupRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.pal = DARK
        self._anchor = QPoint()
        self._source = self._target = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)           # marge pour l'ombre portée
        card = QFrame()
        card.setObjectName("PopupCard")
        card.setFixedWidth(TEXT_W + 28)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 110))
        card.setGraphicsEffect(shadow)
        root.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(8)
        self.caption = QLabel()
        self.caption.setObjectName("Caption")
        self.body = self._browser()
        self.dict_view = self._browser()
        row = QHBoxLayout()
        self.btn_copy = QPushButton("Copier")
        self.btn_open = QPushButton("Ouvrir dans l'application")
        for b in (self.btn_copy, self.btn_open):
            b.setObjectName("Flat")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        row.addWidget(self.btn_copy)
        row.addWidget(self.btn_open)
        row.addStretch()
        for w in (self.caption, self.body, self.dict_view):
            lay.addWidget(w)
        lay.addLayout(row)
        self.btn_copy.clicked.connect(self._copy)
        self.btn_open.clicked.connect(lambda: (self.open_in_window.emit(self._source), self.close()))

    @staticmethod
    def _browser() -> QTextBrowser:
        b = QTextBrowser()
        b.setFrameShape(QFrame.Shape.NoFrame)
        b.setOpenLinks(False)
        b.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return b

    # ------------------------------------------------------------ API
    def show_loading(self, pos: QPoint) -> None:
        self._anchor = pos
        self._source = self._target = ""
        self.caption.setText("Traduction en cours…")
        self._set(self.body, "…", 40)
        self.dict_view.hide()
        self.btn_copy.setEnabled(False)
        self.btn_open.setEnabled(False)
        self._present()

    def show_message(self, text: str, pos: QPoint | None = None) -> None:
        if pos is not None:
            self._anchor = pos
        self.caption.setText("")
        self._set(self.body, text, 120)
        self.dict_view.hide()
        self.btn_copy.setEnabled(False)
        self.btn_open.setEnabled(False)
        self._present()

    def show_result(self, source: str, target: str, src: str, tgt: str, entries: list[dict]) -> None:
        self._source, self._target = source, target
        self.caption.setText(f"{src.upper()} → {tgt.upper()}")
        self._set(self.body, target, 260)
        if entries:
            self.dict_view.setHtml(dictionary_html(entries, self.pal))
            self._fit(self.dict_view, 180)
            self.dict_view.show()
        else:
            self.dict_view.hide()
        self.btn_copy.setEnabled(True)
        self.btn_open.setEnabled(True)
        self._present()

    # ------------------------------------------------------------ internals
    def _set(self, view: QTextBrowser, text: str, max_h: int) -> None:
        view.setPlainText(text)
        self._fit(view, max_h)

    @staticmethod
    def _fit(view: QTextBrowser, max_h: int) -> None:
        view.document().setTextWidth(TEXT_W)
        view.setFixedHeight(min(int(view.document().size().height()) + 8, max_h))

    def _present(self) -> None:
        self.adjustSize()
        screen = QGuiApplication.screenAt(self._anchor) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        w, h = self.width(), self.height()
        x, y = self._anchor.x() + 4, self._anchor.y() + 14
        if x + w > geo.right():
            x = geo.right() - w
        if y + h > geo.bottom():
            y = self._anchor.y() - h - 4
        self.move(max(geo.left(), x), max(geo.top(), y))
        if not self.isVisible():
            self.show()

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self._target)
        self.close()

    def keyPressEvent(self, e) -> None:  # noqa: N802
        if e.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)
