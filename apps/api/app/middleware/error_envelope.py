from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import logger


def setup_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            "HTTP %d error on %s: %s (request_id=%s)",
            exc.status_code,
            request.url.path,
            exc.detail,
            request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            "Validation error on %s: %s (request_id=%s)",
            request.url.path,
            exc.errors(),
            request_id,
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters",
                    "request_id": request_id,
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(
            "Unhandled server error on %s (request_id=%s): %s",
            request.url.path,
            request_id,
            str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "request_id": request_id,
                }
            },
        )
