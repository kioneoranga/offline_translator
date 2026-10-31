from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from ..paths import DATA_DIR

MAX_ROWS = 5000


class History:
    def __init__(self, path: Path | None = None):
        path = Path(path) if path else DATA_DIR / "history.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._con = sqlite3.connect(path, check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, ts REAL, src_lang TEXT, "
            "tgt_lang TEXT, source TEXT, target TEXT)"
        )
        self._con.commit()

    def add(self, src_lang: str, tgt_lang: str, source: str, target: str) -> None:
        with self._lock:
            last = self._con.execute("SELECT id, source, tgt_lang FROM history ORDER BY id DESC LIMIT 1").fetchone()
            if last and last["source"] == source and last["tgt_lang"] == tgt_lang:
                self._con.execute("UPDATE history SET ts=?, target=? WHERE id=?", (time.time(), target, last["id"]))
            else:
                self._con.execute(
                    "INSERT INTO history(ts, src_lang, tgt_lang, source, target) VALUES(?,?,?,?,?)",
                    (time.time(), src_lang, tgt_lang, source, target))
                self._con.execute(
                    "DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT ?)", (MAX_ROWS,))
            self._con.commit()

    def search(self, query: str = "", limit: int = 200) -> list[dict]:
        like = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        with self._lock:
            rows = self._con.execute(
                "SELECT * FROM history WHERE source LIKE ? ESCAPE '\\' OR target LIKE ? ESCAPE '\\' "
                "ORDER BY ts DESC LIMIT ?", (like, like, limit)).fetchall()
        return [dict(r) for r in rows]

    def delete(self, row_id: int) -> None:
        with self._lock:
            self._con.execute("DELETE FROM history WHERE id=?", (row_id,))
            self._con.commit()

    def clear(self) -> None:
        with self._lock:
            self._con.execute("DELETE FROM history")
            self._con.commit()
