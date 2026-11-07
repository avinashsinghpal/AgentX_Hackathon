import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, status

from app.api.deps import CurrentSeller, DbSession
from app.models.seller import SellerCustomerLink
from app.services.audit import AuditLogService

router = APIRouter(prefix="/customers", tags=["Seller Customers"])


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@router.get("/invites")
def list_invites(
    seller: CurrentSeller,
    db: DbSession,
) -> list[dict[str, Any]]:
    invites = (
        db.query(SellerCustomerLink)
        .filter(
            SellerCustomerLink.seller_id == seller.id,
        )
        .order_by(SellerCustomerLink.created_at.desc())
        .all()
    )

    now = datetime.now(UTC)
    results = []
    for inv in invites:
        exp_utc = ensure_utc(inv.expires_at)
        is_expired = exp_utc is not None and exp_utc < now and inv.invite_status == "pending"
        current_status = "expired" if is_expired else inv.invite_status
        results.append(
            {
                "id": inv.id,
                "invite_token": inv.invite_token,
                "invite_url": f"/invite/{inv.invite_token}" if inv.invite_token else None,
                "status": current_status,
                "created_at": inv.created_at.isoformat(),
                "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
                "accepted_at": inv.accepted_at.isoformat() if inv.accepted_at else None,
            }
        )
    return results


@router.post("/invites", status_code=status.HTTP_201_CREATED)
def create_invite(
    seller: CurrentSeller,
    db: DbSession,
) -> dict[str, Any]:
    token = secrets.token_urlsafe(24)
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=7)

    invite = SellerCustomerLink(
        seller_id=seller.id,
        invite_token=token,
        invite_status="pending",
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    AuditLogService.log_action(
        db=db,
        action="customer.invite_created",
        actor_role="seller",
        actor_id=seller.user_id,
        seller_id=seller.id,
        payload={"token_prefix": token[:6], "expires_at": expires_at.isoformat()},
    )

    return {
        "id": invite.id,
        "invite_token": token,
        "invite_url": f"/invite/{token}",
        "expires_at": expires_at.isoformat(),
        "status": invite.invite_status,
    }
