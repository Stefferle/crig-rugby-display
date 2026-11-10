"""Tests des corrections manuelles (overrides.yaml), en particulier l'inversion."""

from crig_rugby.models import Match
from crig_rugby.overrides import MatchOverride, apply_overrides, load_overrides


def _match(home: str, away: str, date_label: str = "samedi 7 novembre 2026") -> Match:
    return Match(
        date_label=date_label,
        journee="7",
        heure="15:00",
        home_team=home,
        away_team=away,
        home_score=None,
        away_score=None,
        played=False,
        home_logo=f"{home}.webp",
        away_logo=f"{away}.webp",
    )


def test_inversion_swaps_teams_and_logos():
    match = _match("Saint Claude", "Illkirch Graffenstaden")
    override = MatchOverride(
        slug="f2", home_team="Saint Claude", away_team="Illkirch Graffenstaden", inverser=True
    )

    apply_overrides([match], "f2", [override])

    assert (match.home_team, match.away_team) == ("Illkirch Graffenstaden", "Saint Claude")
    assert (match.home_logo, match.away_logo) == ("Illkirch Graffenstaden.webp", "Saint Claude.webp")
    assert match.inverted
    assert match.site_teams == ("Saint Claude", "Illkirch Graffenstaden")
    # inversion seule : date et heure inchangées
    assert match.date_label == "samedi 7 novembre 2026"
    assert match.heure == "15:00"


def test_inversion_is_idempotent():
    """Les corrections sont réappliquées à chaque `generate` sur le cache,
    déjà corrigé : le match ne doit pas être ré-inversé."""
    match = _match("Saint Claude", "Illkirch Graffenstaden")
    override = MatchOverride(
        slug="f2", home_team="Saint Claude", away_team="Illkirch Graffenstaden", inverser=True
    )

    apply_overrides([match], "f2", [override])
    apply_overrides([match], "f2", [override])

    assert (match.home_team, match.away_team) == ("Illkirch Graffenstaden", "Saint Claude")


def test_inverted_aller_not_confused_with_retour():
    """Après inversion, l'aller A-B s'affiche B-A comme le retour : une
    correction de date visant le retour ne doit pas toucher l'aller."""
    aller = _match("Saint Claude", "Illkirch Graffenstaden")
    retour = _match("Illkirch Graffenstaden", "Saint Claude", "dimanche 7 mars 2027")
    overrides = [
        MatchOverride(
            slug="f2", home_team="Saint Claude", away_team="Illkirch Graffenstaden", inverser=True
        ),
        MatchOverride(
            slug="f2",
            home_team="Illkirch Graffenstaden",
            away_team="Saint Claude",
            date_label="samedi 6 mars 2027",
        ),
    ]

    apply_overrides([aller, retour], "f2", overrides)
    apply_overrides([aller, retour], "f2", overrides)  # 2e passage, comme `generate`

    assert aller.date_label == "samedi 7 novembre 2026"
    assert retour.date_label == "samedi 6 mars 2027"
    assert not retour.inverted


def test_other_category_untouched():
    match = _match("Saint Claude", "Illkirch Graffenstaden")
    override = MatchOverride(
        slug="fb", home_team="Saint Claude", away_team="Illkirch Graffenstaden", inverser=True
    )

    apply_overrides([match], "f2", [override])

    assert not match.inverted


def test_load_overrides_optional_fields(tmp_path):
    path = tmp_path / "overrides.yaml"
    path.write_text(
        "overrides:\n"
        "  - slug: f2\n"
        "    home_team: \"Saint Claude\"\n"
        "    away_team: \"Illkirch Graffenstaden\"\n"
        "    inverser: true\n"
        "  - slug: fb\n"
        "    home_team: \"Saint Claude\"\n"
        "    away_team: \"Illkirch Graffenstaden\"\n"
        "    date_label: \"samedi 7 novembre 2026\"\n",
        encoding="utf-8",
    )

    inversion, report = load_overrides(path)

    assert inversion.inverser and inversion.date_label is None
    assert not report.inverser and report.date_label == "samedi 7 novembre 2026"
