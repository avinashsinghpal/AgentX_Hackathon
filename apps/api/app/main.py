from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.db.session import engine
from app.middleware.error_envelope import setup_error_handlers
from app.middleware.request_id import RequestIdMiddleware
from app.services.monitor import start_proactive_monitor, stop_proactive_monitor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info("Starting SellerResolve API (ENV=%s)", settings.ENV)
    try:
        start_proactive_monitor()
    except Exception as e:
        logger.warning("Could not start background monitor: %s", e)
    yield
    try:
        stop_proactive_monitor()
    except Exception as e:
        logger.warning("Could not stop background monitor: %s", e)
    logger.info("Shutting down SellerResolve API")


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
    headers_enabled=True,
)

app = FastAPI(
    title="SellerResolve API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url=None,
)


def rate_limit_handler(request: Request, exc: Exception) -> Response:
    return _rate_limit_exceeded_handler(request, exc)  # type: ignore[arg-type]


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Request ID & Standard Error Envelope
app.add_middleware(RequestIdMiddleware)
setup_error_handlers(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(api_router)


@app.get("/healthz")
@app.get("/api/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "env": settings.ENV}


@app.get("/readyz")
@app.get("/api/readyz")
async def readyz() -> dict[str, Any]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        logger.error("Database readiness check failed: %s", exc)
        return {"status": "not_ready", "database": "disconnected"}
