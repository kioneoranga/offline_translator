from __future__ import annotations

from html import escape

from .styles import Palette


def dictionary_html(entries: list[dict], p: Palette) -> str:
    if not entries:
        return f"<p style='color:{p.subtext}'>Aucune entrée de dictionnaire pour ce mot.</p>"
    out: list[str] = []
    for e in entries:
        out.append(
            f"<h3 style='margin:8px 0 2px 0'>{escape(e['word'])} "
            f"<span style='color:{p.subtext};font-weight:normal'>· {escape(e['pos'] or '')} · {e['lang'].upper()}</span></h3>")
        if e["glosses"]:
            out.append("<ol style='margin:2px 0 6px 18px'>"
                       + "".join(f"<li>{escape(g)}</li>" for g in e["glosses"][:6]) + "</ol>")
        if e["translations"]:
            groups: dict[str, list[str]] = {}
            for word, sense in e["translations"]:
                groups.setdefault(sense, []).append(word)
            lines = []
            for sense, words in groups.items():
                label = f"<i style='color:{p.subtext}'>{escape(sense)}</i> : " if sense else ""
                lines.append(label + ", ".join(escape(w) for w in words))
            out.append("<p style='margin:2px 0'><b>Traductions</b><br>" + "<br>".join(lines) + "</p>")
        if e["synonyms"]:
            out.append("<p style='margin:2px 0'><b>Synonymes</b> : "
                       + ", ".join(escape(s) for s in e["synonyms"][:12]) + "</p>")
        for ex in e["examples"][:2]:
            out.append(f"<p style='color:{p.subtext};margin:2px 0'><i>« {escape(ex)} »</i></p>")
    return "".join(out)
