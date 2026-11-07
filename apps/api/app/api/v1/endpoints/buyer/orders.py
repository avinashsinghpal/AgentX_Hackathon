from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_

from app.api.deps import CurrentBuyer, DbSession
from app.models.order import Order
from app.models.seller import Seller, SellerCustomerLink
from app.models.shipment import Shipment
from app.schemas.buyer import BuyerOrderSummary, OrderLinkRequest

router = APIRouter(prefix="/orders", tags=["Buyer Orders"])


@router.get("", response_model=list[BuyerOrderSummary])
def get_buyer_orders(
    buyer: CurrentBuyer,
    db: DbSession,
) -> list[BuyerOrderSummary]:
    # Find all sellers the buyer has linked with
    linked_seller_ids = [
        link.seller_id
        for link in db.query(SellerCustomerLink)
        .filter(SellerCustomerLink.buyer_id == buyer.id)
        .all()
    ]

    # Query orders directly assigned to buyer or under linked sellers
    if linked_seller_ids:
        query = db.query(Order).filter(
            or_(
                Order.buyer_id == buyer.id,
                Order.seller_id.in_(linked_seller_ids),
            )
        )
    else:
        query = db.query(Order).filter(Order.buyer_id == buyer.id)

    orders = query.order_by(Order.order_date.desc()).all()
    results: list[BuyerOrderSummary] = []

    for o in orders:
        seller = db.query(Seller).filter(Seller.id == o.seller_id).first()
        seller_name = seller.store_name if seller else "Merchant"

        shipment = (
            db.query(Shipment)
            .filter(Shipment.order_id == o.id)
            .order_by(Shipment.created_at.desc())
            .first()
        )

        raw_items: list[dict[str, Any]] = o.items if isinstance(o.items, list) else []
        normalized_items: list[dict[str, Any]] = []
        for it in raw_items:
            unit_price = float(it.get("unit_price") or it.get("price") or 0.0)
            qty = int(it.get("quantity") or 1)
            total_price = float(it.get("total_price") or (unit_price * qty))
            normalized_items.append({
                **it,
                "unit_price": unit_price,
                "total_price": total_price,
                "quantity": qty,
            })

        results.append(
            BuyerOrderSummary(
                id=o.id,
                order_number=o.order_number,
                seller_id=o.seller_id,
                seller_name=seller_name,
                order_date=o.order_date.isoformat(),
                total_amount=o.total_amount / 100.0,
                currency=o.currency,
                payment_method=o.payment_method,
                payment_status=o.payment_status,
                order_status=o.order_status,
                items_count=len(normalized_items),
                items=normalized_items,
                tracking_number=shipment.tracking_number if shipment else None,
                carrier=shipment.courier_partner if shipment else None,
                delivery_date=shipment.actual_delivery_date.isoformat()
                if shipment and shipment.actual_delivery_date
                else None,
                eligible_for_complaint=o.order_status in ["delivered", "shipped", "placed"],
            )
        )

    return results


@router.post("/link", response_model=BuyerOrderSummary)
def link_order(
    data: OrderLinkRequest,
    buyer: CurrentBuyer,
    db: DbSession,
) -> BuyerOrderSummary:
    query = db.query(Order).filter(Order.order_number == data.order_number.strip())
    if data.seller_id:
        query = query.filter(Order.seller_id == data.seller_id)

    order = query.first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order number '{data.order_number}' not found.",
        )

    if order.buyer_id and order.buyer_id != buyer.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order is already claimed by another customer account.",
        )

    order.buyer_id = buyer.id
    db.commit()
    db.refresh(order)

    seller = db.query(Seller).filter(Seller.id == order.seller_id).first()
    seller_name = seller.store_name if seller else "Merchant"

    shipment = (
        db.query(Shipment)
        .filter(Shipment.order_id == order.id)
        .order_by(Shipment.created_at.desc())
        .first()
    )

    items_list: list[dict[str, Any]] = order.items if isinstance(order.items, list) else []

    return BuyerOrderSummary(
        id=order.id,
        order_number=order.order_number,
        seller_id=order.seller_id,
        seller_name=seller_name,
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
        eligible_for_complaint=order.order_status in ["delivered", "shipped", "placed"],
    )
