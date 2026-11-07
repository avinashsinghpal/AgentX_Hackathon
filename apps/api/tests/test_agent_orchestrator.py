import re
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.buyer import Buyer
from app.models.case import ApprovalRequest, Case, CaseMessage
from app.models.order import Order
from app.models.seller import Seller, SellerPolicy
from app.models.shipment import Shipment
from app.models.user import User
from app.services.agent.orchestrator import ResolutionOrchestrator
from app.services.monitor import run_delay_monitor_cycle

EMOJI_REGEX = re.compile(
    "[\U00010000-\U0010ffff"
    "\U0001f600-\U0001f64f"
    "\U0001f300-\U0001f5ff"
    "\U0001f680-\U0001f6ff"
    "\U0001f700-\U0001f77f"
    "\U0001f780-\U0001f7ff"
    "\U0001f800-\U0001f8ff"
    "\U0001f900-\U0001f9ff"
    "\U0001fa00-\U0001fa6f"
    "\U0001fa70-\U0001faff"
    "\u2600-\u26ff"
    "\u2700-\u27bf]"
)


def assert_zero_emoji(text: str) -> None:
    matches = EMOJI_REGEX.findall(text)
    assert len(matches) == 0, f"Found forbidden emoji in output: {matches}"


@pytest.mark.asyncio
async def test_agent_scenario_1_eligible_return_auto_resolved(db: Session) -> None:
    now = datetime.now(UTC)

    seller_user = User(
        email="s_sc1@test.com",
        full_name="Scenario 1 Seller",
        password_hash="h",
        role="seller",
        is_active=True,
    )
    db.add(seller_user)
    db.flush()
    seller = Seller(user_id=seller_user.id, store_name="Store 1", status="active")
    db.add(seller)
    db.flush()

    policy = SellerPolicy(
        seller_id=seller.id,
        version=1,
        is_active=True,
        policy_yaml="returns:\n  window_days: 7\nrefunds:\n  auto_approve_max_amount: 2000\n",
        parsed_rules={"returns": {"window_days": 7}, "refunds": {"auto_approve_max_amount": 2000}},
    )
    db.add(policy)

    buyer_user = User(
        email="b_sc1@test.com",
        full_name="Buyer 1",
        password_hash="h",
        role="buyer",
        is_active=True,
    )
    db.add(buyer_user)
    db.flush()
    buyer = Buyer(user_id=buyer_user.id)
    db.add(buyer)
    db.flush()

    order = Order(
        seller_id=seller.id,
        buyer_id=buyer.id,
        order_number="ORD-1001-TEST",
        order_date=now - timedelta(days=3),
        total_amount=129900,  # INR 1299.00
        currency="INR",
        payment_method="prepaid",
        payment_status="captured",
        order_status="delivered",
        shipping_address={"street": "MG Road", "city": "Bengaluru", "pincode": "560001"},
        items=[{"sku": "SHIRT", "title": "Cotton Shirt", "quantity": 1, "total_price": 1299.0}],
    )
    db.add(order)
    db.flush()

    shipment = Shipment(
        order_id=order.id,
        courier_partner="Delhivery",
        tracking_number="DEL-1001",
        dispatch_pincode="560001",
        destination_pincode="560002",
        actual_delivery_date=now - timedelta(days=2),  # delivered 2 days ago
        status="delivered",
    )
    db.add(shipment)
    db.flush()

    case = Case(
        case_number="CAS-1001",
        seller_id=seller.id,
        buyer_id=buyer.id,
        order_id=order.id,
        status="investigating",
        issue_category="return",
        customer_narrative="I would like to return the shirt as size M is slightly loose.",
        evidence_urls=[],
    )
    db.add(case)
    db.commit()

    orchestrator = ResolutionOrchestrator(db=db)
    agent_msg = await orchestrator.process_case_resolution(case.id)

    db.refresh(case)
    assert case.status == "resolved"
    assert case.decision == "executed"
    assert case.resolution_type == "return_label"
    assert "REV-DELHIVERY" in case.outcome_details["reverse_awb"]
    assert agent_msg.decision_badge == "executed"
    assert len(agent_msg.tool_calls) == 4
    assert_zero_emoji(agent_msg.message)


