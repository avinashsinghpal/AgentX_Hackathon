#!/usr/bin/env python3
"""Seed default demo seller and buyer accounts for live testing.

Credentials:
- Seller: seller@store.com / Password123!
- Buyer: buyer@example.com / Password123!
"""

import hashlib
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

os.environ.setdefault("ENV", "development")
os.environ.setdefault("SECRET_KEY", "replace-with-a-secure-random-32-byte-hex-key-in-production")

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import engine, get_db
from app.models.buyer import Buyer
from app.models.order import Order
from app.models.seller import Seller, SellerCustomerLink, SellerOperations, SellerPolicy
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas.policy import PolicySchema, policy_to_yaml


def seed_demo_accounts() -> None:
    Base.metadata.create_all(bind=engine)
    db = next(get_db())

    try:
        now = datetime.now(UTC)

        # 1. Demo Seller: Apex Electronics
        seller_user = db.query(User).filter(User.email == "seller@store.com").first()
        if not seller_user:
            seller_user = User(
                email="seller@store.com",
                full_name="Apex Administrator",
                password_hash=hash_password("Password123!"),
                role="seller",
                is_active=True,
            )
            db.add(seller_user)
            db.flush()
            print("Created User: seller@store.com")
        else:
            seller_user.password_hash = hash_password("Password123!")
            seller_user.is_active = True
            db.flush()

        seller = db.query(Seller).filter(Seller.user_id == seller_user.id).first()
        if not seller:
            seller = Seller(
                user_id=seller_user.id,
                store_name="Apex Electronics",
                store_url="https://apex-electronics.com",
                # The seeded catalogue and canonical scenarios are priced in USD.
                currency="USD",
                status="active",
                onboarding_step=4,
            )
            db.add(seller)
            db.flush()
            print("Created Seller: Apex Electronics")
        else:
            seller.status = "active"
            seller.onboarding_step = 4
            db.flush()

        # Seller Operations
        ops = db.query(SellerOperations).filter(SellerOperations.seller_id == seller.id).first()
        if not ops:
            ops = SellerOperations(
                seller_id=seller.id,
                warehouse_pincodes=["560001", "110001"],
                serviceable_pincodes=["*"],
                courier_partners=["BlueDart", "Delhivery", "FedEx", "DHL Express"],
                cod_enabled=True,
                support_email="support@apex-electronics.com",
            )
            db.add(ops)
            db.flush()

        # Seller Policy
        policy = db.query(SellerPolicy).filter(SellerPolicy.seller_id == seller.id, SellerPolicy.is_active.is_(True)).first()
        if not policy:
            # Use the same canonical schema and YAML renderer as the policy
            # configuration service so a fresh seed is immediately valid.
            policy_schema = PolicySchema.model_validate(
                {
                    "currency": seller.currency or "INR",
                    "returns": {"window_days": 14},
                    "refunds": {
                        "auto_approve_up_to": 50,
                        "require_seller_approval_above": 50,
                        "instant_refund_without_return_threshold": 25,
                    },
                    "delays": {
                        "notify_after_days_late": 3,
                        "compensation_per_day_late": 10,
                        "max_delay_compensation": 50,
                    },
                    "damage_claims": {"require_photo": True},
                }
            )
            policy_yaml = policy_to_yaml(policy_schema)
            policy = SellerPolicy(
                seller_id=seller.id,
                version=1,
                is_active=True,
                policy_yaml=policy_yaml,
                parsed_rules=policy_schema.model_dump(mode="json"),
                currency=policy_schema.currency,
                content_sha256=hashlib.sha256(policy_yaml.encode("utf-8")).hexdigest(),
                source="seed",
                published_by_user_id=seller_user.id,
                activated_at=now,
            )
            db.add(policy)
            db.flush()

        # 2. Demo Buyer: Maya Lin
        buyer_user = db.query(User).filter(User.email == "buyer@example.com").first()
        if not buyer_user:
            buyer_user = User(
                email="buyer@example.com",
                full_name="Maya Lin",
                password_hash=hash_password("Password123!"),
                role="buyer",
                phone="+91 98765 43210",
                is_active=True,
            )
            db.add(buyer_user)
            db.flush()
            print("Created User: buyer@example.com")
        else:
            buyer_user.password_hash = hash_password("Password123!")
            buyer_user.is_active = True
            db.flush()

        buyer = db.query(Buyer).filter(Buyer.user_id == buyer_user.id).first()
        if not buyer:
            buyer = Buyer(
                user_id=buyer_user.id,
                phone="+91 98765 43210",
                default_shipping_address={
                    "line1": "Flat 402, Lotus Residency",
                    "city": "Bengaluru",
                    "state": "Karnataka",
                    "pincode": "560034",
                },
            )
            db.add(buyer)
            db.flush()
            print("Created Buyer: Maya Lin")

        # Link Buyer to Seller
        link = db.query(SellerCustomerLink).filter(
            SellerCustomerLink.seller_id == seller.id,
            SellerCustomerLink.buyer_id == buyer.id,
        ).first()
        if not link:
            link = SellerCustomerLink(
                seller_id=seller.id,
                buyer_id=buyer.id,
                invite_status="accepted",
                accepted_at=now,
            )
            db.add(link)
            db.flush()

        # Seed Orders for Maya Lin if not present
        existing_orders = db.query(Order).filter(Order.buyer_id == buyer.id).all()
        if not existing_orders:
            orders_data = [
                {
                    "number": "ORD-1001",
                    "amount": 4500,  # $45.00
                    "status": "delivered",
                    "days_ago": 5,
                    "title": "Wireless Noise-Cancelling Earbuds",
                    "sku": "EARBUD-NC-01",
                    "carrier": "BlueDart",
                    "tracking": "TRK-9821448",
                },
                {
                    "number": "ORD-1002",
                    "amount": 8900,  # $89.00
                    "status": "delivered",
                    "days_ago": 22,
                    "title": "Waterproof Winter Trail Jacket",
                    "sku": "JACKET-TRL-02",
                    "carrier": "FedEx",
                    "tracking": "TRK-9821449",
                },
                {
                    "number": "ORD-1003",
                    "amount": 32000,  # $320.00
                    "status": "delivered",
                    "days_ago": 2,
                    "title": "4K Ultra-Wide Curved Monitor 34-inch",
                    "sku": "MONITOR-4K-34",
                    "carrier": "DHL Express",
                    "tracking": "TRK-9821450",
                },
                {
                    "number": "ORD-1004",
                    "amount": 11000,  # $110.00
                    "status": "shipped",
                    "days_ago": 7,
                    "title": "RGB Mechanical Gaming Keyboard",
                    "sku": "KEYBOARD-RGB-04",
                    "carrier": "Delhivery",
                    "tracking": "TRK-9821451",
                },
            ]

            for od in orders_data:
                order = Order(
                    seller_id=seller.id,
                    buyer_id=buyer.id,
                    order_number=od["number"],
                    order_date=now - timedelta(days=od["days_ago"]),
                    currency="USD",
                    total_amount=od["amount"],
                    payment_method="prepaid",
                    payment_status="captured",
                    order_status=od["status"],
                    shipping_address={
                        "line1": "Flat 402, Lotus Residency",
                        "city": "Bengaluru",
                        "state": "Karnataka",
                        "pincode": "560034",
                    },
                    items=[
                        {
                            "sku": od["sku"],
                            "title": od["title"],
                            "quantity": 1,
                            "unit_price": od["amount"] / 100.0,
                            "returnable": True,
                        }
                    ],
                )
                db.add(order)
                db.flush()

                shipment = Shipment(
                    order_id=order.id,
                    courier_partner=od["carrier"],
                    tracking_number=od["tracking"],
                    dispatch_pincode="110001",
                    destination_pincode="560034",
                    promised_delivery_date=now - timedelta(days=od["days_ago"] - 2),
                    actual_delivery_date=(
                        now - timedelta(days=od["days_ago"] - 2) if od["status"] == "delivered" else None
                    ),
                    status=od["status"],
                )
                db.add(shipment)
                db.flush()

            print("Seeded demo orders ORD-1001 through ORD-1004 for Maya Lin")

        db.commit()
        print("\n[SUCCESS] Demo accounts successfully seeded:")
        print("  Seller: seller@store.com / Password123!")
        print("  Buyer:  buyer@example.com  / Password123!")

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_accounts()
