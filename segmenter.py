"""Découpage en phrases : les modèles Marian/OPUS sont entraînés au niveau phrase,
ils se dégradent sur de longs paragraphes. On traduit phrase par phrase (par lots)
et on reconstruit le texte en conservant les sauts de ligne."""
from __future__ import annotations

import re

_ABBREV = {
    "mr", "mrs", "ms", "dr", "prof", "st", "vs", "etc", "fig", "no", "cf", "inc", "ltd", "jr", "sr",
    "mme", "mlle", "mm", "pp", "p", "env", "approx", "ex", "e.g", "i.e", "al",
}
_BOUNDARY = re.compile(
    r'(?:(?<=[.!?…])|(?<=[.!?…]["”’»)\]]))\s+(?=["“«(\[]?[A-ZÀ-ÖØ-Þ0-9])'
)
_MAX_WORDS = 60


def normalize(text: str, unwrap: bool = True) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00ad", "")
    if unwrap:
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)                      # césure de fin de ligne
        text = re.sub(r"(?<![.!?:;…\n])\n(?!\n|\s*[-•*\d])", " ", text)   # retour « dur » au milieu d'une phrase
    return text


def _needs_merge(prev: str) -> bool:
    tokens = prev.split()
    if not tokens:
        return False
    last = tokens[-1]
    if last.endswith(".") and last[:-1].lower() in _ABBREV:
        return True
    if len(tokens) == 1 and re.fullmatch(r"\d+[.)]", last):               # « 1. »
        return True
    return bool(re.fullmatch(r"[A-Z]\.", last))                           # initiale « J. »


def _merge(pieces: list[str]) -> list[str]:
    out: list[str] = []
    for p in pieces:
        if out and _needs_merge(out[-1]):
            out[-1] += " " + p
        else:
            out.append(p)
    return out


def _chunk_long(sentence: str) -> list[str]:
    words = sentence.split()
    if len(words) <= _MAX_WORDS * 2:
        return [sentence]
    chunks, cur = [], []
    for part in re.split(r"(?<=[,;:])\s+", sentence):
        cur.append(part)
        if sum(len(c.split()) for c in cur) >= _MAX_WORDS:
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    final = []
    for c in chunks:  # dernier recours : découpe brute
        w = c.split()
        final += [" ".join(w[i:i + 120]) for i in range(0, len(w), 120)] if len(w) > 150 else [c]
    return final


def split(text: str) -> list[tuple[bool, str]]:
    """[(est_du_texte, valeur)] — les éléments non-texte sont les séparateurs à restituer tels quels."""
    out: list[tuple[bool, str]] = []
    for piece in re.split(r"(\n+)", text):
        if not piece:
            continue
        core = piece.strip()
        if piece.startswith("\n") or not core:
            out.append((False, piece))
            continue
        lead = piece[: len(piece) - len(piece.lstrip())]
        trail = piece[len(piece.rstrip()):]
        if lead:
            out.append((False, lead))
        first = True
        for sent in _merge(_BOUNDARY.split(core)):
            for chunk in _chunk_long(sent):
                if not first:
                    out.append((False, " "))
                out.append((True, chunk))
                first = False
        if trail:
            out.append((False, trail))
    return out
