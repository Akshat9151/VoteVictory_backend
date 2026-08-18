import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger("app.error_handler")


def format_error_response(
    code: str,
    message: str,
    request: Request,
    status_code: int = 400,
    details: Dict[str, Any] = None
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown-request-id")
    response_payload = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        },
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return JSONResponse(status_code=status_code, content=response_payload)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(
            f"AppException: code={exc.code} message={exc.message} status={exc.status_code} "
            f"req_id={getattr(request.state, 'request_id', 'unknown')}"
        )
        return format_error_response(
            code=exc.code,
            message=exc.message,
            request=request,
            status_code=exc.status_code,
            details=exc.details
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = {}
        for err in exc.errors():
            loc = ".".join(str(item) for item in err.get("loc", []))
            details[loc] = err.get("msg", "Invalid value")

        logger.warning(f"ValidationError: {details} req_id={getattr(request.state, 'request_id', 'unknown')}")
        return format_error_response(
            code="VALIDATION_ERROR",
            message="Request body or parameter validation failed.",
            request=request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code_map = {
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            429: "TOO_MANY_REQUESTS",
            500: "INTERNAL_SERVER_ERROR",
        }
        code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
        return format_error_response(
            code=code,
            message=str(exc.detail),
            request=request,
            status_code=exc.status_code
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.error(f"Database IntegrityError: {str(exc)} req_id={getattr(request.state, 'request_id', 'unknown')}")
        return format_error_response(
            code="DATABASE_INTEGRITY_VIOLATION",
            message="Operation failed due to database constraint violation or duplicate record.",
            request=request,
            status_code=status.HTTP_409_CONFLICT,
            details={"db_error": str(exc.orig) if settings.DEBUG and hasattr(exc, "orig") else "Unique constraint violation"}
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"Database Error: {str(exc)} req_id={getattr(request.state, 'request_id', 'unknown')}", exc_info=True)
        return format_error_response(
            code="DATABASE_ERROR",
            message="A database error occurred during request execution.",
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"debug_info": str(exc)} if settings.DEBUG else {}
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled Server Error: {str(exc)} req_id={getattr(request.state, 'request_id', 'unknown')}", exc_info=True)
        return format_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred." if not settings.DEBUG else str(exc),
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"error_type": type(exc).__name__} if settings.DEBUG else {}
        )
