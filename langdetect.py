"""Détection EN/FR 100 % locale, sans dépendance (mots-outils + accents)."""
from __future__ import annotations

import re

_EN = set(
    "the be to of and in that have it for not with he you do at this but his by from they we say her she "
    "an will my one all would there their what so up out if about who get which go when make can like time "
    "just him know take people into year your good some could them see other than then now look only come "
    "its over think also back after use two how our work first well way even new want because any these "
    "give day most us is are was were been has had did does am don isn ll ve re doesn didn won wasn".split()
)
_FR = set(
    "le la les un une des du de et en est que qui dans pour pas sur au aux avec ne se ce il elle nous vous "
    "ils elles je tu mais où par son sa ses leur leurs cette ces être avoir fait faire comme tout tous "
    "aussi très sans sous entre bien donc alors ainsi ont sont suis es sommes êtes été était mon mes ton "
    "ta tes notre votre nos vos lui moi toi si quand dont même autre autres l qu j ça cela ceci".split()
)
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_ACCENTS = set("éèêëàâùûüçôîïœ")


def detect(text: str) -> str | None:
    """Retourne 'en', 'fr' ou None si indécidable."""
    words = [w.lower() for w in _WORD.findall(text)]
    if not words:
        return None
    en = sum(w in _EN for w in words)
    fr = sum(w in _FR for w in words)
    fr += 0.5 * sum(c in _ACCENTS for c in text.lower())
    if en == fr:
        return None
    return "en" if en > fr else "fr"
