"""Génération des fichiers HTML statiques à partir des données scrutées."""

from __future__ import annotations

from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import Config
from .models import CompetitionData


def _format_updated_at(updated_at: str | None) -> str:
    if not updated_at:
        return "jamais"
    try:
        dt = datetime.fromisoformat(updated_at)
    except ValueError:
        return updated_at
    return dt.strftime("%d/%m/%Y à %H:%M")


def _make_env(config: Config) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(config.templates_dir)),
        autoescape=select_autoescape(["html"]),
    )


def render_all(config: Config, all_data: list[CompetitionData]) -> None:
    env = _make_env(config)
    category_template = env.get_template("category.html")
    rotator_template = env.get_template("rotator.html")

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
            next_match=next_match,
            updated_at_display=_format_updated_at(data.updated_at),
        )
        (config.output_dir / f"{data.slug}.html").write_text(html, encoding="utf-8")

    rotator_html = rotator_template.render(
        pages=[comp.slug for comp in all_competitions],
        rotation_seconds=config.rotation_seconds,
    )
    (config.output_dir / "index.html").write_text(rotator_html, encoding="utf-8")
