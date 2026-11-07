from typing import Any

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.security import (
    create_session_token,
    generate_csrf_token,
    hash_password,
    verify_password,
)
from app.models.buyer import Buyer
from app.models.seller import Seller, SellerOperations
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    BuyerRegisterRequest,
    LoginRequest,
    SellerRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_auth_cookies(response: Response, user_id: str, role: str) -> tuple[str, str]:
    session_token = create_session_token(user_id=user_id, role=role)
    csrf_token = generate_csrf_token()

    is_prod = settings.ENV == "production"

    response.set_cookie(
        key="sr_session",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=settings.SESSION_EXPIRY_SECONDS,
        path="/",
    )
    response.set_cookie(
        key="sr_csrf",
        value=csrf_token,
        httponly=False,  # Readable by frontend for X-CSRF-Token header
        samesite="lax",
        secure=is_prod,
        max_age=settings.SESSION_EXPIRY_SECONDS,
        path="/",
    )
    return session_token, csrf_token


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="sr_session", path="/")
    response.delete_cookie(key="sr_csrf", path="/")


@router.post("/register/seller", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_seller(
    data: SellerRegisterRequest,
    db: DbSession,
    response: Response,
) -> AuthResponse:
    existing_user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    user = User(
        email=data.email.lower().strip(),
        password_hash=hash_password(data.password),
        role="seller",
        full_name=data.full_name.strip(),
        phone=data.phone.strip() if data.phone else None,
        is_active=True,
    )
    db.add(user)
    db.flush()

    seller = Seller(
        user_id=user.id,
        store_name=data.store_name.strip(),
        store_url=data.store_url.strip() if data.store_url else None,
        currency="INR",
        status="onboarding",
        onboarding_step=1,
    )
    db.add(seller)
    db.flush()

    ops = SellerOperations(
        seller_id=seller.id,
        warehouse_pincodes=[],
        serviceable_pincodes=["*"],
        courier_partners=["Delhivery", "Bluedart", "Shadowfax"],
        cod_enabled=True,
        support_email=user.email,
        support_phone=user.phone,
    )
    db.add(ops)
    db.commit()
    db.refresh(user)

    session_token, csrf_token = _set_auth_cookies(response, user.id, user.role)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        redirect_uri="/seller/onboarding",
        csrf_token=csrf_token,
        token=session_token,
        tenant_info={
            "seller_id": seller.id,
            "store_name": seller.store_name,
            "status": seller.status,
        },
    )


@router.post("/register/buyer", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_buyer(
    data: BuyerRegisterRequest,
    db: DbSession,
    response: Response,
) -> AuthResponse:
    existing_user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    user = User(
        email=data.email.lower().strip(),
        password_hash=hash_password(data.password),
        role="buyer",
        full_name=data.full_name.strip(),
        phone=data.phone.strip() if data.phone else None,
        is_active=True,
    )
    db.add(user)
    db.flush()

    buyer = Buyer(
        user_id=user.id,
        phone=user.phone,
    )
    db.add(buyer)
    db.commit()
    db.refresh(user)

    session_token, csrf_token = _set_auth_cookies(response, user.id, user.role)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        redirect_uri="/buyer",
        csrf_token=csrf_token,
        token=session_token,
        tenant_info={"buyer_id": buyer.id},
    )


@router.post("/login", response_model=AuthResponse)
def login(
    data: LoginRequest,
    db: DbSession,
    response: Response,
) -> AuthResponse:
    user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled.",
        )

    session_token, csrf_token = _set_auth_cookies(response, user.id, user.role)

    tenant_info = {}
    if user.role == "seller":
        seller = db.query(Seller).filter(Seller.user_id == user.id).first()
        if seller:
            tenant_info = {
                "seller_id": seller.id,
                "store_name": seller.store_name,
                "status": seller.status,
            }
            redirect_uri = (
                "/seller/dashboard" if seller.status == "active" else "/seller/onboarding"
            )
        else:
            redirect_uri = "/seller/onboarding"
    else:
        buyer = db.query(Buyer).filter(Buyer.user_id == user.id).first()
        if buyer:
            tenant_info = {"buyer_id": buyer.id}
        redirect_uri = "/buyer"

    return AuthResponse(
        user=UserResponse.model_validate(user),
        redirect_uri=redirect_uri,
        csrf_token=csrf_token,
        token=session_token,
        tenant_info=tenant_info,
    )


@router.post("/logout")
def logout(response: Response) -> dict[str, Any]:
    _clear_auth_cookies(response)
    return {"success": True, "message": "Signed out successfully."}


@router.get("/me")
def get_current_user_profile(
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "user": UserResponse.model_validate(current_user).model_dump(),
    }
    if current_user.role == "seller":
        seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
        if seller:
            profile["seller"] = {
                "id": seller.id,
                "store_name": seller.store_name,
                "status": seller.status,
                "onboarding_step": seller.onboarding_step,
                "currency": seller.currency,
            }
    elif current_user.role == "buyer":
        buyer = db.query(Buyer).filter(Buyer.user_id == current_user.id).first()
        if buyer:
            profile["buyer"] = {
                "id": buyer.id,
                "phone": buyer.phone,
                "default_shipping_address": buyer.default_shipping_address,
            }
    return profile
