from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import settings


def is_sqlite_url(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def build_engine(database_url: str | None = None) -> Engine:
    """Create the single SQLAlchemy engine used by the application.

    Engine creation is centralized so tests, the API and scripts share the same
    pooling and SQLite pragma behaviour.
    """
    url = database_url or settings.DATABASE_URL
    kwargs: dict[str, Any] = {"echo": settings.DB_ECHO, "pool_pre_ping": True}

    connect_args: dict[str, Any] = {}
    if is_sqlite_url(url):
        connect_args = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
    else:
        if settings.DB_USE_NULL_POOL:
            kwargs["poolclass"] = NullPool
        else:
            kwargs.update(
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=settings.DB_POOL_RECYCLE,
            )

    engine = create_engine(url, connect_args=connect_args, **kwargs)

    if is_sqlite_url(url):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = build_engine()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
