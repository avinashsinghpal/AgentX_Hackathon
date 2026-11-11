"""Portable SQLAlchemy column types.

SellerResolve supports PostgreSQL only, so JSON columns use native JSONB.
"""

from sqlalchemy.dialects.postgresql import JSONB

JSONType = JSONB
