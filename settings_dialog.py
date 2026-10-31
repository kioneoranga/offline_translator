from __future__ import annotations

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QKeySequenceEdit,
                               QPushButton, QVBoxLayout)

from ..config import Config


def _to_seq(spec: str) -> QKeySequence:
    return QKeySequence(spec.replace("win", "meta"))


class SettingsDialog(QDialog):
    def __init__(self, cfg: Config, on_models, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Paramètres")
        self.setMinimumWidth(420)
        form = QFormLayout()
        self.theme = QComboBox()
        for label, val in (("Système", "system"), ("Sombre", "dark"), ("Clair", "light")):
            self.theme.addItem(label, val)
        self.theme.setCurrentIndex(max(0, self.theme.findData(cfg.theme)))
        self.hk_translate = QKeySequenceEdit(_to_seq(cfg.hotkey_translate))
        self.hk_open = QKeySequenceEdit(_to_seq(cfg.hotkey_open))
        for e in (self.hk_translate, self.hk_open):
            e.setMaximumSequenceLength(1)
        self.live = QCheckBox("Traduire pendant la saisie")
        self.live.setChecked(cfg.live_translate)
        self.hist = QCheckBox("Enregistrer l'historique")
        self.hist.setChecked(cfg.history_enabled)
        self.unwrap = QCheckBox("Recoller les retours à la ligne (texte copié depuis un PDF)")
        self.unwrap.setChecked(cfg.unwrap_lines)
        form.addRow("Thème", self.theme)
        form.addRow("Raccourci : traduire la sélection", self.hk_translate)
        form.addRow("Raccourci : ouvrir la fenêtre", self.hk_open)
        form.addRow(self.live)
        form.addRow(self.hist)
        form.addRow(self.unwrap)
        models = QPushButton("Gérer / télécharger les modèles…")
        models.clicked.connect(on_models)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(models)
        lay.addWidget(buttons)

    def _accept(self) -> None:
        c = self.cfg
        c.theme = self.theme.currentData()
        for attr, edit in (("hotkey_translate", self.hk_translate), ("hotkey_open", self.hk_open)):
            text = edit.keySequence().toString().lower().replace("meta", "win")
            if text:
                setattr(c, attr, text)
        c.live_translate, c.history_enabled = self.live.isChecked(), self.hist.isChecked()
        c.unwrap_lines = self.unwrap.isChecked()
        self.accept()
