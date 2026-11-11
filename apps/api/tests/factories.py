"""Small builders for service-level tests.

These create rows directly through the ORM (not through the API) so tests can
target the deterministic policy engine, action lifecycle and database
constraints in isolation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models.buyer import Buyer
from app.models.case import Case
from app.models.order import Order
from app.models.seller import Seller, SellerPolicy
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas.policy import PolicySchema, policy_rules_dict


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def make_user(db: Session, *, role: str, email: str | None = None) -> User:
    user = User(
        email=email or f"{unique(role)}@test.local",
        full_name=f"{role.title()} User",
        password_hash="test-hash",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def make_seller(
    db: Session,
    *,
    currency: str = "INR",
    status: str = "active",
) -> Seller:
    user = make_user(db, role="seller")
    seller = Seller(
        user_id=user.id,
        store_name=f"Store {uuid.uuid4().hex[:6]}",
        store_url="https://store.test",
        currency=currency,
        status=status,
    )
    db.add(seller)
    db.flush()
    return seller


def make_buyer(db: Session) -> Buyer:
    user = make_user(db, role="buyer")
    buyer = Buyer(user_id=user.id, default_shipping_address={"city": "Testville"})
    db.add(buyer)
    db.flush()
    return buyer


def make_policy(
    db: Session,
    seller: Seller,
    policy: PolicySchema | None = None,
    *,
    version: int = 1,
    active: bool = True,
) -> SellerPolicy:
    document = policy or PolicySchema(currency=seller.currency)
    row = SellerPolicy(
        seller_id=seller.id,
        version=version,
        is_active=active,
        policy_yaml=document.model_dump_json(),
        parsed_rules=policy_rules_dict(document),
    )
    db.add(row)
    db.flush()
    return row


def make_order(
    db: Session,
    seller: Seller,
    buyer: Buyer | None,
    *,
    total_minor: int = 4500,
    currency: str | None = None,
    order_status: str = "delivered",
    payment_method: str = "prepaid",
    payment_status: str = "captured",
    days_ago: int = 2,
    items: list[dict[str, Any]] | None = None,
    order_number: str | None = None,
) -> Order:
    order = Order(
        seller_id=seller.id,
        buyer_id=buyer.id if buyer else None,
        order_number=order_number or unique("ORD"),
        order_date=datetime.now(UTC) - timedelta(days=days_ago),
        total_amount=total_minor,
        currency=currency or seller.currency,
        payment_method=payment_method,
        payment_status=payment_status,
        order_status=order_status,
        shipping_address={"city": "Testville"},
        items=items
        if items is not None
        else [
            {
                "sku": "SKU-1",
                "title": "Test Item",
                "quantity": 1,
                "unit_price": total_minor / 100.0,
            }
        ],
    )
    db.add(order)
    db.flush()
    return order


def make_shipment(
    db: Session,
    order: Order,
    *,
    status: str = "delivered",
    promised_days_ago: int = 2,
    actual_delivery_days_ago: int | None = 2,
    tracking_events: list[dict[str, Any]] | None = None,
) -> Shipment:
    now = datetime.now(UTC)
    shipment = Shipment(
        order_id=order.id,
        courier_partner="Delhivery",
        tracking_number=unique("TRK"),
        dispatch_pincode="110001",
        destination_pincode="560001",
        status=status,
        promised_delivery_date=now - timedelta(days=promised_days_ago),
        actual_delivery_date=(
            now - timedelta(days=actual_delivery_days_ago)
            if actual_delivery_days_ago is not None
            else None
        ),
        tracking_events=tracking_events
        if tracking_events is not None
        else [
            {
                "status": status,
                "timestamp": (
                    now - timedelta(days=actual_delivery_days_ago)
                    if actual_delivery_days_ago is not None
                    else now
                ).isoformat(),
                "location": "Hub",
                "description": f"Shipment {status}",
            }
        ],
    )
    db.add(shipment)
    db.flush()
    return shipment


def make_case(
    db: Session,
    order: Order,
    *,
    category: str = "return",
    evidence: list[str] | None = None,
    status: str = "open",
    narrative: str = "I would like a resolution for this order.",
) -> Case:
    assert order.buyer_id is not None
    case = Case(
        case_number=unique("CAS"),
        seller_id=order.seller_id,
        buyer_id=order.buyer_id,
        order_id=order.id,
        issue_category=category,
        status=status,
        customer_narrative=narrative,
        evidence_urls=evidence or [],
    )
    db.add(case)
    db.flush()
    return case
