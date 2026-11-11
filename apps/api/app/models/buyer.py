from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.order import Order
    from app.models.user import User


class Buyer(Base):
    __tablename__ = "buyers"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    default_shipping_address: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="buyer")
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="buyer",
    )
    cases: Mapped[list["Case"]] = relationship(
        "Case",
        back_populates="buyer",
    )
