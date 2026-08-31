"""Planification des scrapes : toutes les heures le week-end, 1x/jour en semaine."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import pipeline, render
from .config import Config

logger = logging.getLogger(__name__)


def run_scrape_and_render(config: Config) -> None:
    logger.info("Scraping de toutes les compétitions...")
    data = pipeline.scrape_all(config)
    render.render_all(config, data)
    logger.info("Pages régénérées (%d compétitions).", len(data))


def start_scheduler(config: Config) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Europe/Paris")

    scheduler.add_job(
        run_scrape_and_render,
        CronTrigger(
            day_of_week="sat,sun",
            hour=f"{config.weekend_hourly_start}-{config.weekend_hourly_end}",
            minute=0,
        ),
        args=[config],
        id="weekend-hourly",
        replace_existing=True,
    )
    scheduler.add_job(
        run_scrape_and_render,
        CronTrigger(day_of_week="mon-fri", hour=config.weekday_daily_hour, minute=0),
        args=[config],
        id="weekday-daily",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Planificateur démarré (week-end %dh-%dh toutes les heures, semaine %dh/jour).",
        config.weekend_hourly_start,
        config.weekend_hourly_end,
        config.weekday_daily_hour,
    )
    return scheduler
