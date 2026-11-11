from fastapi import APIRouter

from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.buyer import buyer_router, invites_router, sellers_router
from app.api.v1.endpoints.files import router as files_router
from app.api.v1.endpoints.files import uploads_router
from app.api.v1.endpoints.seller import seller_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(files_router)
api_router.include_router(uploads_router)
api_router.include_router(seller_router)
api_router.include_router(buyer_router)
api_router.include_router(sellers_router)
api_router.include_router(invites_router)
