"""Export JSON des données affichées, pour un site tiers (ex. WordPress).

Le JSON reprend exactement ce que montrent les pages HTML (overrides déjà
appliqués, matchs non joués à date passée écartés, doublettes de l'agenda
regroupées) : le site consommateur n'a qu'à l'afficher, sans réimplémenter
la logique de `render.py`. Le format est décrit dans docs/export-json.md.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

from .config import Config
from .dates import parse_date_label
from .models import CompetitionData, Match
from .render import AgendaEntry, _build_agenda, _short_category_label, _upcoming_and_next

# À incrémenter à chaque changement incompatible du format (champ renommé ou
# retiré) : le site consommateur peut ainsi détecter un JSON qu'il ne sait
# pas lire. Ajouter un champ n'est pas un changement incompatible.
SCHEMA_VERSION = 1


def _absolute_url(url: str | None, config: Config) -> str | None:
    """Les logos de remplacement (`club_logo_overrides`) sont souvent des
    chemins relatifs ("/static/img/logos/..."), valables seulement sur le
    serveur de l'afficheur : on les préfixe par `export.public_base_url`
    quand il est configuré, sinon ils restent relatifs."""
    if url and url.startswith("/") and config.export_base_url:
        return config.export_base_url.rstrip("/") + url
    return url


def _team(name: str, scraped_logo: str | None, config: Config) -> dict:
    """`name` est le nom brut du site (stable, à utiliser pour toute
    comparaison) ; `display_name` est l'alias à afficher."""
    return {
        "name": name,
        "display_name": config.club_aliases.get(name, name),
        "logo": _absolute_url(config.club_logo_overrides.get(name, scraped_logo), config),
        "is_crig": name == config.team_name,
    }


def _iso_date(date_label: str) -> str | None:
    parsed = parse_date_label(date_label)
    return parsed.isoformat() if parsed else None


def _match(match: Match | None, config: Config) -> dict | None:
    if match is None:
        return None
    return {
        "date": _iso_date(match.date_label),
        "date_label": match.date_label,
        "journee": match.journee,
        "heure": match.heure,
        "home": _team(match.home_team, match.home_logo, config),
        "away": _team(match.away_team, match.away_logo, config),
        "home_score": match.home_score,
        "away_score": match.away_score,
        "played": match.played,
        "inverted": match.inverted,
    }


def _category(data: CompetitionData, config: Config, today: date) -> dict:
    upcoming, next_match = _upcoming_and_next(data, today)
    return {
        "slug": data.slug,
        "label": data.label,
        "short_label": _short_category_label(data.label),
        "updated_at": data.updated_at,
        "stale": data.stale,
        # Même condition que templates/category.html pour basculer sur
        # l'affichage « clubs de la poule » (voir pipeline.scrape_competition).
        "pre_season": bool(data.engaged_clubs)
        and not data.standings
        and not data.results
        and not data.calendar,
        "standings": [
            {
                "rank": row.rank,
                "team": _team(row.team, row.logo_url, config),
                "points": row.points,
                "played": row.played,
                "won": row.won,
                "drawn": row.drawn,
                "lost": row.lost,
                "scored_for": row.scored_for,
                "scored_against": row.scored_against,
                "diff": row.diff,
            }
            for row in data.standings
        ],
        "last_result": _match(data.results[-1] if data.results else None, config),
        "next_match": _match(next_match, config),
        "upcoming": [_match(m, config) for m in upcoming],
        "engaged_clubs": [_team(c.name, c.logo_url, config) for c in data.engaged_clubs],
    }


def build_export(
    config: Config,
    all_data: list[CompetitionData],
    agenda_data: dict[str, AgendaEntry],
    today: date | None = None,
) -> dict:
    today = today or date.today()
    competitions_by_slug = {comp.slug: comp for comp in config.competitions}

    agenda = []
    for entry in _build_agenda(agenda_data, competitions_by_slug, today=today):
        match = entry["match"]
        agenda.append(
            {
                "date": _iso_date(match.date_label),
                "date_label": match.date_label,
                "home": _team(match.home_team, match.home_logo, config),
                "away": _team(match.away_team, match.away_logo, config),
                "slots": entry["slots"],
            }
        )

    agenda_updated_ats = [updated_at for _, updated_at, _ in agenda_data.values() if updated_at]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "coeurdurugby.com",
        "team_name": config.team_name,
        "categories": [_category(data, config, today) for data in all_data],
        "agenda": {
            "updated_at": max(agenda_updated_ats) if agenda_updated_ats else None,
            "stale": any(stale for _, _, stale in agenda_data.values()),
            "matches": agenda,
        },
    }


def write_export(
    config: Config,
    all_data: list[CompetitionData],
    agenda_data: dict[str, AgendaEntry],
) -> Path:
    path = config.output_dir / "api" / "crig.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(build_export(config, all_data, agenda_data), ensure_ascii=False, indent=2)
    # Écriture atomique : le site consommateur peut lire le fichier à tout
    # moment, il ne doit jamais tomber sur un JSON à moitié écrit.
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)
    return path
