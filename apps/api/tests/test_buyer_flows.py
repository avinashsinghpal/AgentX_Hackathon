from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.buyer import Buyer
from app.models.order import Order
from app.models.seller import Seller, SellerCustomerLink, SellerPolicy
from app.models.user import User


def test_public_sellers_directory_listing(client: TestClient, db: Session):
    # Setup test active seller
    seller_user = User(
        email="directory_seller@example.com",
        full_name="Directory Seller",
        password_hash="hash123",
        role="seller",
        is_active=True,
    )
    db.add(seller_user)
    db.flush()

    seller = Seller(
        user_id=seller_user.id,
        store_name="Lumina Lifestyle",
        status="active",
        onboarding_step=4,
    )
    db.add(seller)
    db.flush()

    policy = SellerPolicy(
        seller_id=seller.id,
        version=1,
        is_active=True,
        policy_yaml="returns:\n  window_days: 14\nrefunds:\n  auto_approve_max_amount: 3000\n",
        parsed_rules={
            "returns": {
                "window_days": 14,
                "return_shipping_paid_by": "seller",
                "eligible_categories": ["apparel", "home"],
            },
            "refunds": {"auto_approve_max_amount": 3000},
        },
    )
    db.add(policy)
    db.commit()

    # Public directory query
    res = client.get("/api/v1/sellers/directory")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    matching = [s for s in data if s["store_name"] == "Lumina Lifestyle"]
    assert len(matching) == 1
    assert matching[0]["return_window_days"] == 14
    assert matching[0]["auto_approve_max_amount"] == 3000.0

    # Test search query filter
    search_res = client.get("/api/v1/sellers/directory?q=Lumina")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert len(search_data) >= 1
    assert any(s["store_name"] == "Lumina Lifestyle" for s in search_data)


