import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentBuyer, DbSession
from app.models.case import Case, CaseMessage
from app.models.order import Order
from app.models.seller import Seller
from app.models.shipment import Shipment
from app.schemas.buyer import (
    BuyerOrderSummary,
    CaseCreateRequest,
    CaseDetailResponse,
    CaseMessageItem,
    CaseSummaryItem,
)
from app.services.audit import AuditLogService

router = APIRouter(prefix="/cases", tags=["Buyer Cases"])


@router.post("", response_model=CaseSummaryItem)
def create_case(
    data: CaseCreateRequest,
    buyer: CurrentBuyer,
    db: DbSession,
) -> CaseSummaryItem:
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    # Scoping check: Ensure order belongs to this buyer
    if order.buyer_id and order.buyer_id != buyer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to file a complaint for this order.",
        )

    if not order.buyer_id:
        order.buyer_id = buyer.id

    # Check for existing open case on this order
    existing_case = (
        db.query(Case)
        .filter(
            Case.order_id == order.id,
            Case.status.in_(["open", "investigating", "pending_approval"]),
        )
        .first()
    )
    if existing_case:
        seller = db.query(Seller).filter(Seller.id == existing_case.seller_id).first()
        return CaseSummaryItem(
            id=existing_case.id,
            case_number=existing_case.case_number,
            order_number=order.order_number,
            seller_id=existing_case.seller_id,
            seller_name=seller.store_name if seller else "Merchant",
            issue_category=existing_case.issue_category,
            status=existing_case.status,
            decision=existing_case.decision,
            created_at=existing_case.created_at.isoformat(),
            resolved_at=existing_case.resolved_at.isoformat()
            if existing_case.resolved_at
            else None,
        )

    now = datetime.now(UTC)
    case_number = f"CAS-{uuid.uuid4().hex[:8].upper()}"

    new_case = Case(
        case_number=case_number,
        seller_id=order.seller_id,
        buyer_id=buyer.id,
        order_id=order.id,
        status="investigating",
        issue_category=data.issue_category,
        customer_narrative=data.customer_narrative,
        evidence_urls=data.evidence_urls,
    )
    db.add(new_case)
    db.flush()

    # Initial buyer message
    initial_buyer_msg = CaseMessage(
        case_id=new_case.id,
        sender_role="buyer",
        message=data.customer_narrative,
    )
    db.add(initial_buyer_msg)

    # Initial Agent Acknowledgment message
    initial_agent_msg = CaseMessage(
        case_id=new_case.id,
        sender_role="agent",
        message=(
            f"Hello. I am the autonomous resolution agent for {order.seller.store_name if order.seller else 'this merchant'}. "
            f"I have received your inquiry regarding order {order.order_number} and am cross-referencing "
            f"courier records and merchant return policies now."
        ),
        tool_calls=[
            {
                "tool_name": "verify_order_record",
                "tool_args": {"order_number": order.order_number},
                "outcome": "Order record retrieved. Payment status verified.",
                "timestamp": now.isoformat(),
            }
        ],
    )
    db.add(initial_agent_msg)

    db.commit()
    db.refresh(new_case)

    # Log cryptographic audit trail
    AuditLogService.log_action(
        db=db,
        action="case.created",
        actor_role="buyer",
        actor_id=buyer.user_id,
        seller_id=order.seller_id,
        case_id=new_case.id,
        payload={
            "case_number": new_case.case_number,
            "order_number": order.order_number,
            "category": data.issue_category,
            "evidence_count": len(data.evidence_urls),
        },
    )

    seller = db.query(Seller).filter(Seller.id == new_case.seller_id).first()

    return CaseSummaryItem(
        id=new_case.id,
        case_number=new_case.case_number,
        order_number=order.order_number,
        seller_id=new_case.seller_id,
        seller_name=seller.store_name if seller else "Merchant",
        issue_category=new_case.issue_category,
        status=new_case.status,
        decision=new_case.decision,
        created_at=new_case.created_at.isoformat(),
        resolved_at=new_case.resolved_at.isoformat() if new_case.resolved_at else None,
    )


@router.get("", response_model=list[CaseSummaryItem])
def get_buyer_cases(
    buyer: CurrentBuyer,
    db: DbSession,
) -> list[CaseSummaryItem]:
    cases = db.query(Case).filter(Case.buyer_id == buyer.id).order_by(Case.created_at.desc()).all()

    results: list[CaseSummaryItem] = []
    for c in cases:
        seller = db.query(Seller).filter(Seller.id == c.seller_id).first()
        order = db.query(Order).filter(Order.id == c.order_id).first()

        results.append(
            CaseSummaryItem(
                id=c.id,
                case_number=c.case_number,
                order_number=order.order_number if order else "Unknown",
                seller_id=c.seller_id,
                seller_name=seller.store_name if seller else "Merchant",
                issue_category=c.issue_category,
                status=c.status,
                decision=c.decision,
                created_at=c.created_at.isoformat(),
                resolved_at=c.resolved_at.isoformat() if c.resolved_at else None,
            )
        )

    return results


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case_detail(
    case_id: str,
    buyer: CurrentBuyer,
    db: DbSession,
) -> CaseDetailResponse:
    c = db.query(Case).filter(Case.id == case_id, Case.buyer_id == buyer.id).first()
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or you do not have permission to view it.",
        )

    seller = db.query(Seller).filter(Seller.id == c.seller_id).first()
    order = db.query(Order).filter(Order.id == c.order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated order not found.",
        )

    shipment = (
        db.query(Shipment)
        .filter(Shipment.order_id == order.id)
        .order_by(Shipment.created_at.desc())
        .first()
    )

    items_list: list[dict[str, Any]] = order.items if isinstance(order.items, list) else []

    order_summary = BuyerOrderSummary(
        id=order.id,
        order_number=order.order_number,
        seller_id=order.seller_id,
        seller_name=seller.store_name if seller else "Merchant",
        order_date=order.order_date.isoformat(),
        total_amount=order.total_amount / 100.0,
        currency=order.currency,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        order_status=order.order_status,
        items_count=len(items_list),
        items=items_list,
        tracking_number=shipment.tracking_number if shipment else None,
        carrier=shipment.courier_partner if shipment else None,
        delivery_date=shipment.actual_delivery_date.isoformat()
        if shipment and shipment.actual_delivery_date
        else None,
        eligible_for_complaint=False,
    )

    case_summary = CaseSummaryItem(
        id=c.id,
        case_number=c.case_number,
        order_number=order.order_number,
        seller_id=c.seller_id,
        seller_name=seller.store_name if seller else "Merchant",
        issue_category=c.issue_category,
        status=c.status,
        decision=c.decision,
        created_at=c.created_at.isoformat(),
        resolved_at=c.resolved_at.isoformat() if c.resolved_at else None,
    )

    messages = (
        db.query(CaseMessage)
        .filter(CaseMessage.case_id == c.id)
        .order_by(CaseMessage.created_at.asc())
        .all()
    )

    message_items = [
        CaseMessageItem(
            id=m.id,
            sender_role=m.sender_role,
            message=m.message,
            tool_calls=m.tool_calls,
            decision_badge=m.decision_badge,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]

    return CaseDetailResponse(
        case=case_summary,
        order=order_summary,
        customer_narrative=c.customer_narrative,
        evidence_urls=c.evidence_urls,
        messages=message_items,
        outcome_details=c.outcome_details,
    )
