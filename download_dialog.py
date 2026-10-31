"""Premier lancement : téléchargement des poids des modèles avec barre de progression."""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QPushButton, QHBoxLayout, QVBoxLayout

from ..core.models import DownloadCancelled, ModelSpec, download_all


class _Worker(QThread):
    progress = Signal(int, str)        # permille, texte
    done = Signal(bool, str)

    def __init__(self, specs: list[ModelSpec]):
        super().__init__()
        self.specs = specs
        self.cancel = threading.Event()

    def run(self) -> None:
        def cb(done: int, total: int, name: str) -> None:
            pm = int(done * 1000 / total) if total else 0
            self.progress.emit(pm, f"{name} — {done / 1e6:.0f} / {total / 1e6:.0f} Mo")
        try:
            download_all(self.specs, cb, self.cancel)
            self.done.emit(True, "")
        except DownloadCancelled:
            self.done.emit(False, "Téléchargement annulé.")
        except Exception as e:  # noqa: BLE001
            self.done.emit(False, f"Échec : {e}")


class DownloadDialog(QDialog):
    def __init__(self, specs: list[ModelSpec], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Téléchargement des modèles de traduction")
        self.setMinimumWidth(480)
        self.specs = specs
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Téléchargement unique des modèles linguistiques (anglais ⇄ français).\n"
                             "Ensuite, l'application fonctionne entièrement hors ligne."))
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.status = QLabel("Préparation…")
        self.status.setObjectName("Caption")
        lay.addWidget(self.bar)
        lay.addWidget(self.status)
        row = QHBoxLayout()
        row.addStretch()
        self.btn = QPushButton("Annuler")
        row.addWidget(self.btn)
        lay.addLayout(row)
        self.btn.clicked.connect(self._on_button)
        self._worker: _Worker | None = None
        self._failed = False
        self._start()

    def _start(self) -> None:
        self._failed = False
        self.btn.setText("Annuler")
        self.status.setText("Connexion à Hugging Face…")
        self._worker = _Worker(self.specs)
        self._worker.progress.connect(lambda pm, t: (self.bar.setValue(pm), self.status.setText(t)))
        self._worker.done.connect(self._finished)
        self._worker.start()

    def _finished(self, ok: bool, msg: str) -> None:
        if ok:
            self.accept()
        else:
            self._failed = True
            self.status.setText(msg + "  (vérifiez la connexion, ou copiez les modèles dans le dossier models/)")
            self.btn.setText("Réessayer")

    def _on_button(self) -> None:
        if self._failed:
            self._start()
        else:
            self._stop()
            self.reject()

    def _stop(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel.set()
            self._worker.wait(3000)

    def closeEvent(self, e) -> None:  # noqa: N802
        self._stop()
        super().closeEvent(e)
