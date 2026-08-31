"""Récupération et parsing des pages coeurdurugby.com.

Le site n'utilise pas d'API : on parse le HTML directement avec BeautifulSoup.
Pour limiter la fragilité, chaque étape de navigation suit un lien réellement
présent sur la page précédente plutôt que de reconstruire une URL à la main
(l'identifiant de division dans l'URL des classements n'est pas prévisible).

Point de vigilance (voir README) : la saison 2026-2027 démarre le 13/09/2026,
donc au moment d'écrire ce module aucune page ne contient de match déjà joué.
Le parsing des scores dans `_extract_score` est donc écrit par inférence sur
les classes CSS observées côté calendrier/classement, mais n'a pas pu être
vérifié sur un vrai résultat. À recontrôler dès les premiers matchs joués.
"""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import Config
from .models import EngagedClub, Match, StandingRow

logger = logging.getLogger(__name__)

BASE_SITE_URL = "https://coeurdurugby.com/"


class ScrapeError(RuntimeError):
    """Erreur lors de la récupération ou du parsing d'une page source."""


def fetch_html(url: str, config: Config) -> str:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": config.user_agent},
            timeout=config.request_timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ScrapeError(f"Échec de la récupération de {url} : {exc}") from exc
    time.sleep(config.request_delay_seconds)
    return response.text


def _effective_base(soup: BeautifulSoup, fallback_url: str) -> str:
    """coeurdurugby.com déclare <base href="https://coeurdurugby.com/">, donc les
    liens relatifs (sans '/' initial) se résolvent contre ce base, pas contre
    l'URL de la page courante."""
    base_tag = soup.find("base", href=True)
    return base_tag["href"] if base_tag else fallback_url


def find_classement_url(resultats_html: str, resultats_url: str) -> str:
    soup = BeautifulSoup(resultats_html, "html.parser")
    link = soup.find("a", string=re.compile(r"Consulter le classement", re.IGNORECASE))
    if link is None or not link.get("href"):
        raise ScrapeError(
            f"Lien 'Consulter le classement' introuvable sur {resultats_url}"
        )
    return urljoin(_effective_base(soup, resultats_url), link["href"])


_STANDING_COLUMNS = (
    "rank",
    "team",
    "points",
    "played",
    "won",
    "drawn",
    "lost",
    "scored_for",
    "scored_against",
    "diff",
)


def parse_standings(
    classement_html: str, team_name: str
) -> tuple[list[StandingRow], str | None]:
    """Retourne (lignes de classement, URL de la fiche équipe du club suivi)."""
    soup = BeautifulSoup(classement_html, "html.parser")
    table = soup.find("table", class_="standing")
    if table is None:
        raise ScrapeError("Tableau de classement introuvable sur la page")

    base = _effective_base(soup, BASE_SITE_URL)
    rows: list[StandingRow] = []
    team_page_url: str | None = None
    body_rows = table.find_all("tr")[1:]  # la 1re ligne est le header
    for tr in body_rows:
        cells = tr.find_all("td")
        if len(cells) < len(_STANDING_COLUMNS):
            logger.warning("Ligne de classement inattendue, colonnes manquantes : %s", tr)
            continue

        name_link = cells[1].find("a")
        name = name_link.get_text(strip=True) if name_link else cells[1].get_text(strip=True)
        is_crig = name.strip().lower() == team_name.strip().lower()
        if is_crig and name_link and name_link.get("href"):
            team_page_url = urljoin(base, name_link["href"])

        logo_img = cells[1].find("img")
        logo_url = urljoin(base, logo_img["src"]) if logo_img and logo_img.get("src") else None

        values = {
            "rank": cells[0].get_text(strip=True),
            "team": name,
            "logo_url": logo_url,
        }
        for column, cell in zip(_STANDING_COLUMNS[2:], cells[2:]):
            values[column] = cell.get_text(strip=True)

        rows.append(StandingRow(is_crig=is_crig, **values))

    return rows, team_page_url


