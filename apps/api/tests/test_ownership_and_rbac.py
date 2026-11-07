from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.seller import Seller
from app.models.user import User
from app.services.audit import AuditLogService


def test_unauthenticated_request_returns_401(client: TestClient) -> None:
    res = client.get("/api/v1/seller/audit")
    assert res.status_code == 401


def test_buyer_role_forbidden_from_seller_audit(client: TestClient) -> None:
    # Register as buyer
    buyer_res = client.post(
        "/api/v1/auth/register/buyer",
        json={
            "email": "buyer_rbac@test.com",
            "password": "Password123!",
            "full_name": "Buyer RBAC",
        },
    )
    buyer_token = buyer_res.json()["token"]

    # Clear cookies so client uses Bearer header
    client.cookies.clear()

    # Attempt to access seller endpoint
    res = client.get(
        "/api/v1/seller/audit",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert res.status_code == 403
    detail = res.json().get("error", {}).get("message") or res.json().get("detail", "")
    assert "Requires seller account privileges" in detail


def test_multi_tenant_audit_log_isolation(client: TestClient, db: Session) -> None:
    # Register Seller A
    res_a = client.post(
        "/api/v1/auth/register/seller",
        json={
            "email": "seller_a@test.com",
            "password": "Password123!",
            "full_name": "Seller A",
            "store_name": "Store A",
        },
    )
    token_a = res_a.json()["token"]
    user_a = db.query(User).filter(User.email == "seller_a@test.com").first()
    seller_a = db.query(Seller).filter(Seller.user_id == user_a.id).first()

    # Register Seller B
    res_b = client.post(
        "/api/v1/auth/register/seller",
        json={
            "email": "seller_b@test.com",
            "password": "Password123!",
            "full_name": "Seller B",
            "store_name": "Store B",
        },
    )
    token_b = res_b.json()["token"]
    user_b = db.query(User).filter(User.email == "seller_b@test.com").first()
    seller_b = db.query(Seller).filter(Seller.user_id == user_b.id).first()

    # Log actions for both sellers
    AuditLogService.log_action(
        db,
        action="policy.update",
        actor_role="seller",
        actor_id=user_a.id,
        seller_id=seller_a.id,
        payload={"version": 1},
    )
    AuditLogService.log_action(
        db,
        action="policy.update",
        actor_role="seller",
        actor_id=user_b.id,
        seller_id=seller_b.id,
        payload={"version": 2},
    )

    # Seller A should only see Seller A's records
    client.cookies.clear()
    res_audit_a = client.get("/api/v1/seller/audit", headers={"Authorization": f"Bearer {token_a}"})
    assert res_audit_a.status_code == 200
    records_a = res_audit_a.json()["records"]
    assert len(records_a) == 1
    assert records_a[0]["payload"]["version"] == 1

    # Seller B should only see Seller B's records
    client.cookies.clear()
    res_audit_b = client.get("/api/v1/seller/audit", headers={"Authorization": f"Bearer {token_b}"})
    assert res_audit_b.status_code == 200
    records_b = res_audit_b.json()["records"]
    assert len(records_b) == 1
    assert records_b[0]["payload"]["version"] == 2
