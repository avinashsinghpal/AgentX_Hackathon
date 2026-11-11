from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentSeller, DbSession
from app.models.case import ApprovalRequest
from app.services.approvals import (
    ApprovalNotFoundError,
    ApprovalService,
    ApprovalStateError,
    resolve_requested_amount_minor,
)
from app.services.orders import order_items_payload

router = APIRouter(prefix="/approvals", tags=["Seller Approvals"])


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    seller_notes: str | None = Field(default=None, max_length=1000)


@router.get("")
def list_approvals(
    seller: CurrentSeller,
    db: DbSession,
    status_filter: str | None = None,
) -> list[dict[str, Any]]:
    query = db.query(ApprovalRequest).filter(ApprovalRequest.seller_id == seller.id)
    if status_filter:
        query = query.filter(ApprovalRequest.status == status_filter)
    else:
        # Default to pending requests
        query = query.filter(ApprovalRequest.status == "pending")

    approvals = query.order_by(ApprovalRequest.created_at.desc()).all()

    results = []
    for app_req in approvals:
        c = app_req.case
        order = c.order if c else None
        buyer_name = c.buyer.user.full_name if c and c.buyer and c.buyer.user else "Customer"
        results.append(
            {
                "id": app_req.id,
                "case_id": app_req.case_id,
                "case_number": c.case_number if c else "",
                "buyer_name": buyer_name,
                "reason": app_req.reason,
                "auto_evaluation_summary": app_req.auto_evaluation_summary,
                "requested_action": app_req.requested_action,
                "requested_amount_minor": resolve_requested_amount_minor(app_req, order),
                "currency": app_req.currency or (order.currency if order else "INR"),
                "policy_evaluation_id": app_req.policy_evaluation_id,
                "action_id": app_req.action_id,
                "status": app_req.status,
                "seller_notes": app_req.seller_notes,
                "created_at": app_req.created_at.isoformat(),
                "expires_at": app_req.expires_at.isoformat() if app_req.expires_at else None,
                "decided_at": app_req.decided_at.isoformat() if app_req.decided_at else None,
                "order": {
                    "order_number": order.order_number if order else "",
                    "total_amount": order.total_amount if order else 0,
                    "currency": order.currency if order else "INR",
                    "items": order_items_payload(order) if order else [],
                }
                if order
                else None,
                "customer_narrative": c.customer_narrative if c else "",
                "evidence_urls": c.evidence_urls if c else [],
            }
        )
    return results


@router.post("/{approval_id}/decide")
def decide_approval(
    approval_id: str,
    data: ApprovalDecisionRequest,
    seller: CurrentSeller,
    db: DbSession,
) -> dict[str, Any]:
    service = ApprovalService()
    try:
        outcome = service.decide(
            db,
            approval_id=approval_id,
            seller=seller,
            decision=data.decision,
            seller_notes=data.seller_notes,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ApprovalStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    approval = outcome.approval
    return {
        "success": True,
        "approval_id": approval.id,
        "status": approval.status,
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
        # Approval is authorization; execution is reported separately.
        "executed": outcome.executed,
        "action_id": outcome.action.action.id if outcome.action else approval.action_id,
        "failure_reason": outcome.failure_reason,
        "case_status": outcome.case.status,
        "case_decision": outcome.case.decision,
    }
