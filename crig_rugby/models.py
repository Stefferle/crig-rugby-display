"""Structures de données pour une compétition scrutée."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Match:
    date_label: str
    journee: str | None
    heure: str | None
    home_team: str
    away_team: str
    home_score: str | None
    away_score: str | None
    played: bool
    home_logo: str | None = None
    away_logo: str | None = None
    # Vrai si domicile/extérieur ont été permutés par une correction
    # `inverser` de overrides.yaml (voir `overrides.apply_overrides`).
    inverted: bool = False

    @property
    def site_teams(self) -> tuple[str, str]:
        """(domicile, extérieur) tels que publiés par coeurdurugby.com, avant
        une éventuelle inversion manuelle."""
        if self.inverted:
            return self.away_team, self.home_team
        return self.home_team, self.away_team

    def invert(self) -> None:
        """Permute domicile et extérieur (noms, scores, logos)."""
        self.home_team, self.away_team = self.away_team, self.home_team
        self.home_score, self.away_score = self.away_score, self.home_score
        self.home_logo, self.away_logo = self.away_logo, self.home_logo
        self.inverted = not self.inverted

    @property
    def involves_crig(self) -> bool:
        return True  # les Match sont toujours déjà filtrés sur l'équipe CRIG


@dataclass
class StandingRow:
    rank: str
    team: str
    points: str
    played: str
    won: str
    drawn: str
    lost: str
    scored_for: str
    scored_against: str
    diff: str
    is_crig: bool = False
    logo_url: str | None = None


@dataclass
class EngagedClub:
    name: str
    logo_url: str | None = None


@dataclass
class CompetitionData:
    slug: str
    label: str
    team_id: str | None = None
    standings: list[StandingRow] = field(default_factory=list)
    results: list[Match] = field(default_factory=list)
    calendar: list[Match] = field(default_factory=list)
    engaged_clubs: list[EngagedClub] = field(default_factory=list)
    first_match: Match | None = None
    updated_at: str | None = None
    stale: bool = False
    error: str | None = None
