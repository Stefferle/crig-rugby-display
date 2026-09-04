"""Persistance du dernier snapshot valide de chaque compétition.

Sert de filet de sécurité : si une compétition ne peut pas être scrutée
(site indisponible, page modifiée...), on continue à afficher son dernier
snapshot connu plutôt que de casser l'affichage.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import CompetitionData, EngagedClub, Match, StandingRow


def _cache_path(cache_dir: Path, slug: str) -> Path:
    return cache_dir / f"{slug}.json"


def save(cache_dir: Path, data: CompetitionData) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir, data.slug)
    path.write_text(
        json.dumps(asdict(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load(cache_dir: Path, slug: str) -> CompetitionData | None:
    path = _cache_path(cache_dir, slug)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    first_match_raw = raw.get("first_match")
    return CompetitionData(
        slug=raw["slug"],
        label=raw["label"],
        team_id=raw.get("team_id"),
        standings=[StandingRow(**row) for row in raw.get("standings", [])],
        results=[Match(**m) for m in raw.get("results", [])],
        calendar=[Match(**m) for m in raw.get("calendar", [])],
        engaged_clubs=[EngagedClub(**c) for c in raw.get("engaged_clubs", [])],
        first_match=Match(**first_match_raw) if first_match_raw else None,
        updated_at=raw.get("updated_at"),
        stale=raw.get("stale", False),
        error=raw.get("error"),
    )


def _agenda_cache_path(cache_dir: Path, slug: str) -> Path:
    return cache_dir / f"agenda_{slug}.json"


def save_agenda_matches(cache_dir: Path, slug: str, matches: list[Match], updated_at: str) -> None:
    """Cache dédié à l'agenda multi-catégories : la fiche équipe complète
    (via `equipe_url`), indépendante du snapshot par catégorie (`save`/`load`
    ci-dessus) pour ne pas modifier ce qui alimente les pages catégorie."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _agenda_cache_path(cache_dir, slug)
    payload = {"updated_at": updated_at, "matches": [asdict(m) for m in matches]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_agenda_matches(cache_dir: Path, slug: str) -> tuple[list[Match], str | None] | None:
    path = _agenda_cache_path(cache_dir, slug)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Match(**m) for m in raw.get("matches", [])], raw.get("updated_at")
