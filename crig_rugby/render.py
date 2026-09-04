"""Génération des fichiers HTML statiques à partir des données scrutées."""

from __future__ import annotations

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import Competition, Config
from .models import CompetitionData, Match

# (matchs à venir, horodatage de la dernière mise à jour, données de repli)
AgendaEntry = tuple[list[Match], str | None, bool]

_DISPLAY_TZ = ZoneInfo("Europe/Paris")

_MOIS_FR = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "décembre": 12,
}
_DATE_LABEL_RE = re.compile(r"^(\w+)?\s*(\d{1,2})\s+(\w+)\s+(\d{4})")
_POULE_SUFFIX_RE = re.compile(r"\s*-\s*Poule\s+\S+$", re.IGNORECASE)


def _format_updated_at(updated_at: str | None) -> str:
    if not updated_at:
        return "jamais"
    try:
        dt = datetime.fromisoformat(updated_at)
    except ValueError:
        return updated_at
    return dt.astimezone(_DISPLAY_TZ).strftime("%d/%m/%Y à %H:%M")


def _parse_date_label(date_label: str) -> date | None:
    """Reconstruit une date à partir d'un libellé français (ex: "samedi 26
    septembre 2026"). Le site source ne fournit pas de date machine-readable
    (pas d'attribut `datetime` sur les <time>)."""
    match = _DATE_LABEL_RE.match(date_label)
    if not match:
        return None
    _, day, month_name, year = match.groups()
    month = _MOIS_FR.get(month_name.lower())
    if month is None:
        return None
    return date(int(year), month, int(day))


def _format_agenda_date(date_label: str, heure: str | None) -> str:
    """Reformate un libellé français ("samedi 26 septembre 2026") en
    "samedi 26/09/2026", complété par l'heure si connue."""
    match = _DATE_LABEL_RE.match(date_label)
    parsed = _parse_date_label(date_label)
    if match is None or parsed is None:
        formatted = date_label
    else:
        weekday = match.group(1)
        numeric = parsed.strftime("%d/%m/%Y")
        formatted = f"{weekday} {numeric}" if weekday else numeric
    return f"{formatted} — {heure}" if heure else formatted


def _short_category_label(label: str) -> str:
    """Retire la mention "- Poule X" du libellé complet d'une compétition,
    pour l'affichage compact de l'agenda (le libellé complet reste utilisé
    tel quel sur les pages catégorie)."""
    return _POULE_SUFFIX_RE.sub("", label)


def _build_agenda(
    agenda_data: dict[str, AgendaEntry],
    competitions_by_slug: dict[str, Competition],
    max_entries: int = 5,
) -> list[dict]:
    """Les prochains matchs à venir, toutes catégories confondues, triés
    chronologiquement (peut inclure plusieurs matchs d'une même catégorie si
    son calendrier est plus rempli que celui des autres). Source : la fiche
    équipe complète de chaque catégorie (`equipe_url`), pas le classement de
    poule — donne le calendrier entier même en pré-saison. L'ordre domicile /
    extérieur d'origine est conservé tel quel (pas de normalisation CRIG en
    tête : ce serait faux quand CRIG reçoit à l'extérieur)."""
    entries = []
    for slug, (matches, _, _) in agenda_data.items():
        competition = competitions_by_slug[slug]
        upcoming = [m for m in matches if not m.played]
        for match in upcoming:
            # La fiche équipe (equipe_url) ne donne pas l'heure du match (seule
            # la page de poule l'a) : on retombe sur l'heure habituelle de la
            # catégorie, configurée dans config.yaml.
            heure = match.heure or competition.heure_habituelle
            sort_key = (_parse_date_label(match.date_label) or date.max, heure or "23:59")
            entries.append(
                {
                    "sort_key": sort_key,
                    "category_label": _short_category_label(competition.label),
                    "match": match,
                    "date_display": _format_agenda_date(match.date_label, heure),
                }
            )
    entries.sort(key=lambda e: e["sort_key"])
    return entries[:max_entries]


def _make_env(config: Config) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(config.templates_dir)),
        autoescape=select_autoescape(["html"]),
    )


def render_all(
    config: Config,
    all_data: list[CompetitionData],
    agenda_data: dict[str, AgendaEntry],
) -> None:
    env = _make_env(config)
    category_template = env.get_template("category.html")
    rotator_template = env.get_template("rotator.html")
    agenda_template = env.get_template("agenda.html")

    config.output_dir.mkdir(parents=True, exist_ok=True)

    competitions_by_slug = {comp.slug: comp for comp in config.competitions}
    all_competitions = config.competitions

    for data in all_data:
        competition = competitions_by_slug[data.slug]
        next_match = data.calendar[0] if data.calendar else data.first_match

        html = category_template.render(
            competition=competition,
            all_competitions=all_competitions,
            data=data,
            team_name=config.team_name,
            club_aliases=config.club_aliases,
            next_match=next_match,
            updated_at_display=_format_updated_at(data.updated_at),
        )
        (config.output_dir / f"{data.slug}.html").write_text(html, encoding="utf-8")

    rotator_html = rotator_template.render(
        pages=[comp.slug for comp in all_competitions],
        rotation_seconds=config.rotation_seconds,
    )
    (config.output_dir / "index.html").write_text(rotator_html, encoding="utf-8")

    agenda_updated_ats = [updated_at for _, updated_at, _ in agenda_data.values() if updated_at]
    agenda_html = agenda_template.render(
        all_competitions=all_competitions,
        team_name=config.team_name,
        club_aliases=config.club_aliases,
        agenda=_build_agenda(agenda_data, competitions_by_slug),
        any_stale=any(stale for _, _, stale in agenda_data.values()),
        updated_at_display=_format_updated_at(max(agenda_updated_ats) if agenda_updated_ats else None),
    )
    (config.output_dir / "agenda.html").write_text(agenda_html, encoding="utf-8")
