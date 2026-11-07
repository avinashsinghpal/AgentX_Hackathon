import uuid
from datetime import UTC, datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.session import SessionLocal
from app.models.case import Case, CaseMessage
from app.models.order import Order
from app.models.seller import SellerPolicy
from app.models.shipment import Shipment
from app.services.audit import AuditLogService


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def run_delay_monitor_cycle(db: Session) -> list[dict[str, Any]]:
    """Scans in-transit shipments for overdue delivery dates and executes proactive remedies."""
    now = datetime.now(UTC)
    delayed_shipments = (
        db.query(Shipment)
        .filter(
            Shipment.status.in_(["in_transit", "delayed", "manifested"]),
            Shipment.promised_delivery_date.isnot(None),
        )
        .all()
    )

    remedies_executed: list[dict[str, Any]] = []

    for shipment in delayed_shipments:
        if not shipment.promised_delivery_date:
            continue

        pdd = ensure_utc(shipment.promised_delivery_date)
        if now <= pdd:
            continue

        days_late = (now - pdd).days
        if days_late < 1:
            continue

        order = db.query(Order).filter(Order.id == shipment.order_id).first()
        if not order:
            continue

        # Check if already compensated for delay
        existing_delay_case = (
            db.query(Case)
            .filter(
                Case.order_id == order.id,
                Case.issue_category == "delay",
            )
            .first()
        )
        if existing_delay_case:
            continue

        # Fetch seller's active policy
        policy = (
            db.query(SellerPolicy)
            .filter(SellerPolicy.seller_id == order.seller_id, SellerPolicy.is_active.is_(True))
            .first()
        )
        rules = policy.parsed_rules if (policy and policy.parsed_rules) else {}
        delays_rule = rules.get("delays", {})

        delay_threshold_days = delays_rule.get("delay_threshold_days", 3)
        comp_per_day = float(delays_rule.get("compensation_per_day_late", 50.0))
        max_comp = float(delays_rule.get("max_delay_compensation", 250.0))

        if days_late >= delay_threshold_days:
            # Mark shipment status as delayed
            shipment.status = "delayed"

            compensation_amount = min(days_late * comp_per_day, max_comp)
            case_number = f"CAS-DELAY-{uuid.uuid4().hex[:6].upper()}"

            # Ensure order has a buyer_id, or find or fallback
            buyer_id = order.buyer_id
            if not buyer_id:
                # If buyer not claimed, skip or attribute to seller
                continue

            # Create proactive resolution case
            proactive_case = Case(
                case_number=case_number,
                seller_id=order.seller_id,
                buyer_id=buyer_id,
                order_id=order.id,
                status="resolved",
                issue_category="delay",
                customer_narrative="System detected carrier shipment delay exceeding estimated delivery date.",
                evidence_urls=[],
                decision="executed",
                resolution_type="delay_compensation",
                outcome_details={
                    "days_late": days_late,
                    "compensation_amount": compensation_amount,
                    "carrier": shipment.courier_partner,
                    "tracking_number": shipment.tracking_number,
                },
                resolved_at=now,
            )
            db.add(proactive_case)
            db.flush()

            # Add explanatory agent message turn
            explanation = (
                f"Proactive Transit Monitor: Your shipment with {shipment.courier_partner} (AWB: {shipment.tracking_number}) "
                f"is currently {days_late} days overdue beyond the promised delivery date. "
                f"In accordance with our customer SLA policy, an automatic wallet credit of INR {compensation_amount:.2f} "
                "has been applied to your account while we expedite courier delivery."
            )

            msg = CaseMessage(
                case_id=proactive_case.id,
                sender_role="agent",
                message=explanation,
                tool_calls=[
                    {
                        "tool_name": "proactive_delay_monitor",
                        "tool_args": {
                            "order_number": order.order_number,
                            "awb": shipment.tracking_number,
                        },
                        "outcome": f"Shipment is {days_late} days late. Disbursed INR {compensation_amount:.2f} credit.",
                        "timestamp": now.isoformat(),
                    }
                ],
                decision_badge="executed",
            )
            db.add(msg)
            db.commit()

            AuditLogService.log_action(
                db=db,
                action="delay.proactive_compensated",
                actor_role="system",
                actor_id=None,
                seller_id=order.seller_id,
                case_id=proactive_case.id,
                payload={
                    "order_number": order.order_number,
                    "awb": shipment.tracking_number,
                    "days_late": days_late,
                    "compensation_amount": compensation_amount,
                },
            )

            remedies_executed.append(
                {
                    "case_number": case_number,
                    "order_number": order.order_number,
                    "days_late": days_late,
                    "compensation": compensation_amount,
                }
            )

    return remedies_executed


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
            scheduled_monitor_tick, "interval", seconds=60, id="proactive_delay_monitor"
        )
        scheduler.start()
        logger.info("APScheduler Proactive Delay Monitor started (interval=60s).")


def stop_proactive_monitor() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler Proactive Delay Monitor stopped.")
