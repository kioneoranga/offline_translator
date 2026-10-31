"""Amorçage : icône de notification, raccourcis globaux, fenêtre, popup, premier lancement."""
from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QLockFile, QObject, QPoint, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from .config import Config
from .core.dictionary import Dictionary
from .core.history import History
from .core.models import missing_models
from .core.pipeline import Pipeline
from .core.translator import TranslationService
from .paths import DATA_DIR, ensure_dirs
from .system import theme as win_theme
from .ui.download_dialog import DownloadDialog
from .ui.main_window import MainWindow
from .ui.popup import TranslationPopup
from .ui.settings_dialog import SettingsDialog
from .ui.styles import DARK, LIGHT, build_qss, make_icon


class _Bridge(QObject):
    """Les callbacks du thread de raccourcis émettent ces signaux ; Qt les remet dans le thread GUI."""
    translate = Signal()
    open_main = Signal()


class _CaptureSignals(QObject):
    done = Signal(object, object)       # texte | None, QPoint


class _CaptureTask(QRunnable):
    def __init__(self, pos: QPoint, sig: _CaptureSignals):
        super().__init__()
        self.pos, self.sig = pos, sig

    def run(self) -> None:
        try:
            from .system.clipboard import capture_selection
            text = capture_selection()
        except Exception:  # noqa: BLE001
            text = None
        self.sig.done.emit(text, self.pos)


class Controller(QObject):
    def __init__(self, qapp: QApplication):
        super().__init__()
        self.qapp = qapp
        self.cfg = Config.load()
        self.history = History()
        self.dictionary = Dictionary()
        self.translator = TranslationService(self.cfg)
        self.pipeline = Pipeline(self.cfg, self.translator, self.dictionary, self.history)
        self.popup = TranslationPopup()
        self.window = MainWindow(self.cfg, self.pipeline, self.history)
        self.icon = make_icon()
        self.window.setWindowIcon(self.icon)

        self.pipeline.finished.connect(self._route_result)
        self.window.settings_requested.connect(self.open_settings)
        self.window.models_requested.connect(lambda: self.ensure_models(force=True))
        self.popup.open_in_window.connect(self.window.show_and_focus)

        self._cap_sig = _CaptureSignals()
        self._cap_sig.done.connect(self._on_captured)
        self._popup_req = 0

        self._build_tray()
        self.apply_theme()
        self._start_hotkeys()
        QTimer.singleShot(200, self._first_run)

    # ------------------------------------------------------------ thème
    def apply_theme(self) -> None:
        dark = win_theme.system_is_dark() if self.cfg.theme == "system" else self.cfg.theme == "dark"
        pal = DARK if dark else LIGHT
        self.qapp.setStyleSheet(build_qss(pal))
        self.popup.pal = pal
        self.window.set_palette(pal, dark)

    # ------------------------------------------------------------ zone de notification
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.icon, self)
        menu = QMenu()
        for label, slot in (("Ouvrir le traducteur", lambda: self.window.show_and_focus()),
                            ("Traduire la sélection", self.on_translate_hotkey),
                            ("Paramètres…", self.open_settings), (None, None), ("Quitter", self.quit)):
            if label is None:
                menu.addSeparator()
            else:
                act = QAction(label, menu)
                act.triggered.connect(slot)
                menu.addAction(act)
        self._tray_menu = menu
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("Traducteur hors ligne")
        self.tray.activated.connect(
            lambda reason: self.window.show_and_focus() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    # ------------------------------------------------------------ raccourcis globaux
    def _start_hotkeys(self) -> None:
        from .system.hotkeys import HotkeyManager
        if not hasattr(self, "hotkeys"):
            self.hotkeys = HotkeyManager()
            self.bridge = _Bridge()
            self.bridge.translate.connect(self.on_translate_hotkey)
            self.bridge.open_main.connect(lambda: self.window.show_and_focus())
        failed = self.hotkeys.start([(self.cfg.hotkey_translate, self.bridge.translate.emit),
                                     (self.cfg.hotkey_open, self.bridge.open_main.emit)])
        if failed:
            self.tray.showMessage("Raccourci indisponible",
                                  "Déjà utilisé par une autre application : " + ", ".join(failed)
                                  + "\nChoisissez-en un autre dans les paramètres.",
                                  QSystemTrayIcon.MessageIcon.Warning, 8000)

    def on_translate_hotkey(self) -> None:
        pos = QCursor.pos()
        # Capture AVANT d'afficher quoi que ce soit : la fenêtre cible doit garder le focus.
        QThreadPool.globalInstance().start(_CaptureTask(pos, self._cap_sig))

    def _on_captured(self, text, pos) -> None:
        if not text or not text.strip():
            self.popup.show_message("Aucun texte sélectionné.", pos)
            return
        self.popup.show_loading(pos)
        self._popup_req = self.pipeline.submit(text, "auto", tag="popup", record=True)

    def _route_result(self, res) -> None:
        if res.tag == "window":
            self.window.handle_result(res)
        elif res.request_id == self._popup_req:
            if res.error.startswith("model_missing"):
                self.popup.show_message("Modèle de traduction absent.\nOuvrez l'application pour le télécharger.")
            elif res.error:
                self.popup.show_message("Erreur : " + res.error)
            else:
                self.popup.show_result(res.source, res.target, res.src_lang, res.tgt_lang, res.entries)
            if res.recorded:
                self.window.history_panel.refresh()

    # ------------------------------------------------------------ modèles / paramètres
    def _first_run(self) -> None:
        if missing_models():
            self.window.show_and_focus()
            self.ensure_models()
        elif not self.cfg.first_run_done:
            self.tray.showMessage("Traducteur hors ligne",
                                  f"Sélectionnez du texte puis {self.cfg.hotkey_translate.upper()}.",
                                  QSystemTrayIcon.MessageIcon.Information, 5000)
        self.cfg.first_run_done = True
        self.cfg.save()

    def ensure_models(self, force: bool = False) -> None:
        specs = missing_models()
        if not specs and not force:
            return
        if not specs:
            QMessageBox.information(self.window, "Modèles", "Tous les modèles sont déjà installés.")
            return
        if DownloadDialog(specs, self.window).exec():
            self.translator.reset()

    def open_settings(self) -> None:
        dlg = SettingsDialog(self.cfg, lambda: self.ensure_models(force=True), self.window)
        if dlg.exec():
            self.cfg.save()
            self.apply_theme()
            self._start_hotkeys()

    def quit(self) -> None:
        self.hotkeys.stop()
        self.tray.hide()
        self.qapp.quit()


def main() -> None:
    ensure_dirs()
    try:  # icône correcte dans la barre des tâches
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OfflineTranslator.App")
    except Exception:  # noqa: BLE001
        pass
    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)
    qapp.setApplicationName("Traducteur hors ligne")
    lock = QLockFile(str(DATA_DIR / "app.lock"))
    if not lock.tryLock(100):                      # instance unique
        QMessageBox.information(None, "Traducteur hors ligne", "L'application est déjà en cours d'exécution.")
        sys.exit(0)
    controller = Controller(qapp)  # noqa: F841 — garde les références vivantes
    sys.exit(qapp.exec())
