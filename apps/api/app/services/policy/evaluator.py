"""Loads authoritative records, runs the engine and persists the evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.action import Action
from app.models.case import Case
from app.models.file_upload import FileUpload
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.policy_evaluation import PolicyEvaluation
from app.models.seller import Seller, SellerPolicy
from app.models.shipment import Shipment
from app.schemas.policy import PolicySchema, normalize_parsed_rules
from app.services.orders import normalize_legacy_item
from app.services.policy.engine import PolicyEngine
from app.services.policy.result import EvaluationResult
from app.services.policy.schemas import (
    CaseInput,
    ItemInput,
    OrderInput,
    PolicyEvaluationInput,
    ShipmentInput,
)

REFUND_ACTION_TYPES = ("refund", "wallet_credit")


@dataclass
class CaseEvaluation:
    result: EvaluationResult
    record: PolicyEvaluation


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def load_policy(
    db: Session, seller_id: str
) -> tuple[SellerPolicy | None, PolicySchema | None, bool]:
    """Return (row, validated policy, is_invalid)."""
    row = (
        db.query(SellerPolicy)
        .filter(SellerPolicy.seller_id == seller_id, SellerPolicy.is_active.is_(True))
        .order_by(SellerPolicy.version.desc())
        .first()
    )
    if row is None:
        return None, None, False

    policy = normalize_parsed_rules(row.parsed_rules)
    if policy is None:
        from app.schemas.policy import parse_and_validate_yaml

        valid, parsed, _ = parse_and_validate_yaml(row.policy_yaml or "")
        if valid and parsed is not None:
            return row, parsed, False
        return row, None, True
    return row, policy, False


def latest_shipment(db: Session, order_id: str) -> Shipment | None:
    return (
        db.query(Shipment)
        .filter(Shipment.order_id == order_id)
        .order_by(Shipment.created_at.desc())
        .first()
    )


def shipment_snapshot(shipment: Shipment | None, db: Session) -> ShipmentInput | None:
    if shipment is None:
        return None
    from app.models.tracking_event import TrackingEvent

    events = (
        db.query(TrackingEvent)
        .filter(TrackingEvent.shipment_id == shipment.id)
        .order_by(TrackingEvent.event_timestamp.asc())
        .all()
    )
    latest_event_at = _utc(events[-1].event_timestamp) if events else None
    return ShipmentInput(
        id=shipment.id,
        status=shipment.status,
        promised_delivery_date=_utc(shipment.promised_delivery_date),
        actual_delivery_date=_utc(shipment.actual_delivery_date),
        tracking_event_count=len(events),
        latest_event_at=latest_event_at,
        courier_partner=shipment.courier_partner,
        tracking_number=shipment.tracking_number,
    )


def item_snapshots(db: Session, order: Order) -> tuple[ItemInput, ...]:
    rows = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order.id)
        .order_by(OrderItem.created_at.asc())
        .all()
    )
    if rows:
        return tuple(
            ItemInput(
                reference_id=row.id,
                title=row.title,
                quantity=row.quantity,
                unit_price_minor=row.unit_price_minor,
                returnable=row.returnable,
                category=row.category,
                sku=row.sku,
            )
            for row in rows
        )

    legacy = order.items if isinstance(order.items, list) else []
    snapshots = []
    for index, item in enumerate(legacy):
        normalized = normalize_legacy_item(item, index)
        snapshots.append(
            ItemInput(
                reference_id=str(normalized["reference_id"]),
                title=str(normalized["title"]),
                quantity=int(normalized["quantity"]),
                unit_price_minor=int(normalized["unit_price_minor"]),
                returnable=bool(normalized["returnable"]),
                category=normalized["category"],
                sku=normalized["sku"],
            )
        )
    return tuple(snapshots)


def evidence_references(db: Session, case: Case) -> tuple[str, ...]:
    """Union of the authoritative file links and the legacy JSON projection."""
    ordered: list[str] = []
    seen: set[str] = set()

    rows = db.query(FileUpload).filter(FileUpload.case_id == case.id).all()
    for row in rows:
        if row.id not in seen:
            seen.add(row.id)
            ordered.append(row.id)

    legacy = case.evidence_urls if isinstance(case.evidence_urls, list) else []
    for reference in legacy:
        if reference and reference not in seen:
            seen.add(reference)
            ordered.append(reference)

    return tuple(ordered)


def buyer_refund_count(db: Session, buyer_id: str | None, now: datetime) -> int:
    if not buyer_id:
        return 0
    since = now - timedelta(days=30)
    return (
        db.query(func.count(Action.id))
        .join(Order, Action.order_id == Order.id)
        .filter(
            Order.buyer_id == buyer_id,
            Action.status == "succeeded",
            Action.action_type.in_(REFUND_ACTION_TYPES),
            Action.created_at >= since,
        )
        .scalar()
        or 0
    )


def duplicate_claim_exists(db: Session, case: Case) -> bool:
    query = db.query(Case).filter(
        Case.order_id == case.order_id,
        Case.issue_category == case.issue_category,
        Case.status.in_(["open", "investigating", "pending_approval"]),
    )
    if case.id:
        query = query.filter(Case.id != case.id)
    return db.query(query.exists()).scalar() is True


class PolicyEvaluationService:
    """Builds trusted inputs from the database and persists each evaluation."""

    def __init__(self, engine: PolicyEngine | None = None) -> None:
        self.engine = engine or PolicyEngine()

    def evaluate_case(
        self,
        db: Session,
        case: Case,
        *,
        now: datetime | None = None,
        persist: bool = True,
    ) -> CaseEvaluation:
        evaluated_at = now or datetime.now(UTC)
        order = db.query(Order).filter(Order.id == case.order_id).first()
        if order is None:
            raise ValueError(f"Order {case.order_id} not found for case {case.id}")

        seller = db.query(Seller).filter(Seller.id == case.seller_id).first()
        policy_row, policy, policy_invalid = load_policy(db, case.seller_id)
        shipment = latest_shipment(db, order.id)

        inputs = PolicyEvaluationInput(
            case=CaseInput(
                id=case.id,
                case_number=case.case_number,
                seller_id=case.seller_id,
                buyer_id=case.buyer_id,
                order_id=case.order_id,
                issue_category=case.issue_category,
            ),
            order=OrderInput(
                id=order.id,
                seller_id=order.seller_id,
                buyer_id=order.buyer_id,
                order_number=order.order_number,
                currency=order.currency,
                total_amount_minor=order.total_amount,
                payment_method=order.payment_method,
                payment_status=order.payment_status,
                order_status=order.order_status,
                original_delivery_date=_utc(order.order_date),
            ),
            seller_status=seller.status if seller else "unknown",
            policy=policy,
            policy_id=policy_row.id if policy_row else None,
            policy_version=policy_row.version if policy_row else None,
            policy_invalid=policy_invalid,
            shipment=shipment_snapshot(shipment, db),
            items=item_snapshots(db, order),
            evidence_count=len(evidence_references(db, case)),
            evidence_reference_ids=evidence_references(db, case),
            buyer_refund_count_30d=buyer_refund_count(db, order.buyer_id, evaluated_at),
            duplicate_claim_exists=duplicate_claim_exists(db, case),
            now=evaluated_at,
            evaluator_version=self.engine.EVALUATOR_VERSION,
        )

        result = self.engine.evaluate(inputs)
        record = self._persist(db, result, policy_row, persist=persist)
        return CaseEvaluation(result=result, record=record)

    def evaluate_order_category(
        self,
        db: Session,
        *,
        order: Order,
        seller_id: str,
        buyer_id: str | None,
        issue_category: str,
        evidence_count: int = 0,
        evidence_reference_ids: tuple[str, ...] = (),
        duplicate_claim_exists: bool = False,
        now: datetime | None = None,
        persist: bool = False,
    ) -> CaseEvaluation:
        """Evaluate an order without a persisted case (used by investigation tools)."""
        evaluated_at = now or datetime.now(UTC)
        seller = db.query(Seller).filter(Seller.id == seller_id).first()
        policy_row, policy, policy_invalid = load_policy(db, seller_id)
        shipment = latest_shipment(db, order.id)

        inputs = PolicyEvaluationInput(
            case=CaseInput(
                seller_id=seller_id,
                buyer_id=buyer_id or "",
                order_id=order.id,
                issue_category=issue_category,
            ),
            order=OrderInput(
                id=order.id,
                seller_id=order.seller_id,
                buyer_id=order.buyer_id,
                order_number=order.order_number,
                currency=order.currency,
                total_amount_minor=order.total_amount,
                payment_method=order.payment_method,
                payment_status=order.payment_status,
                order_status=order.order_status,
                original_delivery_date=_utc(order.order_date),
            ),
            seller_status=seller.status if seller else "unknown",
            policy=policy,
            policy_id=policy_row.id if policy_row else None,
            policy_version=policy_row.version if policy_row else None,
            policy_invalid=policy_invalid,
            shipment=shipment_snapshot(shipment, db),
            items=item_snapshots(db, order),
            evidence_count=evidence_count,
            evidence_reference_ids=evidence_reference_ids,
            buyer_refund_count_30d=buyer_refund_count(db, order.buyer_id, evaluated_at),
            duplicate_claim_exists=duplicate_claim_exists,
            now=evaluated_at,
            evaluator_version=self.engine.EVALUATOR_VERSION,
        )

        result = self.engine.evaluate(inputs)
        record = self._persist(db, result, policy_row, persist=persist)
        return CaseEvaluation(result=result, record=record)

    def evaluate_delay(
        self,
        db: Session,
        order: Order,
        shipment: Shipment | None,
        *,
        now: datetime | None = None,
        persist: bool = True,
    ) -> CaseEvaluation:
        """Proactive delay evaluation, scoped to an order rather than a case."""
        evaluated_at = now or datetime.now(UTC)
        seller = db.query(Seller).filter(Seller.id == order.seller_id).first()
        policy_row, policy, policy_invalid = load_policy(db, order.seller_id)

        inputs = PolicyEvaluationInput(
            case=CaseInput(
                seller_id=order.seller_id,
                buyer_id=order.buyer_id or "",
                order_id=order.id,
                issue_category="delay",
            ),
            order=OrderInput(
                id=order.id,
                seller_id=order.seller_id,
                buyer_id=order.buyer_id,
                order_number=order.order_number,
                currency=order.currency,
                total_amount_minor=order.total_amount,
                payment_method=order.payment_method,
                payment_status=order.payment_status,
                order_status=order.order_status,
                original_delivery_date=_utc(order.order_date),
            ),
            seller_status=seller.status if seller else "unknown",
            policy=policy,
            policy_id=policy_row.id if policy_row else None,
            policy_version=policy_row.version if policy_row else None,
            policy_invalid=policy_invalid,
            shipment=shipment_snapshot(shipment, db),
            items=item_snapshots(db, order),
            evidence_count=0,
            buyer_refund_count_30d=buyer_refund_count(db, order.buyer_id, evaluated_at),
            duplicate_claim_exists=False,
            now=evaluated_at,
            evaluator_version=self.engine.EVALUATOR_VERSION,
        )

        result = self.engine.evaluate(inputs)
        record = self._persist(db, result, policy_row, persist=persist)
        return CaseEvaluation(result=result, record=record)

    def _persist(
        self,
        db: Session,
        result: EvaluationResult,
        policy_row: SellerPolicy | None,
        *,
        persist: bool,
    ) -> PolicyEvaluation:
        record = PolicyEvaluation(
            case_id=result.case_id,
            seller_id=result.seller_id,
            order_id=result.order_id,
            seller_policy_id=policy_row.id if policy_row else None,
            policy_version=result.policy_version,
            decision=result.decision.value,
            reason_code=result.reason_code,
            explanation=result.reason,
            evaluation_result=result.model_dump(mode="json"),
            evaluator_version=result.evaluator_version,
            evaluated_at=result.evaluated_at,
        )
        if persist:
            db.add(record)
            db.commit()
            db.refresh(record)
        return record
