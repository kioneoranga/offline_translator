"""Construit data/dictionary.db (SQLite) à partir d'extraits Wiktionnaire au format JSONL de kaikki.org.

Télécharger (une fois, avec connexion) depuis https://kaikki.org/dictionary/ :
  - English  -> kaikki.org-dictionary-English.jsonl   (mots anglais : définitions, synonymes, traductions vers le français)
  - French   -> kaikki.org-dictionary-French.jsonl    (mots français : définitions en anglais)

Usage :  python tools/build_dictionary.py English.jsonl French.jsonl -o data/dictionary.db
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

SCHEMA = """
DROP TABLE IF EXISTS entry;
CREATE TABLE entry(
    id INTEGER PRIMARY KEY, lang TEXT NOT NULL, word TEXT NOT NULL, word_lc TEXT NOT NULL, pos TEXT,
    glosses TEXT, synonyms TEXT, translations TEXT, examples TEXT);
"""


def _uniq(seq):
    seen, out = set(), []
    for x in seq:
        key = tuple(x) if isinstance(x, list) else x
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out


def convert(entry: dict):
    lang = entry.get("lang_code")
    if lang not in ("en", "fr") or not entry.get("word"):
        return None
    other = "fr" if lang == "en" else "en"
    glosses, examples, synonyms = [], [], []
    for sense in entry.get("senses", []):
        if sense.get("glosses"):
            glosses.append(sense["glosses"][-1])
        for ex in sense.get("examples", [])[:1]:
            if ex.get("text"):
                examples.append(ex["text"])
        synonyms += [s["word"] for s in sense.get("synonyms", []) if s.get("word")]
    synonyms += [s["word"] for s in entry.get("synonyms", []) if s.get("word")]
    translations = [[t["word"], t.get("sense", "")] for t in entry.get("translations", [])
                    if t.get("code") == other and t.get("word")]
    if not glosses and not translations:
        return None
    return (lang, entry["word"], entry["word"].lower(), entry.get("pos", ""),
            json.dumps(_uniq(glosses)[:8], ensure_ascii=False),
            json.dumps(_uniq(synonyms)[:15], ensure_ascii=False),
            json.dumps(_uniq(translations)[:40], ensure_ascii=False),
            json.dumps(_uniq(examples)[:3], ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("data/dictionary.db"))
    args = ap.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(args.output)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    con.executescript(SCHEMA)
    batch, total = [], 0
    for path in args.inputs:
        with open(path, encoding="utf-8") as f:
            for line in f:
                row = convert(json.loads(line))
                if row:
                    batch.append(row)
                if len(batch) >= 20000:
                    con.executemany("INSERT INTO entry(lang,word,word_lc,pos,glosses,synonyms,translations,examples)"
                                    " VALUES(?,?,?,?,?,?,?,?)", batch)
                    con.commit()
                    total += len(batch)
                    batch.clear()
                    print(f"{total} entrées…", end="\r")
    if batch:
        con.executemany("INSERT INTO entry(lang,word,word_lc,pos,glosses,synonyms,translations,examples)"
                        " VALUES(?,?,?,?,?,?,?,?)", batch)
        total += len(batch)
    con.execute("CREATE INDEX idx_entry_word ON entry(lang, word_lc)")
    con.commit()
    con.execute("VACUUM")
    con.close()
    print(f"\nTerminé : {total} entrées -> {args.output}")


if __name__ == "__main__":
    main()
