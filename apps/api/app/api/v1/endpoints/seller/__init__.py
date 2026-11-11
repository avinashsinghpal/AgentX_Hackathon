from fastapi import APIRouter

from app.api.v1.endpoints.seller.approvals import router as approvals_router
from app.api.v1.endpoints.seller.customers import router as customers_router
from app.api.v1.endpoints.seller.metrics import router as metrics_router
from app.api.v1.endpoints.seller.onboarding import router as onboarding_router
from app.api.v1.endpoints.seller.operations import router as operations_router
from app.api.v1.endpoints.seller.orders import router as orders_router
from app.api.v1.endpoints.seller.policies import router as policies_router

seller_router = APIRouter(prefix="/seller")
seller_router.include_router(onboarding_router)
seller_router.include_router(operations_router)
seller_router.include_router(policies_router)
seller_router.include_router(approvals_router)
seller_router.include_router(customers_router)
seller_router.include_router(orders_router)

seller_router.include_router(metrics_router)

__all__ = ["seller_router"]
