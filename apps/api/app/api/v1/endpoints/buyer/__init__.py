from fastapi import APIRouter

from app.api.v1.endpoints.buyer.cases import router as cases_router
from app.api.v1.endpoints.buyer.chat import router as chat_router
from app.api.v1.endpoints.buyer.invites import router as invites_router
from app.api.v1.endpoints.buyer.orders import router as orders_router
from app.api.v1.endpoints.buyer.sellers import router as sellers_router

buyer_router = APIRouter(prefix="/buyer", tags=["Buyer Portal"])
buyer_router.include_router(orders_router)
buyer_router.include_router(cases_router)
buyer_router.include_router(chat_router)

__all__ = ["buyer_router", "sellers_router", "invites_router"]
