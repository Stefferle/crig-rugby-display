"""Orchestration : scrape chaque compétition, avec repli sur le cache en cas d'échec."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from . import cache
from .config import Competition, Config
from .models import CompetitionData, Match
from .scraper import (
    ScrapeError,
    fetch_html,
    find_classement_url,
    parse_poule_preview,
    parse_standings,
    parse_team_page,
)

logger = logging.getLogger(__name__)


def scrape_competition(competition: Competition, config: Config) -> CompetitionData:
    try:
        resultats_html = fetch_html(competition.resultats_url, config)
        classement_url = find_classement_url(resultats_html, competition.resultats_url)

        classement_html = fetch_html(classement_url, config)
        standings, team_page_url = parse_standings(classement_html, config.team_name)

        if not standings:
            # Saison pas encore commencée : classement vide sur le site. On
            # affiche à la place les clubs engagés et le premier match, tirés
            # de la page résultats (voir docstring de `parse_poule_preview`).
            engaged_clubs, first_match = parse_poule_preview(resultats_html, config.team_name)
            data = CompetitionData(
                slug=competition.slug,
                label=competition.label,
                engaged_clubs=engaged_clubs,
                first_match=first_match,
                updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                stale=False,
                error=None,
            )
            cache.save(config.cache_dir, data)
            return data

        if team_page_url is None:
            raise ScrapeError(
                f"Équipe '{config.team_name}' introuvable dans le classement de "
                f"{competition.label}"
            )

        team_html = fetch_html(team_page_url, config)
        results, upcoming = parse_team_page(team_html)

        data = CompetitionData(
            slug=competition.slug,
            label=competition.label,
            standings=standings,
            results=results,
            calendar=upcoming,
            updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            stale=False,
            error=None,
        )
        cache.save(config.cache_dir, data)
        return data

    except ScrapeError as exc:
        logger.error("Échec du scraping pour %s : %s", competition.label, exc)
        previous = cache.load(config.cache_dir, competition.slug)
        if previous is not None:
            previous.stale = True
            previous.error = str(exc)
            return previous
        return CompetitionData(
            slug=competition.slug,
            label=competition.label,
            error=str(exc),
            stale=True,
        )


def scrape_all(config: Config) -> list[CompetitionData]:
    return [scrape_competition(comp, config) for comp in config.competitions]


AgendaEntry = tuple[list[Match], str | None, bool]  # (matchs, updated_at, stale)


def scrape_agenda_matches(competition: Competition, config: Config) -> AgendaEntry:
    """Calendrier complet de l'équipe, lu directement sur sa fiche
    (`equipe_url`), indépendamment de l'état du classement de sa poule.
    Alimente uniquement la page agenda multi-catégories — n'affecte pas les
    pages catégorie, qui gardent leur propre logique pré-saison/saison."""
    try:
        html = fetch_html(competition.equipe_url, config)
        _, calendar = parse_team_page(html)
        updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cache.save_agenda_matches(config.cache_dir, competition.slug, calendar, updated_at)
        return calendar, updated_at, False
    except ScrapeError as exc:
        logger.error("Échec du scraping agenda pour %s : %s", competition.label, exc)
        previous = cache.load_agenda_matches(config.cache_dir, competition.slug)
        if previous is not None:
            matches, updated_at = previous
            return matches, updated_at, True
        return [], None, True


def scrape_all_agenda(config: Config) -> dict[str, AgendaEntry]:
    return {comp.slug: scrape_agenda_matches(comp, config) for comp in config.competitions}


def load_all_agenda_from_cache(config: Config) -> dict[str, AgendaEntry]:
    result: dict[str, AgendaEntry] = {}
    for comp in config.competitions:
        cached = cache.load_agenda_matches(config.cache_dir, comp.slug)
        if cached is None:
            result[comp.slug] = ([], None, False)
        else:
            matches, updated_at = cached
            result[comp.slug] = (matches, updated_at, False)
    return result
