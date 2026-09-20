"""Parsing des libellés de date en français tels que fournis par le site
source (ex: "samedi 26 septembre 2026"), qui ne fournit pas de date
machine-readable (pas d'attribut `datetime` sur les <time>)."""

from __future__ import annotations

import re
from datetime import date

_MOIS_FR = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "décembre": 12,
}

# Groupes : (jour de la semaine optionnel, jour, mois, année). Exposée (sans
# underscore) car `render.py` a aussi besoin du jour de la semaine (groupe 1).
DATE_LABEL_RE = re.compile(r"^(\w+)?\s*(\d{1,2})\s+(\w+)\s+(\d{4})")


def parse_date_label(date_label: str) -> date | None:
    match = DATE_LABEL_RE.match(date_label)
    if not match:
        return None
    _, day, month_name, year = match.groups()
    month = _MOIS_FR.get(month_name.lower())
    if month is None:
        return None
    return date(int(year), month, int(day))
