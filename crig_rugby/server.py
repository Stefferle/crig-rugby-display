"""Petit serveur Flask qui sert les pages générées et les fichiers statiques."""

from __future__ import annotations

from flask import Flask, send_from_directory

from .config import Config


def create_app(config: Config) -> Flask:
    app = Flask(__name__, static_folder=str(config.output_dir), static_url_path="")

    @app.route("/")
    def index():
        return send_from_directory(str(config.output_dir), "index.html")

    @app.route("/static/<path:filename>")
    def project_static(filename: str):
        return send_from_directory(str(config.static_dir), filename)

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    return app


def run_server(config: Config) -> None:
    app = create_app(config)
    app.run(host="0.0.0.0", port=config.port)
