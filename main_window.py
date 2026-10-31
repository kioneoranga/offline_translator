"""Fenêtre principale : double volet source/traduction, dictionnaire, historique."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTabWidget,
                               QTextBrowser, QVBoxLayout, QWidget)

from ..system.theme import set_titlebar_dark
from .render import dictionary_html
from .styles import DARK

LANG_NAMES = {"en": "Anglais", "fr": "Français"}


class HistoryPanel(QWidget):
    load_requested = Signal(dict)

    def __init__(self, history):
        super().__init__()
        self.history = history
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher dans l'historique…")
        self.list = QListWidget()
        self.btn_delete = QPushButton("Supprimer")
        self.btn_clear = QPushButton("Tout effacer")
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.btn_delete)
        row.addWidget(self.btn_clear)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        for w in (self.search, self.list):
            lay.addWidget(w)
        lay.addLayout(row)
        self.search.textChanged.connect(self.refresh)
        self.list.itemDoubleClicked.connect(lambda it: self.load_requested.emit(it.data(Qt.ItemDataRole.UserRole)))
        self.btn_delete.clicked.connect(self._delete)
        self.btn_clear.clicked.connect(self._clear)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for row in self.history.search(self.search.text()):
            one = lambda s, n: (s.replace("\n", " ")[:n] + ("…" if len(s) > n else ""))  # noqa: E731
            item = QListWidgetItem(f"{row['src_lang'].upper()}→{row['tgt_lang'].upper()}   "
                                   f"{one(row['source'], 60)}  ›  {one(row['target'], 60)}")
            item.setData(Qt.ItemDataRole.UserRole, row)
            item.setToolTip(f"{row['source']}\n\n{row['target']}")
            self.list.addItem(item)

    def _delete(self) -> None:
        item = self.list.currentItem()
        if item:
            self.history.delete(item.data(Qt.ItemDataRole.UserRole)["id"])
            self.refresh()

    def _clear(self) -> None:
        if QMessageBox.question(self, "Historique", "Effacer tout l'historique ?") == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self.refresh()


class MainWindow(QMainWindow):
    settings_requested = Signal()
    models_requested = Signal()

    def __init__(self, cfg, pipeline, history):
        super().__init__()
        self.cfg, self.pipeline, self.history = cfg, pipeline, history
        self.pal = DARK
        self._req_id = 0
        self._pending_hist = None
        self.setWindowTitle("Traducteur hors ligne")
        self.resize(1100, 720)

        # --- barre d'outils
        self.direction = QComboBox()
        for label, val in (("Détection automatique", "auto"), ("Anglais → Français", "en-fr"),
                           ("Français → Anglais", "fr-en")):
            self.direction.addItem(label, val)
        self.btn_swap = QPushButton("⇄")
        self.btn_swap.setToolTip("Inverser les langues")
        self.btn_swap.setFixedWidth(44)
        self.btn_translate = QPushButton("Traduire  (Ctrl+Entrée)")
        self.btn_translate.setObjectName("Primary")
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("Flat")
        self.btn_settings.setFixedWidth(40)
        top = QHBoxLayout()
        for w in (self.direction, self.btn_swap):
            top.addWidget(w)
        top.addStretch()
        top.addWidget(self.btn_translate)
        top.addWidget(self.btn_settings)

        # --- double volet
        self.source = QPlainTextEdit()
        self.source.setPlaceholderText("Saisissez ou collez le texte à traduire…")
        self.target = QPlainTextEdit()
        self.target.setReadOnly(True)
        self.target.setPlaceholderText("La traduction apparaît ici.")
        self.status = QLabel("Prêt")
        self.status.setObjectName("Caption")
        self.btn_copy = QPushButton("Copier la traduction")
        self.btn_copy.setObjectName("Flat")
        self.btn_clear = QPushButton("Effacer")
        self.btn_clear.setObjectName("Flat")
        left, right = QWidget(), QWidget()
        ll, rl = QVBoxLayout(left), QVBoxLayout(right)
        for lay in (ll, rl):
            lay.setContentsMargins(0, 0, 0, 0)
        cap_l = QLabel("Texte source")
        cap_l.setObjectName("Caption")
        ll.addWidget(cap_l)
        ll.addWidget(self.source)
        crow = QHBoxLayout()
        crow.addWidget(self.status)
        crow.addStretch()
        crow.addWidget(self.btn_copy)
        crow.addWidget(self.btn_clear)
        rl.addLayout(crow)
        rl.addWidget(self.target)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(left)
        split.addWidget(right)
        split.setChildrenCollapsible(False)

        # --- onglets
        self.dict_view = QTextBrowser()
        self.history_panel = HistoryPanel(history)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.dict_view, "Dictionnaire")
        self.tabs.addTab(self.history_panel, "Historique")

        central = QWidget()
        v = QVBoxLayout(central)
        v.setContentsMargins(16, 12, 16, 16)
        v.setSpacing(10)
        v.addLayout(top)
        v.addWidget(split, 3)
        v.addWidget(self.tabs, 2)
        self.setCentralWidget(central)

        # --- comportements
        self._timer = QTimer(self, singleShot=True, interval=450)
        self._hist_timer = QTimer(self, singleShot=True, interval=2500)
        self._timer.timeout.connect(lambda: self.translate_now(record=False))
        self._hist_timer.timeout.connect(self._commit_live_history)
        self.source.textChanged.connect(self._on_text_changed)
        self.btn_translate.clicked.connect(lambda: self.translate_now(record=True))
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=lambda: self.translate_now(record=True))
        self.btn_swap.clicked.connect(self._swap)
        self.btn_copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.target.toPlainText()))
        self.btn_clear.clicked.connect(self._clear)
        self.btn_settings.clicked.connect(self.settings_requested)
        self.direction.currentIndexChanged.connect(lambda _: self.translate_now(record=False))
        self.history_panel.load_requested.connect(self._load_history_row)

    # ------------------------------------------------------------ API publique
    def set_palette(self, pal, dark: bool) -> None:
        self.pal = pal
        set_titlebar_dark(int(self.winId()), dark)

    def show_and_focus(self, text: str | None = None) -> None:
        if text:
            self.source.setPlainText(text)
            self.translate_now(record=True)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.source.setFocus()

    def handle_result(self, res) -> None:
        if res.request_id != self._req_id:
            return                                             # résultat périmé
        if res.error:
            if res.error.startswith("model_missing"):
                self.status.setText("Modèle absent — téléchargement requis")
                self.models_requested.emit()
            else:
                self.status.setText("Erreur : " + res.error)
            return
        self.target.setPlainText(res.target)
        self.status.setText(f"{LANG_NAMES[res.src_lang]} → {LANG_NAMES[res.tgt_lang]}")
        self.dict_view.setHtml(dictionary_html(res.entries, self.pal) if res.entries else
                               f"<p style='color:{self.pal.subtext}'>Le dictionnaire s'affiche pour un mot isolé.</p>")
        if res.entries:
            self.tabs.setCurrentIndex(0)
        if res.recorded:
            self.history_panel.refresh()
        else:
            self._pending_hist = res
            self._hist_timer.start()

    # ------------------------------------------------------------ interne
    def translate_now(self, record: bool = True) -> None:
        self._timer.stop()
        text = self.source.toPlainText().strip()
        if not text:
            self.target.clear()
            self.status.setText("Prêt")
            return
        self.status.setText("Traduction…")
        self._req_id = self.pipeline.submit(text, self.direction.currentData(), tag="window", record=record)

    def _on_text_changed(self) -> None:
        if not self.source.toPlainText().strip():
            self.target.clear()
            self._timer.stop()
        elif self.cfg.live_translate:
            self._timer.start()

    def _commit_live_history(self) -> None:
        r = self._pending_hist
        if r and self.cfg.history_enabled and r.source == self.source.toPlainText().strip():
            self.history.add(r.src_lang, r.tgt_lang, r.source, r.target)
            self.history_panel.refresh()

    def _swap(self) -> None:
        translated = self.target.toPlainText()
        cur = self.direction.currentData()
        if cur != "auto":
            a, b = cur.split("-")
            self.direction.blockSignals(True)
            self.direction.setCurrentIndex(self.direction.findData(f"{b}-{a}"))
            self.direction.blockSignals(False)
        if translated:
            self.source.setPlainText(translated)
            self.translate_now(record=False)

    def _clear(self) -> None:
        self.source.clear()
        self.target.clear()
        self.dict_view.clear()
        self.source.setFocus()

    def _load_history_row(self, row: dict) -> None:
        self.direction.blockSignals(True)
        self.direction.setCurrentIndex(self.direction.findData(f"{row['src_lang']}-{row['tgt_lang']}"))
        self.direction.blockSignals(False)
        self.source.setPlainText(row["source"])
        self.target.setPlainText(row["target"])

    def closeEvent(self, e) -> None:  # noqa: N802 — réduit dans la zone de notification
        e.ignore()
        self.hide()
