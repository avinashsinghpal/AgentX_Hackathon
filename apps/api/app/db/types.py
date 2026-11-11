"""Portable SQLAlchemy column types.

The application must behave identically on PostgreSQL (the development and
production database) and on SQLite (in-memory unit tests only).  Models use
``JSONType`` instead of importing ``sqlalchemy.dialects.sqlite.JSON`` so that
PostgreSQL gets native ``JSONB`` while SQLite keeps a safe ``JSON`` fallback.
"""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

# JSONB on PostgreSQL, plain JSON everywhere else.
JSONType = JSON().with_variant(JSONB(), "postgresql")