def parse_poule_preview(
    resultats_html: str, team_name: str
) -> tuple[list[EngagedClub], Match | None]:
    """Avant le début de saison, le classement est vide (voir `parse_standings`) :
    on reconstruit à la place, depuis la page résultats déjà récupérée, la liste
    des clubs engagés dans la poule (déduite des matchs de la journée en cours)
    et le premier match du club suivi.
    """
    soup = BeautifulSoup(resultats_html, "html.parser")
    section = soup.find("section", class_="teamGames")
    if section is None:
        return [EngagedClub(name=team_name)], None

    base = _effective_base(soup, BASE_SITE_URL)
    clubs: dict[str, str | None] = {}
    first_match: Match | None = None
    current_date = ""

    def team_info(span) -> tuple[str, str | None]:
        if span is None:
            return "?", None
        link = span.find("a")
        name = link.get_text(strip=True) if link else "?"
        img = span.find("img")
        logo_url = urljoin(base, img["src"]) if img and img.get("src") else None
        return name, logo_url

    for p in section.find_all("p", class_="teamCalendar"):
        date_tag = p.find("time", class_="date")
        if date_tag:
            current_date = date_tag.get_text(strip=True)
        heure_tag = p.find("time", class_="heure")
        heure = heure_tag.get_text(strip=True) if heure_tag else None

        home, home_logo = team_info(p.find("span", class_="eqL"))
        away, away_logo = team_info(p.find("span", class_="eqR"))
        clubs.setdefault(home, home_logo)
        clubs.setdefault(away, away_logo)

        if team_name in (home, away):
            first_match = Match(
                date_label=current_date,
                journee=None,
                heure=heure,
                home_team=home,
                away_team=away,
                home_logo=home_logo,
                away_logo=away_logo,
                home_score=None,
                away_score=None,
                played=False,
            )

    team_logo = clubs.pop(team_name, None)
    engaged_clubs = [EngagedClub(name=team_name, logo_url=team_logo)] + [
        EngagedClub(name=name, logo_url=logo) for name, logo in sorted(clubs.items())
    ]

    return engaged_clubs, first_match


def _clean_text(tag) -> str:
    return tag.get_text(" ", strip=True) if tag is not None else ""


def _extract_score(span) -> str | None:
    """Best-effort : cherche un score numérique dans un span équipe.

    Non vérifié sur un vrai match joué (saison pas commencée) — voir le
    commentaire en tête de module.
    """
    if span is None:
        return None
    for tag in span.find_all(["big", "strong", "span"]):
        text = tag.get_text(strip=True)
        if text.isdigit():
            return text
    return None


def _parse_team_games(section, base: str) -> list[Match]:
    matches: list[Match] = []
    for p in section.find_all("p", class_="teamGames"):
        time_tag = p.find("time", class_="date")
        journee_span = time_tag.find("span") if time_tag else None
        journee = journee_span.get_text(strip=True) if journee_span else None
        date_label = _clean_text(time_tag)
        if journee and date_label:
            date_label = date_label.replace(journee, "").strip()

        heure_tag = p.find("time", class_="heure")
        heure = heure_tag.get_text(strip=True) if heure_tag else None

        home_span = p.find("span", class_="team_left")
        away_span = p.find("span", class_="team_right")

        def team_info(span) -> tuple[str, str | None]:
            if span is None:
                return "?", None
            img = span.find("img")
            name = img["alt"] if img and img.get("alt") else (span.get_text(strip=True) or "?")
            logo_url = urljoin(base, img["src"]) if img and img.get("src") else None
            return name, logo_url

        home_team, home_logo = team_info(home_span)
        away_team, away_logo = team_info(away_span)

        matches.append(
            Match(
                date_label=date_label,
                journee=journee,
                heure=heure,
                home_team=home_team,
                away_team=away_team,
                home_logo=home_logo,
                away_logo=away_logo,
                home_score=_extract_score(home_span),
                away_score=_extract_score(away_span),
                played=False,  # ajusté par l'appelant selon la section d'origine
            )
        )
    return matches


def parse_team_page(team_html: str) -> tuple[list[Match], list[Match]]:
    """Retourne (résultats joués, calendrier à venir) pour la fiche équipe."""
    soup = BeautifulSoup(team_html, "html.parser")
    base = _effective_base(soup, BASE_SITE_URL)
    results: list[Match] = []
    calendar: list[Match] = []

    for section in soup.find_all("section", class_="teamResults"):
        heading = section.find("h2")
        title = heading.get_text(strip=True) if heading else ""
        matches = _parse_team_games(section, base)
        if title.startswith("Résultats"):
            for match in matches:
                match.played = True
            results.extend(matches)
        elif title.startswith("Calendrier"):
            calendar.extend(matches)

    return results, calendar
