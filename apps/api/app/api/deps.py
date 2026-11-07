from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import decode_session_token, verify_csrf_token
from app.db.session import SessionLocal
from app.models.buyer import Buyer
from app.models.seller import Seller
from app.models.user import User


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]


def get_token_from_request(
    request: Request,
    sr_session: str | None = Cookie(None),
    authorization: str | None = Header(None),
) -> str | None:
    """Extract session token from Authorization header or HTTP-only cookie."""
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()
    if sr_session:
        return sr_session
    return None


def get_current_user(
    request: Request,
    db: DbSession,
    sr_session: str | None = Cookie(None),
    authorization: str | None = Header(None),
) -> User:
    token = get_token_from_request(request, sr_session, authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
        )

    payload = decode_session_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please sign in again.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed session token.",
        )

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or no longer exists.",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(allowed_role: str) -> Callable[[User], User]:
    def role_checker(current_user: CurrentUser) -> User:
        if current_user.role != allowed_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires {allowed_role} account privileges.",
            )
        return current_user

    return role_checker


def get_current_seller(
    current_user: Annotated[User, Depends(require_role("seller"))],
    db: DbSession,
) -> Seller:
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller profile not initialized.",
        )
    return seller


CurrentSeller = Annotated[Seller, Depends(get_current_seller)]


def get_current_buyer(
    current_user: Annotated[User, Depends(require_role("buyer"))],
    db: DbSession,
) -> Buyer:
    buyer = db.query(Buyer).filter(Buyer.user_id == current_user.id).first()
    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Buyer profile not initialized.",
        )
    return buyer


CurrentBuyer = Annotated[Buyer, Depends(get_current_buyer)]


def verify_csrf(
    request: Request,
    sr_csrf: str | None = Cookie(None),
    x_csrf_token: str | None = Header(None),
) -> None:
    """Enforce CSRF protection on state-changing requests using cookie-to-header double-submit verification."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # If authentication is provided via Bearer token in header, CSRF can be safely bypassed
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return

    # For browser cookie sessions, verify CSRF token
    if not verify_csrf_token(sr_csrf, x_csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF token.",
        )
