from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, status

from app.api.deps import CurrentSeller, DbSession
from app.models.order import Order
from app.models.shipment import Shipment
from app.services.audit import AuditLogService
from app.services.orders import order_items_payload, sync_order_items, sync_tracking_events

router = APIRouter(prefix="/orders", tags=["Seller Orders"])


@dataclass
class DemoScenario:
    order_number: str
    order_date: datetime
    total_amount: int
    payment_method: str
    payment_status: str
    order_status: str
    items: list[dict[str, Any]]
    shipment_status: str
    courier: str
    tracking: str
    delivered_days_ago: int | None = None
    promised_days_ago: int | None = None


@router.get("")
def list_orders(
    seller: CurrentSeller,
    db: DbSession,
) -> list[dict[str, Any]]:
    orders = (
        db.query(Order).filter(Order.seller_id == seller.id).order_by(Order.order_date.desc()).all()
    )
    results = []
    for ord_obj in orders:
        shipment = ord_obj.shipments[0] if ord_obj.shipments else None
        items = order_items_payload(ord_obj)
        address = ord_obj.shipping_address or {}
        buyer_name = address.get("name")
        if not buyer_name and ord_obj.buyer is not None:
            buyer_name = ord_obj.buyer.user.full_name
        created_at = ord_obj.order_date.isoformat()
        results.append(
            {
                "id": ord_obj.id,
                "order_number": ord_obj.order_number,
                "order_date": created_at,
                # Legacy seller-console fields.  Keep them alongside the
                # normalized names so existing pages do not need a contract
                # migration, while money is explicit about its unit.
                "created_at": created_at,
                "buyer_name": buyer_name or "Guest customer",
                "items_count": len(items),
                "status": ord_obj.order_status,
                "total_amount": ord_obj.total_amount / 100.0,
                "total_amount_minor": ord_obj.total_amount,
                "currency": ord_obj.currency,
                "payment_method": ord_obj.payment_method,
                "payment_status": ord_obj.payment_status,
                "order_status": ord_obj.order_status,
                "shipping_address": ord_obj.shipping_address,
                "items": items,
                "shipment": {
                    "tracking_number": shipment.tracking_number,
                    "courier_partner": shipment.courier_partner,
                    "status": shipment.status,
                    "dispatch_pincode": shipment.dispatch_pincode,
                    "destination_pincode": shipment.destination_pincode,
                    "promised_delivery_date": (
                        shipment.promised_delivery_date.isoformat()
                        if shipment.promised_delivery_date
                        else None
                    ),
                    "actual_delivery_date": (
                        shipment.actual_delivery_date.isoformat()
                        if shipment.actual_delivery_date
                        else None
                    ),
                }
                if shipment
                else None,
            }
        )
    return results


