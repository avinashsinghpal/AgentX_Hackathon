from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.case import ApprovalRequest, Case
from app.models.order import Order
from app.models.seller import Seller
from app.models.user import User
from app.schemas.policy import DEFAULT_POLICY_YAML


def test_onboarding_status_and_progression(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/register/seller",
        json={
            "email": "onboard_seller@test.com",
            "password": "Password123!",
            "full_name": "Onboard User",
            "store_name": "Onboard Store",
        },
    )
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Check status
    status_res = client.get("/api/v1/seller/onboarding/status", headers=headers)
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["status"] == "onboarding"
    assert data["has_store_connected"] is True
    assert data["has_operations"] is False
    assert data["has_policy"] is False

    # Attempt activate before operations and policy should fail
    act_res = client.post("/api/v1/seller/onboarding/activate", headers=headers)
    assert act_res.status_code == 400


def test_operations_update(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/register/seller",
        json={
            "email": "ops_seller@test.com",
            "password": "Password123!",
            "full_name": "Ops User",
            "store_name": "Ops Store",
        },
    )
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_payload = {
        "warehouse_pincodes": ["560001", "110001"],
        "serviceable_pincodes": ["*"],
        "courier_partners": ["Delhivery", "Bluedart"],
        "cod_enabled": True,
        "support_email": "help@opsstore.in",
        "support_phone": "+91 80 1234 5678",
    }
    put_res = client.put("/api/v1/seller/operations", headers=headers, json=update_payload)
    assert put_res.status_code == 200
    assert put_res.json()["success"] is True

    get_res = client.get("/api/v1/seller/operations", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["warehouse_pincodes"] == ["560001", "110001"]


def test_policy_validation_and_publishing(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/register/seller",
        json={
            "email": "policy_seller@test.com",
            "password": "Password123!",
            "full_name": "Policy User",
            "store_name": "Policy Store",
        },
    )
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test dry-run validation with default YAML
    val_res = client.post(
        "/api/v1/seller/policies/validate",
        headers=headers,
        json={"policy_yaml": DEFAULT_POLICY_YAML},
    )
    assert val_res.status_code == 200
    assert val_res.json()["valid"] is True

    # Test dry-run validation with invalid YAML
    invalid_yaml = "returns:\n  window_days: -5"  # negative days violates ge=0
    val_bad = client.post(
        "/api/v1/seller/policies/validate",
        headers=headers,
        json={"policy_yaml": invalid_yaml},
    )
    assert val_bad.status_code == 200
    assert val_bad.json()["valid"] is False

    # Publish policy
    pub_res = client.post(
        "/api/v1/seller/policies",
        headers=headers,
        json={"policy_yaml": DEFAULT_POLICY_YAML, "confirm": True},
    )
    assert pub_res.status_code == 201
    assert pub_res.json()["version"] == 1

    # Check active policy
    active_res = client.get("/api/v1/seller/policies/active", headers=headers)
    assert active_res.status_code == 200
    assert active_res.json()["has_policy"] is True
    assert active_res.json()["version"] == 1


def test_seller_activation_flow(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/register/seller",
        json={
            "email": "activate_seller@test.com",
            "password": "Password123!",
            "full_name": "Activate User",
            "store_name": "Activate Store",
        },
    )
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Set operations
    client.put(
        "/api/v1/seller/operations",
        headers=headers,
        json={
            "warehouse_pincodes": ["560001"],
            "serviceable_pincodes": ["*"],
            "courier_partners": ["Delhivery"],
            "cod_enabled": True,
        },
    )

    # Set policy
    client.post(
        "/api/v1/seller/policies",
        headers=headers,
        json={"policy_yaml": DEFAULT_POLICY_YAML, "confirm": True},
    )

    # Now activate
    act_res = client.post("/api/v1/seller/onboarding/activate", headers=headers)
    assert act_res.status_code == 200
    assert act_res.json()["status"] == "active"
    assert act_res.json()["redirect_uri"] == "/seller/dashboard"


def test_demo_order_seeding_and_metrics(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/register/seller",
        json={
            "email": "seed_seller@test.com",
            "password": "Password123!",
            "full_name": "Seed User",
            "store_name": "Seed Store",
        },
    )
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    seed_res = client.post("/api/v1/seller/orders/demo-seed", headers=headers)
    assert seed_res.status_code == 201
    assert seed_res.json()["seeded_count"] == 4

    orders_res = client.get("/api/v1/seller/orders", headers=headers)
    assert orders_res.status_code == 200
    orders = orders_res.json()
    assert len(orders) == 4

    # Verify metrics
    metrics_res = client.get("/api/v1/seller/metrics", headers=headers)
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["total_orders"] == 4
    assert metrics["pending_approvals"] == 0


def test_customer_invites_generator(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/register/seller",
        json={
            "email": "invite_seller@test.com",
            "password": "Password123!",
            "full_name": "Invite User",
            "store_name": "Invite Store",
        },
    )
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/seller/customers/invites", headers=headers)
    assert create_res.status_code == 201
    invite_data = create_res.json()
    assert "invite_token" in invite_data
    assert invite_data["invite_url"].startswith("/invite/")

    list_res = client.get("/api/v1/seller/customers/invites", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_approval_decision_workflow(client: TestClient, db: Session) -> None:
    # Register seller
    res = client.post(
        "/api/v1/auth/register/seller",
        json={
            "email": "approval_seller@test.com",
            "password": "Password123!",
            "full_name": "Approval User",
            "store_name": "Approval Store",
        },
    )
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    user = db.query(User).filter(User.email == "approval_seller@test.com").first()
    seller = db.query(Seller).filter(Seller.user_id == user.id).first()

    # Seed demo orders to get an order
    client.post("/api/v1/seller/orders/demo-seed", headers=headers)
    ord_obj = db.query(Order).filter(Order.seller_id == seller.id).first()

    # Register buyer for valid foreign key
    b_res = client.post(
        "/api/v1/auth/register/buyer",
        json={
            "email": "approval_buyer@test.com",
            "password": "Password123!",
            "full_name": "Approval Buyer",
        },
    )
    buyer_id = b_res.json()["tenant_info"]["buyer_id"]

    # Create dummy case and approval request
    c = Case(
        seller_id=seller.id,
        buyer_id=buyer_id,
        order_id=ord_obj.id,
        case_number="CASE-TEST-999",
        status="pending_approval",
        issue_category="damaged",
        customer_narrative="Item arrived with torn packaging and scratched surface.",
        evidence_urls=[],
        decision="needs_approval",
    )
    db.add(c)
    db.flush()

    app_req = ApprovalRequest(
        case_id=c.id,
        seller_id=seller.id,
        reason="Claim amount exceeds autonomous approval threshold",
        auto_evaluation_summary={"order_total": ord_obj.total_amount, "policy_ceiling": 500},
        requested_action={"type": "refund", "amount": ord_obj.total_amount},
        status="pending",
    )
    db.add(app_req)
    db.commit()

    # List approvals
    list_res = client.get("/api/v1/seller/approvals", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == app_req.id

    # 1-click Approve
    decide_res = client.post(
        f"/api/v1/seller/approvals/{app_req.id}/decide",
        headers=headers,
        json={"decision": "approved", "seller_notes": "One-time goodwill exception granted."},
    )
    assert decide_res.status_code == 200
    assert decide_res.json()["status"] == "approved"

    # Verify case was resolved
    db.refresh(c)
    assert c.status == "resolved"
    assert c.decision == "executed"
