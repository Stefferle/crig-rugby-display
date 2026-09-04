"""Orchestration : scrape chaque compétition, avec repli sur le cache en cas d'échec."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from . import cache
from .config import Competition, Config
from .models import CompetitionData, Match
from .overrides import MatchOverride, apply_overrides, load_overrides
from .scraper import (
    ScrapeError,
    fetch_html,
    find_classement_url,
    parse_poule_preview,
    parse_standings,
    parse_team_page,
)

logger = logging.getLogger(__name__)


def _apply_overrides_to_data(data: CompetitionData, overrides: list[MatchOverride]) -> None:
    apply_overrides(data.results, data.slug, overrides)
    apply_overrides(data.calendar, data.slug, overrides)
    if data.first_match is not None:
        apply_overrides([data.first_match], data.slug, overrides)


def scrape_competition(
    competition: Competition, config: Config, overrides: list[MatchOverride]
) -> CompetitionData:
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
            _apply_overrides_to_data(data, overrides)
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
        _apply_overrides_to_data(data, overrides)
        cache.save(config.cache_dir, data)
        return data

    except ScrapeError as exc:
        logger.error("Échec du scraping pour %s : %s", competition.label, exc)
        previous = cache.load(config.cache_dir, competition.slug)
        if previous is not None:
            previous.stale = True
            previous.error = str(exc)
            _apply_overrides_to_data(previous, overrides)
            return previous
        return CompetitionData(
            slug=competition.slug,
            label=competition.label,
            error=str(exc),
            stale=True,
        )


def scrape_all(config: Config) -> list[CompetitionData]:
    overrides = load_overrides(config.overrides_path)
    return [scrape_competition(comp, config, overrides) for comp in config.competitions]


def load_all_from_cache(config: Config) -> list[CompetitionData | None]:
    """Comme `scrape_all`, mais sans requête réseau : relit le dernier
    snapshot en cache pour chaque catégorie (utilisé par `generate`).
    Les corrections de `overrides.yaml` sont réappliquées à chaque appel,
    donc un changement y prend effet même sans relancer `scrape`."""
    overrides = load_overrides(config.overrides_path)
    result: list[CompetitionData | None] = []
    for comp in config.competitions:
        data = cache.load(config.cache_dir, comp.slug)
        if data is not None:
            _apply_overrides_to_data(data, overrides)
        result.append(data)
    return result


AgendaEntry = tuple[list[Match], str | None, bool]  # (matchs, updated_at, stale)


def scrape_agenda_matches(
    competition: Competition, config: Config, overrides: list[MatchOverride]
) -> AgendaEntry:
    """Calendrier complet de l'équipe, lu directement sur sa fiche
    (`equipe_url`), indépendamment de l'état du classement de sa poule.
    Alimente uniquement la page agenda multi-catégories — n'affecte pas les
    pages catégorie, qui gardent leur propre logique pré-saison/saison."""
    try:
        html = fetch_html(competition.equipe_url, config)
        _, calendar = parse_team_page(html)
        apply_overrides(calendar, competition.slug, overrides)
        updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cache.save_agenda_matches(config.cache_dir, competition.slug, calendar, updated_at)
        return calendar, updated_at, False
    except ScrapeError as exc:
        logger.error("Échec du scraping agenda pour %s : %s", competition.label, exc)
        previous = cache.load_agenda_matches(config.cache_dir, competition.slug)
        if previous is not None:
            matches, updated_at = previous
            apply_overrides(matches, competition.slug, overrides)
            return matches, updated_at, True
        return [], None, True


def scrape_all_agenda(config: Config) -> dict[str, AgendaEntry]:
    overrides = load_overrides(config.overrides_path)
    return {comp.slug: scrape_agenda_matches(comp, config, overrides) for comp in config.competitions}


def load_all_agenda_from_cache(config: Config) -> dict[str, AgendaEntry]:
    """Comme `scrape_all_agenda`, mais sans requête réseau (voir
    `load_all_from_cache`)."""
    overrides = load_overrides(config.overrides_path)
    result: dict[str, AgendaEntry] = {}
    for comp in config.competitions:
        cached = cache.load_agenda_matches(config.cache_dir, comp.slug)
        if cached is None:
            result[comp.slug] = ([], None, False)
        else:
            matches, updated_at = cached
            apply_overrides(matches, comp.slug, overrides)
            result[comp.slug] = (matches, updated_at, False)
    return result