@pytest.mark.asyncio
async def test_agent_scenario_2_expired_return_window_rejected(db: Session) -> None:
    now = datetime.now(UTC)

    seller_user = User(
        email="s_sc2@test.com",
        full_name="Scenario 2 Seller",
        password_hash="h",
        role="seller",
        is_active=True,
    )
    db.add(seller_user)
    db.flush()
    seller = Seller(user_id=seller_user.id, store_name="Store 2", status="active")
    db.add(seller)
    db.flush()

    policy = SellerPolicy(
        seller_id=seller.id,
        version=1,
        is_active=True,
        policy_yaml="returns:\n  window_days: 7\nrefunds:\n  auto_approve_max_amount: 2000\n",
        parsed_rules={"returns": {"window_days": 7}, "refunds": {"auto_approve_max_amount": 2000}},
    )
    db.add(policy)

    buyer_user = User(
        email="b_sc2@test.com",
        full_name="Buyer 2",
        password_hash="h",
        role="buyer",
        is_active=True,
    )
    db.add(buyer_user)
    db.flush()
    buyer = Buyer(user_id=buyer_user.id)
    db.add(buyer)
    db.flush()

    order = Order(
        seller_id=seller.id,
        buyer_id=buyer.id,
        order_number="ORD-1002-TEST",
        order_date=now - timedelta(days=35),
        total_amount=249900,  # INR 2499.00
        currency="INR",
        payment_method="prepaid",
        payment_status="captured",
        order_status="delivered",
        shipping_address={"street": "Indiranagar", "city": "Bengaluru", "pincode": "560038"},
        items=[{"sku": "SHOES", "title": "Sneakers", "quantity": 1, "total_price": 2499.0}],
    )
    db.add(order)
    db.flush()

    shipment = Shipment(
        order_id=order.id,
        courier_partner="Bluedart",
        tracking_number="BLU-1002",
        dispatch_pincode="560001",
        destination_pincode="560038",
        actual_delivery_date=now - timedelta(days=28),  # delivered 28 days ago (exceeds 7 days)
        status="delivered",
    )
    db.add(shipment)
    db.flush()

    case = Case(
        case_number="CAS-1002",
        seller_id=seller.id,
        buyer_id=buyer.id,
        order_id=order.id,
        status="investigating",
        issue_category="return",
        customer_narrative="I bought these sneakers a month ago and would like to return them.",
        evidence_urls=[],
    )
    db.add(case)
    db.commit()

    orchestrator = ResolutionOrchestrator(db=db)
    agent_msg = await orchestrator.process_case_resolution(case.id)

    db.refresh(case)
    assert case.status == "rejected"
    assert case.decision == "not_eligible"
    assert agent_msg.decision_badge == "not_eligible"
    assert "exceeding" in case.outcome_details["reason"].lower()
    assert_zero_emoji(agent_msg.message)


@pytest.mark.asyncio
async def test_agent_scenario_3_high_value_escalated_for_approval(db: Session) -> None:
    now = datetime.now(UTC)

    seller_user = User(
        email="s_sc3@test.com",
        full_name="Scenario 3 Seller",
        password_hash="h",
        role="seller",
        is_active=True,
    )
    db.add(seller_user)
    db.flush()
    seller = Seller(user_id=seller_user.id, store_name="Store 3", status="active")
    db.add(seller)
    db.flush()

    policy = SellerPolicy(
        seller_id=seller.id,
        version=1,
        is_active=True,
        policy_yaml="returns:\n  window_days: 7\nrefunds:\n  auto_approve_max_amount: 2000\n",
        parsed_rules={"returns": {"window_days": 7}, "refunds": {"auto_approve_max_amount": 2000}},
    )
    db.add(policy)

    buyer_user = User(
        email="b_sc3@test.com",
        full_name="Buyer 3",
        password_hash="h",
        role="buyer",
        is_active=True,
    )
    db.add(buyer_user)
    db.flush()
    buyer = Buyer(user_id=buyer_user.id)
    db.add(buyer)
    db.flush()

    order = Order(
        seller_id=seller.id,
        buyer_id=buyer.id,
        order_number="ORD-1003-TEST",
        order_date=now - timedelta(days=2),
        total_amount=899900,  # INR 8999.00 (exceeds INR 2000 ceiling)
        currency="INR",
        payment_method="prepaid",
        payment_status="captured",
        order_status="delivered",
        shipping_address={"street": "Koramangala", "city": "Bengaluru", "pincode": "560034"},
        items=[
            {"sku": "WATCH", "title": "Chronograph Watch", "quantity": 1, "total_price": 8999.0}
        ],
    )
    db.add(order)
    db.flush()

    shipment = Shipment(
        order_id=order.id,
        courier_partner="Delhivery",
        tracking_number="DEL-1003",
        dispatch_pincode="560001",
        destination_pincode="560034",
        actual_delivery_date=now - timedelta(days=1),
        status="delivered",
    )
    db.add(shipment)
    db.flush()

    case = Case(
        case_number="CAS-1003",
        seller_id=seller.id,
        buyer_id=buyer.id,
        order_id=order.id,
        status="investigating",
        issue_category="damaged",
        customer_narrative="The watch glass arrived cracked.",
        evidence_urls=["file-id-watch-1"],
    )
    db.add(case)
    db.commit()

    orchestrator = ResolutionOrchestrator(db=db)
    agent_msg = await orchestrator.process_case_resolution(case.id)

    db.refresh(case)
    assert case.status == "pending_approval"
    assert case.decision == "needs_approval"
    assert agent_msg.decision_badge == "needs_approval"

    # Verify ApprovalRequest created in database
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.case_id == case.id).first()
    assert approval is not None
    assert approval.status == "pending"
    assert approval.requested_action["amount"] == 8999.0
    assert_zero_emoji(agent_msg.message)


