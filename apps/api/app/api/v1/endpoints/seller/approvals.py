from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentSeller, DbSession
from app.models.case import ApprovalRequest, Case, CaseMessage
from app.services.audit import AuditLogService

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
        c: Case = app_req.case
        results.append(
            {
                "id": app_req.id,
                "case_id": app_req.case_id,
                "case_number": c.case_number if c else "",
                "reason": app_req.reason,
                "auto_evaluation_summary": app_req.auto_evaluation_summary,
                "requested_action": app_req.requested_action,
                "status": app_req.status,
                "seller_notes": app_req.seller_notes,
                "created_at": app_req.created_at.isoformat(),
                "decided_at": app_req.decided_at.isoformat() if app_req.decided_at else None,
                "order": {
                    "order_number": c.order.order_number if c and c.order else "",
                    "total_amount": c.order.total_amount if c and c.order else 0,
                    "currency": c.order.currency if c and c.order else "INR",
                    "items": c.order.items if c and c.order else [],
                }
                if c and c.order
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
    approval: ApprovalRequest | None = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.seller_id == seller.id,
        )
        .first()
    )

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found.",
        )

    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This request has already been decided ({approval.status}).",
        )

    now = datetime.now(UTC)
    approval.status = data.decision
    approval.seller_notes = data.seller_notes
    approval.decided_at = now

    case: Case | None = approval.case
    if case:
        if data.decision == "approved":
            case.status = "resolved"
            case.decision = "executed"
            case.resolved_at = now
            case.approved_by = seller.user_id

            # Add message to case
            decision_msg = f"Merchant Approved Exception: {approval.reason}"
            if data.seller_notes:
                decision_msg += f"\nMerchant Note: {data.seller_notes}"

            msg = CaseMessage(
                case_id=case.id,
                sender_role="seller",
                message=decision_msg,
                decision_badge="executed",
            )
            db.add(msg)
        else:
            case.status = "rejected"
            case.decision = "not_eligible"
            case.resolved_at = now

            reject_msg = f"Merchant Rejected Exception: {approval.reason}"
            if data.seller_notes:
                reject_msg += f"\nReason: {data.seller_notes}"

            msg = CaseMessage(
                case_id=case.id,
                sender_role="seller",
                message=reject_msg,
                decision_badge="not_eligible",
            )
            db.add(msg)

    db.commit()
    db.refresh(approval)

    AuditLogService.log_action(
        db=db,
        action=f"approval.{data.decision}",
        actor_role="seller",
        actor_id=seller.user_id,
        seller_id=seller.id,
        case_id=approval.case_id,
        payload={
            "approval_id": approval.id,
            "decision": data.decision,
            "seller_notes": data.seller_notes,
            "requested_action": approval.requested_action,
        },
    )

    return {
        "success": True,
        "approval_id": approval.id,
        "status": approval.status,
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
    }
