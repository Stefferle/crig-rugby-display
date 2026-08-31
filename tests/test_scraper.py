"""Tests de parsing sur des pages réelles de coeurdurugby.com (figées en fixtures).

Ces fixtures ont été téléchargées le 31/08/2026, avant le début de la saison
2026-2027 (13/09/2026) : aucun match n'y est encore joué. Les scores ne sont
donc pas couverts ici — à compléter dès que de vrais résultats existent.
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

    assert results == []  # saison pas commencée
    assert len(calendar) == 21

    first = calendar[0]
    assert first.journee == "J1"
    assert "13 septembre 2026" in first.date_label
    assert first.home_team == "Villefranche Sur Saone"
    assert first.away_team == "Illkirch Graffenstaden"
    assert first.played is False
