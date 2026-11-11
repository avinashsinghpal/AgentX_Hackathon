from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.action import Action


def build_idempotency_key(
    action_type: str,
    seller_id: str,
    *,
    case_id: str | None = None,
    order_id: str | None = None,
    amount_minor: int | None = None,
    policy_version: int | None = None,
) -> str:
    """Deterministic key scoped to the action and the business entity.

    A retry of the same business operation reproduces the same key, so the
    unique constraint rejects a duplicate instead of paying twice.
    """
    parts = [
        action_type,
        seller_id,
        case_id or "-",
        order_id or "-",
        str(amount_minor) if amount_minor is not None else "-",
        f"v{policy_version}" if policy_version is not None else "-",
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"{action_type}:{digest}"


def get_action_by_key(db: Session, seller_id: str, idempotency_key: str) -> Action | None:
    return (
        db.query(Action)
        .filter(Action.seller_id == seller_id, Action.idempotency_key == idempotency_key)
        .first()
    )


def get_or_create_action(
    db: Session,
    *,
    seller_id: str,
    action_type: str,
    idempotency_key: str,
    case_id: str | None,
    order_id: str | None,
    amount_minor: int | None,
    currency: str | None,
    request_payload: dict[str, Any] | None = None,
    initiated_by: str | None = None,
    approval_id: str | None = None,
) -> tuple[Action, bool]:
    """Return (action, created).  Concurrency-safe through the unique constraint."""
    existing = get_action_by_key(db, seller_id, idempotency_key)
    if existing is not None:
        return existing, False

    action = Action(
        seller_id=seller_id,
        action_type=action_type,
        idempotency_key=idempotency_key,
        case_id=case_id,
        order_id=order_id,
        amount_minor=amount_minor,
        currency=currency,
        status="pending",
        request_payload=request_payload or {},
        response_payload={},
        initiated_by=initiated_by,
        approval_id=approval_id,
    )
    db.add(action)
    try:
        db.commit()
    except IntegrityError:
        # Lost the race: another request created the same action first.
        db.rollback()
        existing = get_action_by_key(db, seller_id, idempotency_key)
        if existing is None:
            raise
        return existing, False

    db.refresh(action)
    return action, True
