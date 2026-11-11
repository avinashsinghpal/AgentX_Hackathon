from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def build_engine(database_url: str | None = None) -> Engine:
    """Create the single SQLAlchemy engine used by the application.

    SellerResolve supports PostgreSQL only.  The engine is configured with the
    PostgreSQL connection pool and pre-ping behaviour used by the API, Alembic
    and integration tests.
    """
    url = database_url or settings.DATABASE_URL
    if not url or not url.startswith("postgresql"):
        raise ValueError(
            "SellerResolve requires a PostgreSQL DATABASE_URL. "
            "SQLite and other databases are not supported."
        )

    kwargs: dict[str, Any] = {
        "echo": settings.DB_ECHO,
        "pool_pre_ping": True,
    }
    if settings.DB_USE_NULL_POOL:
        from sqlalchemy.pool import NullPool

        kwargs["poolclass"] = NullPool
    else:
        kwargs.update(
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
        )

    return create_engine(url, **kwargs)


engine = build_engine()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