def test_invite_token_validation_and_expiration(client: TestClient, db: Session):
    seller_user = User(
        email="inv_seller@example.com",
        full_name="Invite Seller",
        password_hash="h",
        role="seller",
        is_active=True,
    )
    db.add(seller_user)
    db.flush()
    seller = Seller(user_id=seller_user.id, store_name="Invite Test Store", status="active")
    db.add(seller)
    db.flush()

    # Active valid invite
    active_token = "valid-test-token-12345"
    link_valid = SellerCustomerLink(
        seller_id=seller.id,
        invite_token=active_token,
        invite_status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(link_valid)

    # Expired invite
    expired_token = "expired-token-99999"
    link_expired = SellerCustomerLink(
        seller_id=seller.id,
        invite_token=expired_token,
        invite_status="pending",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    db.add(link_expired)
    db.commit()

    # Check valid token
    res = client.get(f"/api/v1/invites/{active_token}")
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["seller_name"] == "Invite Test Store"

    # Check expired token
    res_exp = client.get(f"/api/v1/invites/{expired_token}")
    assert res_exp.status_code == 200
    assert res_exp.json()["valid"] is False
    assert "expired" in res_exp.json()["message"].lower()

    # Check non-existent token
    res_none = client.get("/api/v1/invites/nonexistent-token-abc")
    assert res_none.status_code == 404


def test_buyer_accepts_invite_and_links_orders(client: TestClient, db: Session):
    # Setup seller and order
    seller_user = User(
        email="s_link@example.com",
        full_name="Link Seller",
        password_hash="h",
        role="seller",
        is_active=True,
    )
    db.add(seller_user)
    db.flush()
    seller = Seller(user_id=seller_user.id, store_name="Link Demo Store", status="active")
    db.add(seller)
    db.flush()

    test_order = Order(
        seller_id=seller.id,
        order_number="ORD-LINK-01",
        order_date=datetime.now(UTC),
        total_amount=150000,
        currency="INR",
        payment_method="prepaid",
        payment_status="captured",
        order_status="delivered",
        shipping_address={"street": "123 MG Road", "city": "Bengaluru", "pincode": "560001"},
        items=[
            {
                "sku": "SKU-1",
                "title": "Test Item",
                "quantity": 1,
                "unit_price": 1500.0,
                "total_price": 1500.0,
            }
        ],
    )
    db.add(test_order)

    # Register buyer
    res_buyer = client.post(
        "/api/v1/auth/register/buyer",
        json={
            "email": "buyer_claim@example.com",
            "password": "SecurePassword123!",
            "full_name": "Aarav Sharma",
        },
    )
    assert res_buyer.status_code == 201
    buyer_token = res_buyer.json()["token"]
    buyer_headers = {"Authorization": f"Bearer {buyer_token}"}

    # Create invite
    token = "token-for-aarav-123"
    link = SellerCustomerLink(
        seller_id=seller.id,
        invite_token=token,
        invite_status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(link)
    db.commit()

    # Buyer accepts invite
    res_accept = client.post(f"/api/v1/invites/{token}/accept", headers=buyer_headers)
    assert res_accept.status_code == 200
    assert res_accept.json()["success"] is True

    # Check buyer orders endpoint now contains the linked order
    res_orders = client.get("/api/v1/buyer/orders", headers=buyer_headers)
    assert res_orders.status_code == 200
    orders_data = res_orders.json()
    assert len(orders_data) >= 1
    assert any(o["order_number"] == "ORD-LINK-01" for o in orders_data)


def test_complaint_case_creation_and_scoping(client: TestClient, db: Session):
    # Create buyer A
    res_a = client.post(
        "/api/v1/auth/register/buyer",
        json={
            "email": "buyer_a@example.com",
            "password": "SecurePassword123!",
            "full_name": "Buyer A",
        },
    )
    token_a = res_a.json()["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Create buyer B
    res_b = client.post(
        "/api/v1/auth/register/buyer",
        json={
            "email": "buyer_b@example.com",
            "password": "SecurePassword123!",
            "full_name": "Buyer B",
        },
    )
    token_b = res_b.json()["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Get Buyer A DB object
    buyer_a_user = db.query(User).filter(User.email == "buyer_a@example.com").first()
    buyer_a = db.query(Buyer).filter(Buyer.user_id == buyer_a_user.id).first()

    # Seller & Order for Buyer A
    seller_user = User(
        email="s_case@example.com",
        full_name="Case Seller User",
        password_hash="h",
        role="seller",
        is_active=True,
    )
    db.add(seller_user)
    db.flush()
    seller = Seller(user_id=seller_user.id, store_name="Case Seller", status="active")
    db.add(seller)
    db.flush()

    order_a = Order(
        seller_id=seller.id,
        buyer_id=buyer_a.id,
        order_number="ORD-CASE-A",
        order_date=datetime.now(UTC),
        total_amount=249900,
        currency="INR",
        payment_method="prepaid",
        payment_status="captured",
        order_status="delivered",
        shipping_address={"street": "A Street", "city": "Bengaluru", "pincode": "560001"},
        items=[
            {
                "sku": "TSHIRT",
                "title": "Premium Shirt",
                "quantity": 1,
                "unit_price": 2499.0,
                "total_price": 2499.0,
            }
        ],
    )
    db.add(order_a)
    db.commit()

    # Buyer B attempts to raise case on Buyer A's order -> Should be FORBIDDEN
    res_steal = client.post(
        "/api/v1/buyer/cases",
        headers=headers_b,
        json={
            "order_id": order_a.id,
            "issue_category": "damaged",
            "customer_narrative": "I received broken package.",
        },
    )
    assert res_steal.status_code == 403

    # Buyer A creates complaint case on their order
    res_case = client.post(
        "/api/v1/buyer/cases",
        headers=headers_a,
        json={
            "order_id": order_a.id,
            "issue_category": "damaged",
            "customer_narrative": "Shirt arrived torn at the left seam with damaged packaging.",
            "evidence_urls": ["upload-uuid-1", "upload-uuid-2"],
        },
    )
    assert res_case.status_code == 200
    case_data = res_case.json()
    case_id = case_data["id"]
    assert case_data["order_number"] == "ORD-CASE-A"
    assert case_data["status"] == "investigating"

    # Buyer A views their cases list
    res_list = client.get("/api/v1/buyer/cases", headers=headers_a)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # Buyer A views case detail
    res_detail = client.get(f"/api/v1/buyer/cases/{case_id}", headers=headers_a)
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["case"]["id"] == case_id
    assert (
        detail_data["customer_narrative"]
        == "Shirt arrived torn at the left seam with damaged packaging."
    )
    assert len(detail_data["messages"]) >= 2  # Buyer narrative + Agent greeting

    # Buyer B attempts to view Buyer A's case detail -> 404 Not Found (scoped)
    res_b_view = client.get(f"/api/v1/buyer/cases/{case_id}", headers=headers_b)
    assert res_b_view.status_code == 404
