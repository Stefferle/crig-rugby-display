"""Tests de parsing sur des pages réelles de coeurdurugby.com (figées en fixtures).

La plupart de ces fixtures ont été téléchargées le 31/08/2026, avant le début
de la saison 2026-2027 (13/09/2026) : aucun match n'y est encore joué.
`federale2_equipe_crig.html` a été rafraîchie le 12/10/2026 (saison en cours,
J1 à J4 joués) après que le site a changé la structure de la fiche équipe
(classes `eqL`/`eqR` + `score-home`/`score-away`, comme la page de poule, au
lieu de l'ancien `team_left`/`team_right`).
"""

from pathlib import Path

from crig_rugby.scraper import (
    find_classement_url,
    parse_poule_preview,
    parse_standings,
    parse_team_page,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_find_classement_url_resolves_relative_link():
    html = _read("federale2_resultats.html")
    url = find_classement_url(
        html, "https://coeurdurugby.com/competitions/federale-2/Qualification/resultats/poule-2"
    )
    assert url == "https://coeurdurugby.com/competitions/federale-2/1/classements/poule-2"


def test_parse_standings_prefilled_table():
    html = _read("top14_classement_prefilled.html")
    rows, team_page_url = parse_standings(html, "Illkirch Graffenstaden")

    assert len(rows) == 14
    assert team_page_url is None  # Illkirch ne joue pas en Top 14

    first = rows[0]
    assert first.rank == "1"
    assert first.team == "Aviron Bayonnais"
    assert first.points == "0"
    assert not first.is_crig
    assert first.logo_url == "https://coeurdurugby.com/assets/images/logos/avironbayonnais.webp"


def test_parse_standings_empty_table_before_season_start():
    html = _read("federale2_classement.html")
    rows, team_page_url = parse_standings(html, "Illkirch Graffenstaden")

    assert rows == []
    assert team_page_url is None


def test_parse_poule_preview_before_season_start():
    html = _read("federale2_resultats.html")
    clubs, first_match = parse_poule_preview(html, "Illkirch Graffenstaden")
    names = [c.name for c in clubs]

    assert names[0] == "Illkirch Graffenstaden"
    assert len(names) == len(set(names)) == 12
    assert clubs[0].logo_url == (
        "https://coeurdurugby.com/assets/images/logos/illkirchgraffenstaden.webp"
    )

    assert first_match is not None
    assert first_match.home_team == "Villefranche Sur Saone"
    assert first_match.away_team == "Illkirch Graffenstaden"
    assert "13 septembre 2026" in first_match.date_label
    assert first_match.heure == "15:15"
    assert first_match.played is False
    assert first_match.away_logo == clubs[0].logo_url


def test_parse_team_page_calendar():
    html = _read("federale2_equipe_crig.html")
    results, calendar = parse_team_page(html)

    assert len(results) == 4
    assert len(calendar) == 18

    # Le site liste les résultats du plus récent au plus ancien (voir le tri
    # explicite par date dans pipeline.py, qui corrige cet ordre avant cache).
    last_played = results[0]
    assert last_played.journee == "J4"
    assert last_played.home_team == "Illkirch Graffenstaden"
    assert last_played.away_team == "Andrezieux Bouthéon"
    assert last_played.home_score == "11"
    assert last_played.away_score == "17"
    assert last_played.played is True

    first_upcoming = calendar[0]
    assert first_upcoming.journee == "J5"
    assert "18 octobre 2026" in first_upcoming.date_label
    assert first_upcoming.home_team == "Nantua"
    assert first_upcoming.away_team == "Illkirch Graffenstaden"
    assert first_upcoming.heure == "15:15"
    assert first_upcoming.played is False
