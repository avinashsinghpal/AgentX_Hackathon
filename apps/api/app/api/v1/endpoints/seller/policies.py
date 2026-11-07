from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentSeller, DbSession
from app.models.seller import SellerPolicy
from app.schemas.policy import DEFAULT_POLICY_YAML, parse_and_validate_yaml
from app.services.audit import AuditLogService

router = APIRouter(prefix="/policies", tags=["Seller Policies"])


class PolicySubmitRequest(BaseModel):
    policy_yaml: str


class PolicyValidateRequest(BaseModel):
    policy_yaml: str


@router.get("/active")
def get_active_policy(
    seller: CurrentSeller,
    db: DbSession,
) -> dict[str, Any]:
    policy = (
        db.query(SellerPolicy)
        .filter(
            SellerPolicy.seller_id == seller.id,
            SellerPolicy.is_active.is_(True),
        )
        .order_by(SellerPolicy.version.desc())
        .first()
    )

    if not policy:
        # If no policy exists yet, return default template
        is_valid, parsed, _ = parse_and_validate_yaml(DEFAULT_POLICY_YAML)
        return {
            "has_policy": False,
            "version": 1,
            "policy_yaml": DEFAULT_POLICY_YAML,
            "parsed_rules": parsed.model_dump() if parsed else {},
            "activated_at": None,
        }

    return {
        "has_policy": True,
        "id": policy.id,
        "version": policy.version,
        "policy_yaml": policy.policy_yaml,
        "parsed_rules": policy.parsed_rules,
        "activated_at": policy.activated_at.isoformat() if policy.activated_at else None,
    }


@router.get("/history")
def get_policy_history(
    seller: CurrentSeller,
    db: DbSession,
) -> list[dict[str, Any]]:
    policies = (
        db.query(SellerPolicy)
        .filter(
            SellerPolicy.seller_id == seller.id,
        )
        .order_by(SellerPolicy.version.desc())
        .all()
    )

    return [
        {
            "id": p.id,
            "version": p.version,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat(),
            "activated_at": p.activated_at.isoformat() if p.activated_at else None,
            "returns_window": p.parsed_rules.get("returns", {}).get("window_days"),
            "refund_ceiling": p.parsed_rules.get("refunds", {}).get("auto_approve_up_to"),
        }
        for p in policies
    ]


@router.post("/validate")
def validate_policy(
    data: PolicyValidateRequest,
) -> dict[str, Any]:
    is_valid, parsed, error_msg = parse_and_validate_yaml(data.policy_yaml)
    return {
        "valid": is_valid,
        "error": error_msg,
        "parsed": parsed.model_dump() if parsed else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def save_policy(
    data: PolicySubmitRequest,
    seller: CurrentSeller,
    db: DbSession,
) -> dict[str, Any]:
    is_valid, parsed, error_msg = parse_and_validate_yaml(data.policy_yaml)
    if not is_valid or not parsed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid policy schema: {error_msg}",
        )

    # Deactivate existing policies
    existing_policies = (
        db.query(SellerPolicy)
        .filter(
            SellerPolicy.seller_id == seller.id,
            SellerPolicy.is_active.is_(True),
        )
        .all()
    )
    for p in existing_policies:
        p.is_active = False

    # Compute next version number
    latest = (
        db.query(SellerPolicy)
        .filter(SellerPolicy.seller_id == seller.id)
        .order_by(SellerPolicy.version.desc())
        .first()
    )
    next_version = (latest.version + 1) if latest else 1

    now = datetime.now(UTC)
    new_policy = SellerPolicy(
        seller_id=seller.id,
        version=next_version,
        is_active=True,
        policy_yaml=data.policy_yaml,
        parsed_rules=parsed.model_dump(),
        activated_at=now,
    )
    db.add(new_policy)

    # Update seller onboarding step if on step 3
    if seller.onboarding_step < 4:
        seller.onboarding_step = 4

    db.commit()
    db.refresh(new_policy)

    AuditLogService.log_action(
        db=db,
        action="policy.activated",
        actor_role="seller",
        actor_id=seller.user_id,
        seller_id=seller.id,
        payload={
            "version": new_policy.version,
            "refund_ceiling": parsed.refunds.auto_approve_up_to,
            "return_window_days": parsed.returns.window_days,
        },
    )

    return {
        "success": True,
        "id": new_policy.id,
        "version": new_policy.version,
        "policy_yaml": new_policy.policy_yaml,
        "parsed_rules": new_policy.parsed_rules,
    }
