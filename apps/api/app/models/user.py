from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.buyer import Buyer
    from app.models.seller import Seller


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )  # "seller" | "buyer"
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # 1:1 Relationships
    seller: Mapped[Optional["Seller"]] = relationship(
        "Seller",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    buyer: Mapped[Optional["Buyer"]] = relationship(
        "Buyer",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
