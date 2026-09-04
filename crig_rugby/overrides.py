"""Corrections manuelles de date/heure pour un match à venir.

Sert de filet de sécurité quand coeurdurugby.com n'a pas (encore) répercuté
un changement de programmation (ex: match avancé au samedi soir) : on
recherche le match par équipes (noms tels que scrapés, avant club_aliases)
dans chaque catégorie, et on remplace sa date/heure juste avant la mise en
cache. Rechargé à chaque cycle de scraping, sans redémarrage nécessaire.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .models import Match


@dataclass
class MatchOverride:
    slug: str
    home_team: str
    away_team: str
    date_label: str
    heure: str | None = None


def load_overrides(path: Path) -> list[MatchOverride]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [
        MatchOverride(
            slug=item["slug"],
            home_team=item["home_team"],
            away_team=item["away_team"],
            date_label=item["date_label"],
            heure=item.get("heure"),
        )
        for item in raw.get("overrides") or []
    ]


def apply_overrides(matches: list[Match], slug: str, overrides: list[MatchOverride]) -> None:
    """Modifie en place la date/heure des Match qui correspondent à une
    correction déclarée pour cette catégorie."""
    for match in matches:
        for override in overrides:
            if (
                override.slug == slug
                and match.home_team == override.home_team
                and match.away_team == override.away_team
            ):
                match.date_label = override.date_label
                if override.heure is not None:
                    match.heure = override.heure
