from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.seller import Seller, SellerOperations
from app.models.user import User


def test_register_seller_success(client: TestClient, db: Session) -> None:
    payload = {
        "email": "seller@artisan.in",
        "password": "StrongPassword123!",
        "full_name": "Vikram Patel",
        "store_name": "The Artisan Store",
        "phone": "+91 98765 43210",
        "store_url": "https://artisan.in",
    }
    response = client.post("/api/v1/auth/register/seller", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["user"]["email"] == "seller@artisan.in"
    assert data["user"]["role"] == "seller"
    assert data["redirect_uri"] == "/seller/onboarding"
    assert "sr_session" in response.cookies
    assert "sr_csrf" in response.cookies

    # Verify database records
    user = db.query(User).filter(User.email == "seller@artisan.in").first()
    assert user is not None
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password("StrongPassword123!", user.password_hash)

    seller = db.query(Seller).filter(Seller.user_id == user.id).first()
    assert seller is not None
    assert seller.store_name == "The Artisan Store"
    assert seller.status == "onboarding"

    ops = db.query(SellerOperations).filter(SellerOperations.seller_id == seller.id).first()
    assert ops is not None
    assert ops.cod_enabled is True


def test_register_duplicate_email_fails(client: TestClient) -> None:
    payload = {
        "email": "duplicate@test.com",
        "password": "Password123!",
        "full_name": "Test User",
        "store_name": "Test Store",
    }
    res1 = client.post("/api/v1/auth/register/seller", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register/seller", json=payload)
    assert res2.status_code == 409


def test_register_buyer_success(client: TestClient, db: Session) -> None:
    payload = {
        "email": "priya@customer.in",
        "password": "BuyerPassword123!",
        "full_name": "Priya Sharma",
        "phone": "+91 91234 56789",
    }
    response = client.post("/api/v1/auth/register/buyer", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["user"]["email"] == "priya@customer.in"
    assert data["user"]["role"] == "buyer"
    assert data["redirect_uri"] == "/buyer"
    assert "sr_session" in response.cookies


def test_login_success(client: TestClient) -> None:
    reg_payload = {
        "email": "login_test@store.com",
        "password": "MySecretPassword123!",
        "full_name": "Login User",
        "store_name": "Login Store",
    }
    client.post("/api/v1/auth/register/seller", json=reg_payload)

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "login_test@store.com", "password": "MySecretPassword123!"},
    )
    assert login_res.status_code == 200
    assert "token" in login_res.json()
    assert "sr_session" in login_res.cookies


def test_login_wrong_password_fails(client: TestClient) -> None:
    reg_payload = {
        "email": "wrong_pw@store.com",
        "password": "CorrectPassword123!",
        "full_name": "User",
        "store_name": "Store",
    }
    client.post("/api/v1/auth/register/seller", json=reg_payload)

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong_pw@store.com", "password": "WrongPassword!"},
    )
    assert login_res.status_code == 401


def test_logout_clears_cookies(client: TestClient) -> None:
    res = client.post("/api/v1/auth/logout")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_me_endpoint(client: TestClient) -> None:
    reg_payload = {
        "email": "me_test@store.com",
        "password": "Password123!",
        "full_name": "Me User",
        "store_name": "Me Store",
    }
    reg_res = client.post("/api/v1/auth/register/seller", json=reg_payload)
    token = reg_res.json()["token"]

    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["user"]["email"] == "me_test@store.com"
    assert data["user"]["role"] == "seller"
    assert data["seller"]["store_name"] == "Me Store"
