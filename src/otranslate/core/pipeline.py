"""Orchestration asynchrone : détection de langue → traduction → dictionnaire → historique.
Un seul thread de travail ; les résultats reviennent au thread GUI par signal."""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from .dictionary import is_single_word
from .langdetect import detect
from .translator import ModelNotInstalled


@dataclass
class Result:
    request_id: int
    tag: str                      # "window" | "popup"
    source: str
    target: str = ""
    src_lang: str = "en"
    tgt_lang: str = "fr"
    entries: list = field(default_factory=list)
    error: str = ""
    recorded: bool = False


class _Job(QRunnable):
    def __init__(self, pipe: "Pipeline", args: tuple):
        super().__init__()
        self.pipe, self.args = pipe, args

    def run(self) -> None:
        self.pipe._process(*self.args)


class Pipeline(QObject):
    finished = Signal(object)     # Result

    def __init__(self, cfg, translator, dictionary, history):
        super().__init__()
        self.cfg, self.translator, self.dictionary, self.history = cfg, translator, dictionary, history
        self._ids = itertools.count(1)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)

    def submit(self, text: str, direction: str = "auto", tag: str = "window", record: bool = True) -> int:
        rid = next(self._ids)
        self._pool.start(_Job(self, (rid, text.strip(), direction, tag, record)))
        return rid

    def _process(self, rid: int, text: str, direction: str, tag: str, record: bool) -> None:
        res = Result(rid, tag, text)
        try:
            if direction == "auto":
                src = detect(text) or self.dictionary.guess_lang(text) or self.cfg.fallback_source
            else:
                src = direction.split("-")[0]
            tgt = "fr" if src == "en" else "en"
            res.src_lang, res.tgt_lang = src, tgt
            res.target = self.translator.translate(text, src, tgt)
            if is_single_word(text):
                res.entries = self.dictionary.lookup(text, src)
            if record and self.cfg.history_enabled and res.target:
                self.history.add(src, tgt, text, res.target)
                res.recorded = True
        except ModelNotInstalled as e:
            res.error = str(e)
        except Exception as e:  # noqa: BLE001 — remonté à l'UI
            res.error = f"{type(e).__name__}: {e}"
        self.finished.emit(res)
