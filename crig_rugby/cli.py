"""Interface en ligne de commande.

Commandes :
  scrape    scrute les 4 compétitions une fois et met à jour le cache, sans rendu
  generate  régénère les pages HTML depuis le cache, sans requête réseau
  serve     démarre uniquement le serveur web (pas de scraping automatique)
  run       scrape+génère immédiatement, puis démarre le planificateur + le serveur
            (commande à utiliser en production, ex. via systemd)
"""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import time
from pathlib import Path

from . import cache, pipeline, render
from .config import BASE_DIR, load_config
from .scheduler import run_scrape_and_render, start_scheduler
from .server import run_server


def _setup_logging() -> None:
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        log_dir / "crig-rugby.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addHandler(console)


def cmd_scrape(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    pipeline.scrape_all(config)


def cmd_generate(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    data = [
        cache.load(config.cache_dir, comp.slug)
        for comp in config.competitions
    ]
    missing = [comp.slug for comp, d in zip(config.competitions, data) if d is None]
    if missing:
        raise SystemExit(
            f"Pas de cache disponible pour : {', '.join(missing)}. "
            "Lancez d'abord 'scrape'."
        )
    render.render_all(config, data)


def cmd_serve(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    run_server(config)


def cmd_run(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    run_scrape_and_render(config)
    start_scheduler(config)
    run_server(config)  # bloquant : sert tant que le processus tourne


def main(argv: list[str] | None = None) -> None:
    _setup_logging()

    parser = argparse.ArgumentParser(prog="crig-rugby", description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=None, help="Chemin vers config.yaml (défaut: ./config.yaml)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scrape").set_defaults(func=cmd_scrape)
    subparsers.add_parser("generate").set_defaults(func=cmd_generate)
    subparsers.add_parser("serve").set_defaults(func=cmd_serve)
    subparsers.add_parser("run").set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
