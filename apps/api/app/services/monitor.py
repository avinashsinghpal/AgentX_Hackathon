"""Proactive shipment monitoring.

The monitor reuses the same policy engine, action service, idempotency keys,
verification and audit trail as interactive resolution.  A delayed shipment
never implies compensation is authorized: the seller policy must configure it
and the action must be verified before it is reported as executed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.db.session import SessionLocal
from app.models.action import Action
from app.models.case import Case, CaseMessage
from app.models.order import Order
from app.models.shipment import Shipment
from app.services.actions.service import ActionService
from app.services.approvals import ApprovalService
from app.services.audit import AuditLogService
from app.services.policy.evaluator import PolicyEvaluationService
from app.services.policy.result import Decision

ACTIVE_SHIPMENT_STATUSES = ("in_transit", "delayed", "manifested", "failed_attempt")


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _days_late(now: datetime, promised: datetime) -> int:
    return max(0, int((ensure_utc(now) - ensure_utc(promised)).total_seconds() // 86400))


def run_delay_monitor_cycle(
    db: Session,
    now: datetime | None = None,
    *,
    evaluations: PolicyEvaluationService | None = None,
    actions: ActionService | None = None,
    approvals: ApprovalService | None = None,
) -> list[dict[str, Any]]:
    """Scan active shipments for overdue delivery promises.

    Returns the compensations that were executed and verified in this cycle.
    Repeated cycles cannot duplicate a credit: a succeeded wallet-credit action
    for the order is skipped, and the deterministic idempotency key prevents a
    second provider operation for the same policy version and amount.
    """
    current = now or datetime.now(UTC)
    evaluations = evaluations or PolicyEvaluationService()
    actions = actions or ActionService()
    approvals = approvals or ApprovalService(actions)

    shipments = (
        db.query(Shipment)
        .filter(
            Shipment.status.in_(ACTIVE_SHIPMENT_STATUSES),
            Shipment.promised_delivery_date.isnot(None),
        )
        .all()
    )

    remedies: list[dict[str, Any]] = []

    for shipment in shipments:
        if not shipment.promised_delivery_date:
            continue
        if current <= ensure_utc(shipment.promised_delivery_date):
            continue

        order = db.query(Order).filter(Order.id == shipment.order_id).first()
        if order is None or order.buyer_id is None:
            # Compensation cannot be attributed without a buyer on the order.
            continue

        already_credited = (
            db.query(Action)
            .filter(
                Action.order_id == order.id,
                Action.action_type == "wallet_credit",
                Action.status == "succeeded",
            )
            .first()
        )
        if already_credited is not None:
            continue

        days_late = _days_late(current, shipment.promised_delivery_date)

        evaluation = evaluations.evaluate_delay(db, order, shipment, now=current, persist=True)
        result = evaluation.result

        if result.decision is Decision.NOT_ELIGIBLE:
            logger.info(
                "Delay monitor skipped order %s: %s", order.order_number, result.reason_code
            )
            continue

        case = (
            db.query(Case)
            .filter(Case.order_id == order.id, Case.issue_category == "delay")
            .order_by(Case.created_at.asc())
            .first()
        )
        if case is None:
            case = Case(
                case_number=f"CAS-DELAY-{uuid.uuid4().hex[:6].upper()}",
                seller_id=order.seller_id,
                buyer_id=order.buyer_id,
                order_id=order.id,
                status="investigating",
                issue_category="delay",
                customer_narrative=(
                    "System detected a carrier shipment delay exceeding the promised delivery date."
                ),
                evidence_urls=[],
            )
            db.add(case)
            db.commit()
            db.refresh(case)

        if result.decision in {Decision.NEEDS_APPROVAL, Decision.MANUAL_REVIEW}:
            approvals.request_for_evaluation(
                db,
                case=case,
                evaluation=result,
                evaluation_id=evaluation.record.id if evaluation.record is not None else None,
                now=current,
            )
            logger.info(
                "Delay compensation for order %s requires seller approval: %s",
                order.order_number,
                result.reason_code,
            )
            continue

        run = actions.execute_delay_compensation(
            db,
            case=case,
            order=order,
            evaluation=result,
            extra_details={
                "days_late": days_late,
                "carrier": shipment.courier_partner,
                "tracking_number": shipment.tracking_number,
                "compensation_amount": result.eligible_amount_minor / 100.0,
            },
        )

        if not run.executed:
            AuditLogService.log_action(
                db=db,
                action="delay.compensation_failed",
                actor_role="system",
                actor_id=None,
                seller_id=order.seller_id,
                case_id=case.id,
                payload={
                    "order_number": order.order_number,
                    "action_id": run.action.id,
                    "status": run.status,
                    "failure_reason": run.reason,
                },
            )
            if not case.messages:
                db.add(
                    CaseMessage(
                        case_id=case.id,
                        sender_role="agent",
                        message=(
                            "Proactive Transit Monitor: your shipment is delayed. The delay "
                            "compensation could not be verified, so no credit was applied. "
                            "The compensation will be retried, and it cannot be duplicated."
                        ),
                        decision_badge="needs_approval",
                    )
                )
                db.commit()
            logger.warning(
                "Delay compensation for order %s was not verified: %s",
                order.order_number,
                run.reason,
            )
            continue

        compensation_major = (run.action.amount_minor or 0) / 100.0
        db.add(
            CaseMessage(
                case_id=case.id,
                sender_role="agent",
                message=(
                    f"Proactive Transit Monitor: your shipment with {shipment.courier_partner} "
                    f"(AWB: {shipment.tracking_number}) is currently {days_late} days overdue "
                    "beyond the promised delivery date. In accordance with the merchant policy, "
                    f"a wallet credit of {order.currency} {compensation_major:.2f} has been "
                    "applied to your account while we expedite courier delivery."
                ),
                tool_calls=[
                    {
                        "tool_name": "proactive_delay_monitor",
                        "tool_args": {
                            "order_number": order.order_number,
                            "awb": shipment.tracking_number,
                        },
                        "outcome": (
                            f"Shipment is {days_late} days late. Verified wallet credit of "
                            f"{order.currency} {compensation_major:.2f} "
                            f"(reference {run.action.external_reference})."
                        ),
                        "timestamp": current.isoformat(),
                    }
                ],
                decision_badge="executed",
            )
        )
        db.commit()

        AuditLogService.log_action(
            db=db,
            action="delay.proactive_compensated",
            actor_role="system",
            actor_id=None,
            seller_id=order.seller_id,
            case_id=case.id,
            payload={
                "order_number": order.order_number,
                "awb": shipment.tracking_number,
                "days_late": days_late,
                "compensation_amount": compensation_major,
                "compensation_minor": run.action.amount_minor,
                "action_id": run.action.id,
                "provider_reference": run.action.external_reference,
                "policy_version": result.policy_version,
            },
        )

        remedies.append(
            {
                "case_number": case.case_number,
                "order_number": order.order_number,
                "days_late": days_late,
                "compensation": compensation_major,
                "action_id": run.action.id,
            }
        )

    return remedies


# Background scheduler instance
scheduler = AsyncIOScheduler()


def scheduled_monitor_tick() -> None:
    """Invoked on periodic scheduler interval."""
    try:
        with SessionLocal() as db:
            remedies = run_delay_monitor_cycle(db)
            if remedies:
                logger.info(
                    "Proactive delay monitor executed %d remedies: %s", len(remedies), remedies
                )
    except Exception as exc:
        logger.error("Error during scheduled monitor tick: %s", exc)


def start_proactive_monitor() -> None:
    if not scheduler.running:
        scheduler.add_job(
            scheduled_monitor_tick,
            "interval",
            seconds=60,
            id="proactive_delay_monitor",
        )
        scheduler.start()
        logger.info(
            "APScheduler Proactive Delay Monitor started (interval=60s, configured=%dmin).",
            settings.PROACTIVE_MONITOR_INTERVAL_MINUTES,
        )


def stop_proactive_monitor() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler Proactive Delay Monitor stopped.")
