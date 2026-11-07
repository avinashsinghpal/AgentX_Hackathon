from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentSeller, DbSession
from app.models.case import ApprovalRequest, Case
from app.models.order import Order

router = APIRouter(prefix="/metrics", tags=["Seller Metrics"])


@router.get("")
def get_seller_metrics(
    seller: CurrentSeller,
    db: DbSession,
) -> dict[str, Any]:
    total_orders = db.query(Order).filter(Order.seller_id == seller.id).count()
    open_cases = (
        db.query(Case)
        .filter(
            Case.seller_id == seller.id,
            Case.status.in_(["open", "investigating"]),
        )
        .count()
    )
    pending_approvals = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.seller_id == seller.id,
            ApprovalRequest.status == "pending",
        )
        .count()
    )
    resolved_cases = (
        db.query(Case)
        .filter(
            Case.seller_id == seller.id,
            Case.status == "resolved",
        )
        .count()
    )
    rejected_cases = (
        db.query(Case)
        .filter(
            Case.seller_id == seller.id,
            Case.status == "rejected",
        )
        .count()
    )

    return {
        "total_orders": total_orders,
        "open_cases": open_cases,
        "pending_approvals": pending_approvals,
        "resolved_cases": resolved_cases,
        "rejected_cases": rejected_cases,
    }
