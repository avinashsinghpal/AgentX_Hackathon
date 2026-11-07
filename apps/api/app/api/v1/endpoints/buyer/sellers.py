from fastapi import APIRouter
from sqlalchemy import or_

from app.api.deps import DbSession
from app.models.order import Order
from app.models.seller import Seller, SellerPolicy
from app.schemas.buyer import SellerPublicItem

router = APIRouter(prefix="/sellers", tags=["Public Sellers Directory"])


@router.get("/directory", response_model=list[SellerPublicItem])
def get_sellers_directory(
    db: DbSession,
    q: str | None = None,
) -> list[SellerPublicItem]:
    query = db.query(Seller).filter(Seller.status == "active")

    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Seller.store_name.ilike(search_pattern),
                Seller.store_url.ilike(search_pattern),
            )
        )

    sellers = query.all()
    results: list[SellerPublicItem] = []

    for s in sellers:
        # Find active policy parameters
        active_policy = (
            db.query(SellerPolicy)
            .filter(SellerPolicy.seller_id == s.id, SellerPolicy.is_active.is_(True))
            .first()
        )

        return_window = 7
        auto_approve_max = 2000.0
        shipping_fee_bearer = "seller"
        categories = ["Apparel", "Footwear", "Electronics", "Accessories"]

        if active_policy and active_policy.parsed_rules:
            rules = active_policy.parsed_rules
            if "returns" in rules and isinstance(rules["returns"], dict):
                return_window = rules["returns"].get("window_days", 7)
                shipping_fee_bearer = rules["returns"].get("return_shipping_paid_by", "seller")
                if "eligible_categories" in rules["returns"]:
                    categories = [c.capitalize() for c in rules["returns"]["eligible_categories"]]
            if "refunds" in rules and isinstance(rules["refunds"], dict):
                auto_approve_max = float(rules["refunds"].get("auto_approve_max_amount", 2000.0))

        orders_count = db.query(Order).filter(Order.seller_id == s.id).count()

        results.append(
            SellerPublicItem(
                id=s.id,
                store_name=s.store_name,
                description=f"Verified independent merchant &bull; {s.store_url or 'Official Store'}",
                categories=categories,
                return_window_days=return_window,
                auto_approve_max_amount=auto_approve_max,
                shipping_fee_bearer=shipping_fee_bearer,
                orders_count=orders_count,
            )
        )

    return results
