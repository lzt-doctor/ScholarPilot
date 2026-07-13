"""Run Alembic while preserving databases created by the original MVP."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database import engine


def run_migrations() -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    tables = set(inspect(engine).get_table_names())
    if "users" in tables and "alembic_version" not in tables:
        command.stamp(config, "0001_initial")
    command.upgrade(config, "head")


if __name__ == "__main__":
    run_migrations()
