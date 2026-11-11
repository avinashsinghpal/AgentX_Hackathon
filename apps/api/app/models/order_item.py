from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.order import Order


class OrderItem(Base):
    """Normalized order line.

    Authoritative representation of order contents.  The legacy ``orders.items``
    JSON column is retained only as a read-only snapshot kept in sync by
    ``app.services.orders.sync_order_items``.
    """

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price_minor >= 0", name="ck_order_items_unit_price_non_negative"),
        Index("ix_order_items_order_id", "order_id"),
        Index("ix_order_items_sku", "sku"),
    )

    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    returnable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="order_items")

    def to_legacy_dict(self) -> dict[str, object]:
        """Legacy API shape, preserved so existing clients keep working.

        ``unit_price``/``total_price`` stay in major units here because the
        existing buyer/seller API returns them that way.
        """
        unit_price = self.unit_price_minor / 100.0
        return {
            "item_id": self.id,
            "sku": self.sku,
            "title": self.title,
            "quantity": self.quantity,
            "unit_price": unit_price,
            "unit_price_minor": self.unit_price_minor,
            "total_price": unit_price * self.quantity,
            "total_price_minor": self.unit_price_minor * self.quantity,
            "returnable": self.returnable,
            "category": self.category,
        }
