"""Chargement et validation de config.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Competition:
    slug: str
    label: str
    resultats_url: str
    equipe_url: str
    heure_habituelle: str | None = None


@dataclass
class Config:
    team_name: str
    competitions: list[Competition]
    club_aliases: dict[str, str] = field(default_factory=dict)
    port: int = 8090
    rotation_seconds: int = 20
    weekend_start: int = 7
    weekend_end: int = 22
    weekend_interval_minutes: int = 60
    weekday_daily_hour: int = 7
    request_timeout: int = 15
    request_delay_seconds: float = 1.0
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 CRIGRugbyDisplay/1.0"
    )

    @property
    def cache_dir(self) -> Path:
        return BASE_DIR / "data" / "cache"

    @property
    def output_dir(self) -> Path:
        return BASE_DIR / "output"

    @property
    def templates_dir(self) -> Path:
        return BASE_DIR / "templates"

    @property
    def static_dir(self) -> Path:
        return BASE_DIR / "static"

    @property
    def overrides_path(self) -> Path:
        return BASE_DIR / "overrides.yaml"


def load_config(path: Path | str | None = None) -> Config:
    config_path = Path(path) if path else BASE_DIR / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    competitions = [
        Competition(
            slug=item["slug"],
            label=item["label"],
            resultats_url=item["resultats_url"],
            equipe_url=item["equipe_url"],
            heure_habituelle=item.get("heure_habituelle"),
        )
        for item in raw["competitions"]
    ]

    schedule = raw.get("schedule", {})
    server = raw.get("server", {})
    scraping = raw.get("scraping", {})

    return Config(
        team_name=raw["team_name"],
        competitions=competitions,
        club_aliases=raw.get("club_aliases", {}),
        port=server.get("port", 8090),
        rotation_seconds=server.get("rotation_seconds", 20),
        weekend_start=schedule.get("weekend_start", 7),
        weekend_end=schedule.get("weekend_end", 22),
        weekend_interval_minutes=schedule.get("weekend_interval_minutes", 60),
        weekday_daily_hour=schedule.get("weekday_daily_hour", 7),
        request_timeout=scraping.get("request_timeout", 15),
        request_delay_seconds=scraping.get("request_delay_seconds", 1.0),
    )