@router.post("/demo-seed", status_code=status.HTTP_201_CREATED)
def seed_demo_orders(
    seller: CurrentSeller,
    db: DbSession,
) -> dict[str, Any]:
    now = datetime.now(UTC)

    scenarios: list[DemoScenario] = [
        DemoScenario(
            order_number="ORD-1001-ELIGIBLE",
            order_date=now - timedelta(days=6),
            total_amount=45000,
            payment_method="prepaid",
            payment_status="captured",
            order_status="delivered",
            items=[
                {
                    "sku": "SKU-COT-01",
                    "title": "Organic Cotton Tee",
                    "quantity": 1,
                    "unit_price": 45000,
                    "returnable": True,
                }
            ],
            shipment_status="delivered",
            courier="Delhivery",
            tracking="DEL100192837",
            delivered_days_ago=3,
        ),
        DemoScenario(
            order_number="ORD-1002-EXPIRED",
            order_date=now - timedelta(days=20),
            total_amount=79900,
            payment_method="prepaid",
            payment_status="captured",
            order_status="delivered",
            items=[
                {
                    "sku": "SKU-DEN-02",
                    "title": "Relaxed Fit Denim",
                    "quantity": 1,
                    "unit_price": 79900,
                    "returnable": True,
                }
            ],
            shipment_status="delivered",
            courier="Bluedart",
            tracking="BLU200281726",
            delivered_days_ago=14,
        ),
        DemoScenario(
            order_number="ORD-1003-HIGHVAL",
            order_date=now - timedelta(days=5),
            total_amount=249900,
            payment_method="prepaid",
            payment_status="captured",
            order_status="delivered",
            items=[
                {
                    "sku": "SKU-JKT-03",
                    "title": "Heritage Canvas Jacket",
                    "quantity": 1,
                    "unit_price": 249900,
                    "returnable": True,
                }
            ],
            shipment_status="delivered",
            courier="Shadowfax",
            tracking="SHD300394857",
            delivered_days_ago=2,
        ),
        DemoScenario(
            order_number="ORD-1004-DELAYED",
            order_date=now - timedelta(days=7),
            total_amount=125000,
            payment_method="cod",
            payment_status="cod_pending",
            order_status="shipped",
            items=[
                {
                    "sku": "SKU-BAG-04",
                    "title": "Waxed Canvas Duffle",
                    "quantity": 1,
                    "unit_price": 125000,
                    "returnable": True,
                }
            ],
            shipment_status="delayed",
            courier="Delhivery",
            tracking="DEL400492831",
            promised_days_ago=3,
        ),
    ]

    created_orders: list[str] = []
    for sc in scenarios:
        existing = (
            db.query(Order)
            .filter(Order.seller_id == seller.id, Order.order_number == sc.order_number)
            .first()
        )
        if existing:
            continue

        deliv_date = (
            (now - timedelta(days=sc.delivered_days_ago))
            if sc.delivered_days_ago is not None
            else None
        )
        prom_date = (
            (now - timedelta(days=sc.promised_days_ago))
            if sc.promised_days_ago is not None
            else (deliv_date or now)
        )

        ord_obj = Order(
            seller_id=seller.id,
            order_number=sc.order_number,
            order_date=sc.order_date,
            currency="INR",
            total_amount=sc.total_amount,
            payment_method=sc.payment_method,
            payment_status=sc.payment_status,
            order_status=sc.order_status,
            shipping_address={
                "name": "Priya Sharma",
                "line1": "Flat 402, Green Glen Layout, Bellandur",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560103",
                "phone": "+91 98765 43210",
            },
            items=sc.items,
        )
        db.add(ord_obj)
        db.flush()
        sync_order_items(db, ord_obj, sc.items)

        tracking_events: list[dict[str, Any]] = [
            {
                "timestamp": (sc.order_date + timedelta(hours=6)).isoformat(),
                "location": "Warehouse Hub, Bengaluru",
                "status": "manifested",
                "description": "Order packed and Manifest generated.",
            },
            {
                "timestamp": (sc.order_date + timedelta(hours=18)).isoformat(),
                "location": "Sorting Center, Bengaluru",
                "status": "in_transit",
                "description": "Package received at regional sorting facility.",
            },
        ]

        if sc.shipment_status == "delivered" and deliv_date is not None:
            tracking_events.append(
                {
                    "timestamp": deliv_date.isoformat(),
                    "location": "Destination Hub, Bengaluru",
                    "status": "delivered",
                    "description": "Shipment delivered to customer.",
                }
            )
        elif sc.shipment_status == "delayed":
            tracking_events.append(
                {
                    "timestamp": (now - timedelta(days=2)).isoformat(),
                    "location": "Transit Hub, Hosur",
                    "status": "delayed",
                    "description": "Weather delay reported. Transit checkpoint stalled.",
                }
            )

        shipment = Shipment(
            order_id=ord_obj.id,
            courier_partner=sc.courier,
            tracking_number=sc.tracking,
            awb=sc.tracking,
            dispatch_pincode="560001",
            destination_pincode="560103",
            promised_delivery_date=prom_date,
            actual_delivery_date=deliv_date,
            status=sc.shipment_status,
            tracking_events=tracking_events,
        )
        db.add(shipment)
        db.flush()
        sync_tracking_events(db, shipment, tracking_events)
        created_orders.append(sc.order_number)

    db.commit()

    AuditLogService.log_action(
        db=db,
        action="demo.orders_seeded",
        actor_role="seller",
        actor_id=seller.user_id,
        seller_id=seller.id,
        payload={"seeded_count": len(created_orders), "orders": created_orders},
    )

    return {
        "success": True,
        "seeded_count": len(created_orders),
        "orders": created_orders,
    }

