from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentSeller, DbSession
from app.models.seller import SellerOperations, SellerPolicy
from app.services.audit import AuditLogService

router = APIRouter(prefix="/onboarding", tags=["Seller Onboarding"])


class StepPayload(BaseModel):
    step: int = Field(ge=1, le=4)
    data: dict[str, Any] = Field(default_factory=dict)


@router.get("/status")
def get_onboarding_status(
    seller: CurrentSeller,
    db: DbSession,
) -> dict[str, Any]:
    ops = db.query(SellerOperations).filter(SellerOperations.seller_id == seller.id).first()
    has_policy = (
        db.query(SellerPolicy)
        .filter(SellerPolicy.seller_id == seller.id, SellerPolicy.is_active.is_(True))
        .first()
        is not None
    )

    return {
        "status": seller.status,
        "onboarding_step": seller.onboarding_step,
        "has_store_connected": bool(seller.store_name),
        "has_operations": bool(ops and len(ops.warehouse_pincodes) > 0),
        "has_policy": has_policy,
    }


@router.put("/step")
def update_onboarding_step(
    payload: StepPayload,
    seller: CurrentSeller,
    db: DbSession,
) -> dict[str, Any]:
    if payload.step > seller.onboarding_step:
        seller.onboarding_step = payload.step
        db.commit()
        db.refresh(seller)

    return {
        "success": True,
        "current_step": seller.onboarding_step,
    }


@router.post("/activate")
def activate_seller(
    seller: CurrentSeller,
    db: DbSession,
) -> dict[str, Any]:
    ops = db.query(SellerOperations).filter(SellerOperations.seller_id == seller.id).first()
    if not ops or len(ops.warehouse_pincodes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot activate: Operations configuration (warehouse PIN codes) is required.",
        )

    active_policy = (
        db.query(SellerPolicy)
        .filter(
            SellerPolicy.seller_id == seller.id,
            SellerPolicy.is_active.is_(True),
        )
        .first()
    )
    if not active_policy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot activate: At least one active policy must be defined.",
        )

    seller.status = "active"
    seller.onboarding_step = 4
    db.commit()
    db.refresh(seller)

    # Log activation in immutable audit trail
    AuditLogService.log_action(
        db=db,
        action="seller.activated",
        actor_role="seller",
        actor_id=seller.user_id,
        seller_id=seller.id,
        payload={"store_name": seller.store_name, "policy_version": active_policy.version},
    )

    return {
        "success": True,
        "status": seller.status,
        "redirect_uri": "/seller/dashboard",
    }
