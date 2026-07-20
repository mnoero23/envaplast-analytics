from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from src.config import settings


def build_engine(url: str | None = None) -> Engine:
    database_url = url or settings.database_url
    if database_url.startswith("sqlite:///"):
        raw_path = database_url.removeprefix("sqlite:///")
        if raw_path != ":memory:":
            Path(raw_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url, future=True, pool_pre_ping=True)
    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = build_engine()


@contextmanager
def session_scope(target_engine: Engine | None = None):
    with Session(target_engine or engine) as session:
        with session.begin():
            yield session
