from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentBuyer, DbSession
from app.models.buyer import Buyer
from app.models.order import Order
from app.models.seller import Seller, SellerCustomerLink
from app.schemas.buyer import InviteAcceptResponse, InviteInfoResponse
from app.services.audit import AuditLogService

router = APIRouter(prefix="/invites", tags=["Customer Invites"])


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@router.get("/{token}", response_model=InviteInfoResponse)
def get_invite_details(
    token: str,
    db: DbSession,
) -> InviteInfoResponse:
    link = (
        db.query(SellerCustomerLink)
        .filter(SellerCustomerLink.invite_token == token.strip())
        .first()
    )

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation link is invalid or does not exist.",
        )

    seller = db.query(Seller).filter(Seller.id == link.seller_id).first()
    seller_name = seller.store_name if seller else "SellerResolve Merchant"

    # If already linked to a buyer, get email
    customer_email = None
    if link.buyer_id:
        buyer = db.query(Buyer).filter(Buyer.id == link.buyer_id).first()
        if buyer and buyer.user:
            customer_email = buyer.user.email

    now = datetime.now(UTC)
    if link.expires_at and ensure_utc(link.expires_at) < now:
        return InviteInfoResponse(
            valid=False,
            invite_token=token,
            seller_name=seller_name,
            seller_id=link.seller_id,
            customer_email=customer_email,
            expires_at=link.expires_at.isoformat(),
            message="This invitation token has expired.",
        )

    if link.invite_status == "accepted":
        return InviteInfoResponse(
            valid=False,
            invite_token=token,
            seller_name=seller_name,
            seller_id=link.seller_id,
            customer_email=customer_email,
            expires_at=link.expires_at.isoformat() if link.expires_at else None,
            message="This invitation token has already been accepted.",
        )

    return InviteInfoResponse(
        valid=True,
        invite_token=token,
        seller_name=seller_name,
        seller_id=link.seller_id,
        customer_email=customer_email,
        expires_at=link.expires_at.isoformat() if link.expires_at else None,
        message=None,
    )


@router.post("/{token}/accept", response_model=InviteAcceptResponse)
def accept_invite(
    token: str,
    buyer: CurrentBuyer,
    db: DbSession,
) -> InviteAcceptResponse:
    link = (
        db.query(SellerCustomerLink)
        .filter(SellerCustomerLink.invite_token == token.strip())
        .first()
    )

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation link is invalid or does not exist.",
        )

    now = datetime.now(UTC)
    if link.expires_at and ensure_utc(link.expires_at) < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation link has expired.",
        )

    if link.invite_status == "accepted" and link.buyer_id != buyer.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has already been claimed by another account.",
        )

    seller = db.query(Seller).filter(Seller.id == link.seller_id).first()
    seller_name = seller.store_name if seller else "Merchant"

    # Link buyer
    link.buyer_id = buyer.id
    link.invite_status = "accepted"
    link.accepted_at = now

    # Also automatically link any existing orders for this seller that don't have a buyer assigned yet
    unassigned_orders = (
        db.query(Order).filter(Order.seller_id == link.seller_id, Order.buyer_id.is_(None)).all()
    )
    for o in unassigned_orders:
        o.buyer_id = buyer.id

    db.commit()

    AuditLogService.log_action(
        db=db,
        action="invite.accepted",
        actor_role="buyer",
        actor_id=buyer.user_id,
        seller_id=link.seller_id,
        payload={
            "token": token,
            "buyer_id": buyer.id,
            "linked_orders_count": len(unassigned_orders),
        },
    )

    return InviteAcceptResponse(
        success=True,
        message=f"Successfully connected to {seller_name}.",
        seller_name=seller_name,
        seller_id=link.seller_id,
    )
