"""Tests de la logique d'affichage (render.py)."""

from datetime import date

from crig_rugby.models import Match
from crig_rugby.render import _is_upcoming


def _match(date_label: str, played: bool = False) -> Match:
    return Match(
        date_label=date_label,
        journee="J3",
        heure="15:00",
        home_team="Drusenheim",
        away_team="Illkirch Graffenstaden",
        home_score=None,
        away_score=None,
        played=played,
    )


def test_past_unplayed_match_is_not_upcoming():
    """Ex. forfait de Drusenheim en R3 (J3 du 11/10/2026) : jamais de score
    sur la fiche équipe, le match ne doit pas rester "Prochain match"."""
    today = date(2026, 11, 10)
    assert not _is_upcoming(_match("dimanche 11 octobre 2026"), today)
    assert _is_upcoming(_match("dimanche 15 novembre 2026"), today)
    assert _is_upcoming(_match("mardi 10 novembre 2026"), today)  # le jour même
    assert not _is_upcoming(_match("dimanche 15 novembre 2026", played=True), today)
