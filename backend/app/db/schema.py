"""Schema application via Alembic."""
from __future__ import annotations

import logging
import os

from alembic import command
from alembic.config import Config

logger = logging.getLogger("backend.schema")


def _alembic_config(database_url: str) -> Config:
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ini_path = os.path.join(here, "alembic.ini")
    cfg = Config(ini_path)
    cfg.set_main_option("script_location", os.path.join(here, "app", "db", "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def apply_schema(database_url: str) -> None:
    """Upgrade the database to the latest revision."""
    logger.info("Applying database migrations (upgrade head)")
    cfg = _alembic_config(database_url)
    command.upgrade(cfg, "head")
    logger.info("Database schema is up to date")
