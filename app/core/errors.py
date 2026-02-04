from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from app.core.exceptions import NilEasyError
from app.schemas.response import ErrorResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

def add_exception_handlers(app: FastAPI):
    """
    Registers exception handlers with the FastAPI app.
    """
    @app.exception_handler(NilEasyError)
    async def nileasy_exception_handler(request: Request, exc: NilEasyError):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.message,
                code=exc.code,
                details=exc.details
            ).model_dump()
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """
        Handles standard HTTP exceptions (404, etc.)
        """
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=str(exc.detail),
                code="HTTP_ERROR",
                details=None
            ).model_dump()
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Handles Pydantic validation errors.
        """
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="Input validation failed",
                code="VALIDATION_ERROR",
                details=exc.errors()  # Pydantic error list
            ).model_dump()
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Catch-all for unhandled exceptions.
        """
        logger.error(
            f"Unhandled exception: {str(exc)}",
            extra={
                "method": request.method,
                "url": str(request.url),
                "client": request.client.host if request.client else "unknown"
            },
            exc_info=True
        )

        message = "An internal error occurred. Please try again later." if settings.is_production else str(exc)
        
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=message,
                code="INTERNAL_ERROR",
                details=None
            ).model_dump()
        )
