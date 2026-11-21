"""Corrections manuelles d'un match : date/heure, inversion et/ou score.

Sert de filet de sécurité quand coeurdurugby.com n'a pas (encore) répercuté
un changement de programmation (ex: match avancé au samedi soir, ou match
inversé : joué chez le club qui devait se déplacer) : on recherche le match
par équipes (noms tels que scrapés, avant club_aliases, dans l'ordre
domicile/extérieur d'origine du site) dans chaque catégorie, et on le
corrige juste avant la mise en cache. Rechargé à chaque cycle de scraping,
sans redémarrage nécessaire.

Le même fichier permet aussi d'écarter du classement un club que le site
y fait figurer à tort (section `exclusions_classement`, voir
`apply_standing_exclusions`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .models import CompetitionData, Match


@dataclass
class StandingExclusion:
    slug: str
    # Nom EXACT tel que scrapé (avant club_aliases), comme partout ailleurs.
    team: str


@dataclass
class MatchOverride:
    slug: str
    home_team: str
    away_team: str
    date_label: str | None = None
    heure: str | None = None
    inverser: bool = False
    # Score forcé (domicile, extérieur), dans l'ordre AFFICHÉ, c.-à-d. après
    # une éventuelle inversion. Sert quand le site garde l'ordre d'origine
    # des équipes d'un match inversé mais saisit le score dans l'ordre du
    # match réellement joué (vu en R3 sur Illkirch-Saverne du 15/11/2026) :
    # l'inversion permuterait alors un score déjà « à l'endroit ».
    score: tuple[str, str] | None = None


def _parse_score(raw: object) -> tuple[str, str] | None:
    """« 25-23 » -> ("25", "23"). Les espaces autour du tiret sont tolérés."""
    if raw is None:
        return None
    home, sep, away = str(raw).partition("-")
    if not sep or not home.strip().isdigit() or not away.strip().isdigit():
        raise ValueError(f"Score invalide dans overrides.yaml : {raw!r} (attendu ex. \"25-23\")")
    return home.strip(), away.strip()


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
            score=_parse_score(item.get("score")),
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
    déjà inversé. Pour la même raison, l'inversion n'est faite qu'une fois.
    Le score forcé est appliqué après l'inversion, puisqu'il est exprimé
    dans l'ordre affiché ; il est idempotent par nature."""
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
            if override.score is not None:
                match.home_score, match.away_score = override.score
                match.played = True


def load_standing_exclusions(path: Path) -> list[StandingExclusion]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [
        StandingExclusion(slug=item["slug"], team=item["equipe"])
        for item in raw.get("exclusions_classement") or []
    ]


def _shift_rank(rank: str, removed_ranks: list[int]) -> str:
    """Décale un rang du nombre de clubs écartés classés devant lui. Un rang
    non numérique (cas jamais vu, mais le site est un tiers) est laissé tel quel."""
    if not rank.strip().isdigit():
        return rank
    value = int(rank)
    return str(value - sum(1 for removed in removed_ranks if removed < value))


def apply_standing_exclusions(
    data: CompetitionData, exclusions: list[StandingExclusion]
) -> None:
    """Retire du classement (et de la liste des clubs engagés, en
    pré-saison) les clubs que coeurdurugby.com rattache à tort à la poule
    (ex. Nancy en Fédérale 1 féminine, poule 1, en novembre 2026).

    Les clubs classés derrière un club écarté remontent d'autant de places.
    Idempotent : une fois le club retiré, une nouvelle application (à chaque
    `generate`, sur le cache déjà corrigé) ne trouve plus rien à faire."""
    excluded = {e.team for e in exclusions if e.slug == data.slug}
    if not excluded:
        return
    removed_ranks = [
        int(row.rank)
        for row in data.standings
        if row.team in excluded and row.rank.strip().isdigit()
    ]
    data.standings = [row for row in data.standings if row.team not in excluded]
    for row in data.standings:
        row.rank = _shift_rank(row.rank, removed_ranks)
    data.engaged_clubs = [club for club in data.engaged_clubs if club.name not in excluded]
