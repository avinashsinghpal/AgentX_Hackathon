import sys
from logging.config import fileConfig
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import engine_from_config, pool

from alembic import context

# Ensure app root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

import app.models  # noqa: F401 - Register all models with Base.metadata
from app.core.config import settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def compare_types(
    context: object,
    inspected_column: sa.Column[object],
    metadata_column: sa.Column[object],
    inspected_type: sa.types.TypeEngine[object],
    metadata_type: sa.types.TypeEngine[object],
) -> bool | None:
    """Treat JSON and PostgreSQL JSONB as the same logical column type.

    ``app.db.types.JSONType`` selects JSONB on PostgreSQL, while historical
    columns (and reflected JSON) stay in PostgreSQL ``json``.  Both map to the
    same Python ``dict``/``list`` contract, so a type-only difference must not
    produce a spurious migration.
    """
    if isinstance(inspected_type, sa.JSON) and isinstance(metadata_type, sa.JSON):
        return False
    return None


def run_migrations_offline() -> None:
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        compare_type=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=compare_types,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
