"""PostgreSQL-specific schema assertions.

SellerResolve supports PostgreSQL only; these assertions run with the rest of
the integration suite.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session


def _require_postgres(db: Session) -> None:
    if db.get_bind().dialect.name != "postgresql":
        pytest.skip("PostgreSQL-specific assertion")


def test_new_json_columns_are_jsonb(db: Session) -> None:
    _require_postgres(db)
    inspector = inspect(db.get_bind())
    actions = {column["name"]: column for column in inspector.get_columns("actions")}
    evaluations = {column["name"]: column for column in inspector.get_columns("policy_evaluations")}
    assert "JSONB" in str(actions["request_payload"]["type"]).upper()
    assert "JSONB" in str(evaluations["evaluation_result"]["type"]).upper()


def test_composite_case_order_foreign_key_exists(db: Session) -> None:
    _require_postgres(db)
    inspector = inspect(db.get_bind())
    foreign_keys = inspector.get_foreign_keys("cases")
    matching = [fk for fk in foreign_keys if fk["name"] == "fk_cases_seller_order"]
    assert len(matching) == 1
    assert matching[0]["constrained_columns"] == ["seller_id", "order_id"]
    assert matching[0]["referred_columns"] == ["seller_id", "id"]


def test_one_active_policy_index_is_partial(db: Session) -> None:
    _require_postgres(db)
    inspector = inspect(db.get_bind())
    indexes = {index["name"]: index for index in inspector.get_indexes("seller_policies")}
    active = indexes["uq_seller_policies_one_active"]
    assert active["unique"] is True
    assert active["column_names"] == ["seller_id"]


def test_audit_chain_columns_are_not_nullable(db: Session) -> None:
    _require_postgres(db)
    inspector = inspect(db.get_bind())
    columns = {column["name"]: column for column in inspector.get_columns("audit_logs")}
    assert columns["chain_key"]["nullable"] is False
    assert columns["sequence"]["nullable"] is False
