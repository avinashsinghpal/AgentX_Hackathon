from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentSeller, DbSession
from app.models.seller import SellerOperations
from app.services.audit import AuditLogService

router = APIRouter(prefix="/operations", tags=["Seller Operations"])


class OperationsUpdateRequest(BaseModel):
    warehouse_pincodes: list[str] = Field(min_length=1, max_length=100)
    serviceable_pincodes: list[str] = Field(default_factory=lambda: ["*"])
    courier_partners: list[str] = Field(
        default_factory=lambda: ["Delhivery", "Bluedart", "Shadowfax"]
    )
    cod_enabled: bool = Field(default=True)
    support_email: str | None = Field(default=None)
    support_phone: str | None = Field(default=None)
    business_hours: dict[str, Any] | None = Field(default=None)


@router.get("")
def get_operations(
    seller: CurrentSeller,
    db: DbSession,
) -> dict[str, Any]:
    ops = db.query(SellerOperations).filter(SellerOperations.seller_id == seller.id).first()
    if not ops:
        ops = SellerOperations(
            seller_id=seller.id,
            warehouse_pincodes=[],
            serviceable_pincodes=["*"],
            courier_partners=["Delhivery", "Bluedart", "Shadowfax"],
            cod_enabled=True,
            support_email=seller.user.email,
            support_phone=seller.user.phone,
        )
        db.add(ops)
        db.commit()
        db.refresh(ops)

    return {
        "warehouse_pincodes": ops.warehouse_pincodes,
        "serviceable_pincodes": ops.serviceable_pincodes,
        "courier_partners": ops.courier_partners,
        "cod_enabled": ops.cod_enabled,
        "support_email": ops.support_email,
        "support_phone": ops.support_phone,
        "business_hours": ops.business_hours,
    }


@router.put("")
def update_operations(
    data: OperationsUpdateRequest,
    seller: CurrentSeller,
    db: DbSession,
) -> dict[str, Any]:
    ops = db.query(SellerOperations).filter(SellerOperations.seller_id == seller.id).first()
    if not ops:
        ops = SellerOperations(seller_id=seller.id)
        db.add(ops)

    # Clean warehouse pincodes
    clean_pins = [p.strip() for p in data.warehouse_pincodes if p.strip()]
    if not clean_pins:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one valid warehouse dispatch PIN code is required.",
        )

    ops.warehouse_pincodes = clean_pins
    ops.serviceable_pincodes = data.serviceable_pincodes
    ops.courier_partners = data.courier_partners
    ops.cod_enabled = data.cod_enabled
    ops.support_email = data.support_email
    ops.support_phone = data.support_phone
    ops.business_hours = data.business_hours

    # Update seller onboarding step if on step 2
    if seller.onboarding_step < 3:
        seller.onboarding_step = 3

    db.commit()
    db.refresh(ops)

    AuditLogService.log_action(
        db=db,
        action="operations.updated",
        actor_role="seller",
        actor_id=seller.user_id,
        seller_id=seller.id,
        payload={
            "warehouse_pincodes": ops.warehouse_pincodes,
            "cod_enabled": ops.cod_enabled,
        },
    )

    return {
        "success": True,
        "message": "Operations settings updated.",
        "operations": {
            "warehouse_pincodes": ops.warehouse_pincodes,
            "serviceable_pincodes": ops.serviceable_pincodes,
            "courier_partners": ops.courier_partners,
            "cod_enabled": ops.cod_enabled,
            "support_email": ops.support_email,
            "support_phone": ops.support_phone,
        },
    }
