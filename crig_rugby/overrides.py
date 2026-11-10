"""Corrections manuelles d'un match à venir : date/heure et/ou inversion.

Sert de filet de sécurité quand coeurdurugby.com n'a pas (encore) répercuté
un changement de programmation (ex: match avancé au samedi soir, ou match
inversé : joué chez le club qui devait se déplacer) : on recherche le match
par équipes (noms tels que scrapés, avant club_aliases, dans l'ordre
domicile/extérieur d'origine du site) dans chaque catégorie, et on le
corrige juste avant la mise en cache. Rechargé à chaque cycle de scraping,
sans redémarrage nécessaire.
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
    date_label: str | None = None
    heure: str | None = None
    inverser: bool = False


def load_overrides(path: Path) -> list[MatchOverride]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [
        MatchOverride(
            slug=item["slug"],
            home_team=item["home_team"],
            away_team=item["away_team"],
            date_label=item.get("date_label"),
            heure=item.get("heure"),
            inverser=bool(item.get("inverser", False)),
        )
        for item in raw.get("overrides") or []
    ]


def apply_overrides(matches: list[Match], slug: str, overrides: list[MatchOverride]) -> None:
    """Modifie en place les Match qui correspondent à une correction déclarée
    pour cette catégorie.

    La correspondance se fait toujours sur l'ordre d'origine du site
    (`Match.site_teams`), pas sur l'ordre affiché : les corrections sont
    réappliquées à chaque `generate` sur des données déjà corrigées en cache,
    et le match retour (B-A) ne doit pas être confondu avec un aller (A-B)
    déjà inversé. Pour la même raison, l'inversion n'est faite qu'une fois."""
    for match in matches:
        site_teams = match.site_teams
        for override in overrides:
            if override.slug != slug or site_teams != (override.home_team, override.away_team):
                continue
            if override.date_label is not None:
                match.date_label = override.date_label
            if override.heure is not None:
                match.heure = override.heure
            if override.inverser and not match.inverted:
                match.invert()