def test_agent_scenario_4_delayed_package_proactive_compensation(db: Session) -> None:
    now = datetime.now(UTC)

    seller_user = User(
        email="s_sc4@test.com",
        full_name="Scenario 4 Seller",
        password_hash="h",
        role="seller",
        is_active=True,
    )
    db.add(seller_user)
    db.flush()
    seller = Seller(user_id=seller_user.id, store_name="Store 4", status="active")
    db.add(seller)
    db.flush()

    policy = SellerPolicy(
        seller_id=seller.id,
        version=1,
        is_active=True,
        policy_yaml="delays:\n  delay_threshold_days: 3\n  compensation_per_day_late: 50\n  max_delay_compensation: 250\n",
        parsed_rules={
            "delays": {
                "delay_threshold_days": 3,
                "compensation_per_day_late": 50,
                "max_delay_compensation": 250,
            }
        },
    )
    db.add(policy)

    buyer_user = User(
        email="b_sc4@test.com",
        full_name="Buyer 4",
        password_hash="h",
        role="buyer",
        is_active=True,
    )
    db.add(buyer_user)
    db.flush()
    buyer = Buyer(user_id=buyer_user.id)
    db.add(buyer)
    db.flush()

    order = Order(
        seller_id=seller.id,
        buyer_id=buyer.id,
        order_number="ORD-1004-TEST",
        order_date=now - timedelta(days=7),
        total_amount=199900,
        currency="INR",
        payment_method="prepaid",
        payment_status="captured",
        order_status="shipped",
        shipping_address={"street": "Whitefield", "city": "Bengaluru", "pincode": "560066"},
        items=[
            {"sku": "HEADPHONES", "title": "Wireless Earbuds", "quantity": 1, "total_price": 1999.0}
        ],
    )
    db.add(order)
    db.flush()

    shipment = Shipment(
        order_id=order.id,
        courier_partner="Delhivery",
        tracking_number="DEL-1004",
        dispatch_pincode="560001",
        destination_pincode="560066",
        promised_delivery_date=now
        - timedelta(days=4),  # promised 4 days ago -> 4 days late >= 3 days threshold
        status="in_transit",
    )
    db.add(shipment)
    db.commit()

    # Trigger proactive background monitor cycle
    remedies = run_delay_monitor_cycle(db)
    assert len(remedies) == 1
    assert remedies[0]["order_number"] == "ORD-1004-TEST"
    assert remedies[0]["days_late"] >= 3
    assert remedies[0]["compensation"] == 200.0  # 4 * 50 = 200

    # Verify proactive case created in DB
    proactive_case = (
        db.query(Case).filter(Case.order_id == order.id, Case.issue_category == "delay").first()
    )
    assert proactive_case is not None
    assert proactive_case.status == "resolved"
    assert proactive_case.decision == "executed"
    assert proactive_case.resolution_type == "delay_compensation"

    # Verify explanatory message has zero emojis
    msg = db.query(CaseMessage).filter(CaseMessage.case_id == proactive_case.id).first()
    assert msg is not None
    assert_zero_emoji(msg.message)


def test_chat_turn_endpoint(client: TestClient, db: Session) -> None:
    # Setup buyer
    res_b = client.post(
        "/api/v1/auth/register/buyer",
        json={"email": "chat_user@test.com", "password": "Password123!", "full_name": "Chat User"},
    )
    token = res_b.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    buyer_user = db.query(User).filter(User.email == "chat_user@test.com").first()
    buyer = db.query(Buyer).filter(Buyer.user_id == buyer_user.id).first()

    # Seller & Order
    seller_user = User(
        email="s_chat@test.com",
        full_name="Chat Seller",
        password_hash="h",
        role="seller",
        is_active=True,
    )
    db.add(seller_user)
    db.flush()
    seller = Seller(user_id=seller_user.id, store_name="Chat Store", status="active")
    db.add(seller)
    db.flush()

    order = Order(
        seller_id=seller.id,
        buyer_id=buyer.id,
        order_number="ORD-CHAT-01",
        order_date=datetime.now(UTC),
        total_amount=150000,
        currency="INR",
        payment_method="prepaid",
        payment_status="captured",
        order_status="delivered",
        shipping_address={"street": "Street", "city": "BLR", "pincode": "560001"},
        items=[{"sku": "ITEM", "title": "Product", "quantity": 1, "total_price": 1500.0}],
    )
    db.add(order)
    db.flush()

    case = Case(
        case_number="CAS-CHAT-01",
        seller_id=seller.id,
        buyer_id=buyer.id,
        order_id=order.id,
        status="investigating",
        issue_category="return",
        customer_narrative="I want to return.",
    )
    db.add(case)
    db.commit()

    # Post message to chat endpoint
    res = client.post(
        f"/api/v1/buyer/cases/{case.id}/chat",
        headers=headers,
        json={"message": "Can you check if my return label has been issued?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["sender_role"] == "agent"
    assert data["decision_badge"] is not None
    assert_zero_emoji(data["message"])
