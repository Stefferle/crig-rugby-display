"""Tests de l'export JSON (export.py)."""

import json
from datetime import date

from crig_rugby.config import Competition, Config
from crig_rugby.export import build_export
from crig_rugby.models import CompetitionData, EngagedClub, Match, StandingRow

TODAY = date(2026, 11, 10)


def _config(**kwargs) -> Config:
    return Config(
        team_name="Illkirch Graffenstaden",
        competitions=[
            Competition("f2", "Séniors M - Fédérale 2 - Poule 2", "", "", heure_habituelle="15:15"),
            Competition("fb", "Séniors M - Fédérale B - Poule 2", "", "", heure_habituelle="13:30"),
        ],
        club_aliases={"Illkirch Graffenstaden": "CRIG", "Wolxheim": "MOM"},
        club_logo_overrides={"Wolxheim": "/static/img/logos/logo_mom.png"},
        **kwargs,
    )


def _match(date_label: str, home: str, away: str, played: bool = False, **kwargs) -> Match:
    return Match(
        date_label=date_label,
        journee="J5",
        heure=kwargs.pop("heure", None),
        home_team=home,
        away_team=away,
        home_score=kwargs.pop("home_score", None),
        away_score=kwargs.pop("away_score", None),
        played=played,
        home_logo="https://coeurdurugby.com/logo-home.webp",
        away_logo="https://coeurdurugby.com/logo-away.webp",
        **kwargs,
    )


def _f2_data() -> CompetitionData:
    return CompetitionData(
        slug="f2",
        label="Séniors M - Fédérale 2 - Poule 2",
        standings=[
            StandingRow("1", "Wolxheim", "20", "4", "4", "0", "0", "137", "71", "66"),
            StandingRow("2", "Illkirch Graffenstaden", "19", "4", "4", "0", "0", "115", "69", "46", is_crig=True),
        ],
        results=[
            _match("samedi 31 octobre 2026", "Illkirch Graffenstaden", "Wolxheim", True, home_score="24", away_score="10"),
        ],
        calendar=[
            # Non joué à date passée (ex. forfait) : ne doit pas être le prochain match.
            _match("dimanche 11 octobre 2026", "Meyzieu", "Illkirch Graffenstaden"),
            _match("samedi 14 novembre 2026", "Wolxheim", "Illkirch Graffenstaden", heure="15:00"),
        ],
        updated_at="2026-11-10T07:00:00+00:00",
    )


def test_export_applies_display_rules_and_keeps_raw_names():
    export = build_export(_config(), [_f2_data()], {}, today=TODAY)
    f2 = export["categories"][0]

    assert f2["short_label"] == "Séniors M - Fédérale 2"
    assert not f2["pre_season"]
    assert f2["standings"][1]["team"] == {
        "name": "Illkirch Graffenstaden",
        "display_name": "CRIG",
        "logo": None,
        "is_crig": True,
    }
    assert f2["last_result"]["home_score"] == "24"

    next_match = f2["next_match"]
    assert next_match["date"] == "2026-11-14"
    assert next_match["home"]["name"] == "Wolxheim"  # ordre du site conservé
    assert next_match["home"]["display_name"] == "MOM"
    # Logo de remplacement relatif : laissé tel quel sans public_base_url.
    assert next_match["home"]["logo"] == "/static/img/logos/logo_mom.png"
    assert [m["date"] for m in f2["upcoming"]] == ["2026-11-14"]

    json.dumps(export)  # sérialisable tel quel


def test_export_makes_override_logos_absolute():
    config = _config(export_base_url="https://rugby.example.org/")
    export = build_export(config, [_f2_data()], {}, today=TODAY)
    home = export["categories"][0]["next_match"]["home"]
    assert home["logo"] == "https://rugby.example.org/static/img/logos/logo_mom.png"


def test_export_pre_season_falls_back_on_first_match():
    data = CompetitionData(
        slug="fb",
        label="Séniors M - Fédérale B - Poule 2",
        engaged_clubs=[EngagedClub("Illkirch Graffenstaden"), EngagedClub("Wolxheim")],
        first_match=_match("dimanche 20 septembre 2026", "Illkirch Graffenstaden", "Wolxheim"),
    )
    fb = build_export(_config(), [data], {}, today=date(2026, 9, 1))["categories"][0]
    assert fb["pre_season"]
    assert fb["next_match"]["away"]["display_name"] == "MOM"
    assert [c["display_name"] for c in fb["engaged_clubs"]] == ["CRIG", "MOM"]


def test_export_agenda_groups_doublettes():
    """F2 et FB contre le même adversaire le même jour : une seule entrée,
    avec un créneau par catégorie (heure habituelle si le site n'en donne pas)."""
    agenda_data = {
        "f2": ([_match("samedi 14 novembre 2026", "Wolxheim", "Illkirch Graffenstaden")], "2026-11-10T07:00:00+00:00", False),
        "fb": ([_match("samedi 14 novembre 2026", "Wolxheim", "Illkirch Graffenstaden")], "2026-11-10T07:05:00+00:00", True),
    }
    agenda = build_export(_config(), [], agenda_data, today=TODAY)["agenda"]

    assert agenda["updated_at"] == "2026-11-10T07:05:00+00:00"
    assert agenda["stale"]
    assert len(agenda["matches"]) == 1
    entry = agenda["matches"][0]
    assert entry["date"] == "2026-11-14"
    assert entry["slots"] == [
        {"slug": "fb", "category_label": "Séniors M - Fédérale B", "heure": "13:30"},
        {"slug": "f2", "category_label": "Séniors M - Fédérale 2", "heure": "15:15"},
    ]
