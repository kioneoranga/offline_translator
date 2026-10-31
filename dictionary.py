"""Dictionnaire bilingue local (SQLite, lecture seule) construit depuis Wiktionnaire via tools/build_dictionary.py."""
from __future__ import annotations

import json
import re
import sqlite3
import threading
import unicodedata
from pathlib import Path

from ..paths import DATA_DIR

_STRIP = " \t\r\n.,;:!?\"'«»“”()[]…"


def normalize_word(text: str) -> str:
    return unicodedata.normalize("NFC", text.strip(_STRIP)).lower()


def is_single_word(text: str) -> bool:
    return bool(re.fullmatch(r"[\w'’\-]+", text.strip(_STRIP), re.UNICODE))


class Dictionary:
    def __init__(self, path: Path | None = None):
        path = Path(path) if path else DATA_DIR / "dictionary.db"
        self._lock = threading.Lock()
        self._con: sqlite3.Connection | None = None
        if path.exists():
            self._con = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, check_same_thread=False)

    @property
    def available(self) -> bool:
        return self._con is not None

    def lookup(self, word: str, lang: str | None = None, limit: int = 12) -> list[dict]:
        if not self._con:
            return []
        w = normalize_word(word)
        sql = "SELECT lang, word, pos, glosses, synonyms, translations, examples FROM entry WHERE word_lc=?"
        args: list = [w]
        if lang:
            sql += " AND lang=?"
            args.append(lang)
        with self._lock:
            rows = self._con.execute(sql + " LIMIT ?", args + [limit]).fetchall()
        return [
            {"lang": r[0], "word": r[1], "pos": r[2], "glosses": json.loads(r[3]),
             "synonyms": json.loads(r[4]), "translations": json.loads(r[5]), "examples": json.loads(r[6])}
            for r in rows
        ]

    def guess_lang(self, word: str) -> str | None:
        """Pour un mot isolé : 'en' ou 'fr' si une seule langue le connaît, sinon None."""
        if not self._con or not is_single_word(word):
            return None
        with self._lock:
            langs = {r[0] for r in self._con.execute(
                "SELECT DISTINCT lang FROM entry WHERE word_lc=?", (normalize_word(word),))}
        return langs.pop() if len(langs) == 1 else None
