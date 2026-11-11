from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import logger


def serializable_validation_errors(
    errors: Sequence[Any],
) -> list[dict[str, Any]]:
    """Reduce Pydantic errors to JSON-safe fields.

    Pydantic puts the original exception object in ``ctx`` for value errors,
    and the submitted value in ``input``.  Neither is guaranteed to be JSON
    serializable (or desirable to echo back), so keep the location, message and
    error type, and stringify the context.
    """
    details: list[dict[str, Any]] = []
    for error in errors:
        if not isinstance(error, dict):
            continue
        item: dict[str, Any] = {
            "type": error.get("type"),
            "loc": [str(part) for part in error.get("loc", ())],
            "msg": str(error.get("msg", "Invalid value")),
        }
        context = error.get("ctx")
        if isinstance(context, dict):
            item["ctx"] = {key: str(value) for key, value in context.items()}
        details.append(item)
    return details


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
                    "details": serializable_validation_errors(exc.errors()),
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
