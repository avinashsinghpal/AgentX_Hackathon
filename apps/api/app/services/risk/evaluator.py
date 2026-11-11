"""Loads trusted records, evaluates risk and keeps it separate from policy."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.buyer import Buyer
from app.models.case import Case
from app.models.file_upload import FileUpload
from app.models.order import Order
from app.services.policy.evaluator import (
    buyer_refund_count,
    load_policy,
)
from app.services.risk.engine import RiskEngine
from app.services.risk.result import RiskResult
from app.services.risk.schemas import RiskEvaluationInput


def _sha256_file(path: str) -> str | None:
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def current_evidence_hashes(db: Session, case: Case) -> tuple[str, ...]:
    rows = db.query(FileUpload).filter(FileUpload.case_id == case.id).all()
    hashes: list[str] = []
    for row in rows:
        digest = _sha256_file(row.storage_path)
        if digest is not None:
            hashes.append(digest)
    return tuple(hashes)


def previous_evidence_hashes(db: Session, case: Case) -> tuple[str, ...]:
    rows = (
        db.query(FileUpload)
        .join(Case, FileUpload.case_id == Case.id)
        .filter(Case.buyer_id == case.buyer_id, Case.id != case.id)
        .all()
    )
    hashes: list[str] = []
    for row in rows:
        digest = _sha256_file(row.storage_path)
        if digest is not None:
            hashes.append(digest)
    return tuple(hashes)


class RiskEvaluationService:
    """Builds trusted risk inputs from the database and evaluates them."""

    def __init__(self, engine: RiskEngine | None = None) -> None:
        self.engine = engine or RiskEngine()

    def evaluate_case(
        self,
        db: Session,
        case: Case,
        *,
        now: datetime | None = None,
        persist: bool = False,
    ) -> RiskResult:
        evaluated_at = now or datetime.now(UTC)
        order = db.query(Order).filter(Order.id == case.order_id).first()
        if order is None:
            raise ValueError(f"Order {case.order_id} not found for case {case.id}")

        buyer = db.query(Buyer).filter(Buyer.id == case.buyer_id).first()
        _policy_row, policy, _policy_invalid = load_policy(db, case.seller_id)

        threshold = None
        if policy is not None:
            threshold = policy.fraud_checks.max_refunds_per_buyer_per_30_days

        history_count = (
            db.query(Order).filter(Order.buyer_id == case.buyer_id).count()
            if case.buyer_id
            else 0
        )

        inputs = RiskEvaluationInput(
            seller_id=case.seller_id,
            buyer_id=case.buyer_id,
            case_id=case.id,
            order_id=case.order_id,
            max_refunds_per_buyer_per_30_days=threshold,
            buyer_refund_count_30d=buyer_refund_count(db, order.buyer_id, evaluated_at),
            current_evidence_hashes=current_evidence_hashes(db, case),
            previous_evidence_hashes=previous_evidence_hashes(db, case),
            order_shipping_address=order.shipping_address,
            buyer_default_shipping_address=(
                buyer.default_shipping_address if buyer is not None else None
            ),
            customer_history_count=history_count,
            history_available=buyer is not None,
        )

        return self.engine.evaluate(inputs)

    def evaluate_order(
        self,
        db: Session,
        *,
        order: Order,
        seller_id: str,
        buyer_id: str | None,
        case_id: str | None = None,
        now: datetime | None = None,
    ) -> RiskResult:
        evaluated_at = now or datetime.now(UTC)
        buyer = db.query(Buyer).filter(Buyer.id == buyer_id).first() if buyer_id else None
        _policy_row, policy, _policy_invalid = load_policy(db, seller_id)

        threshold = None
        if policy is not None:
            threshold = policy.fraud_checks.max_refunds_per_buyer_per_30_days

        history_count = (
            db.query(Order).filter(Order.buyer_id == buyer_id).count() if buyer_id else 0
        )

        inputs = RiskEvaluationInput(
            seller_id=seller_id,
            buyer_id=buyer_id,
            case_id=case_id,
            order_id=order.id,
            max_refunds_per_buyer_per_30_days=threshold,
            buyer_refund_count_30d=buyer_refund_count(db, buyer_id, evaluated_at),
            order_shipping_address=order.shipping_address,
            buyer_default_shipping_address=(
                buyer.default_shipping_address if buyer is not None else None
            ),
            customer_history_count=history_count,
            history_available=buyer is not None,
        )
        return self.engine.evaluate(inputs)