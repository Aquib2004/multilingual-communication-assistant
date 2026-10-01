"""Application factory.

A thin entry point. Wiring, middleware, and error handling live here; no
business logic does.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api.routes import health, messages, translations, verification
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger
from app.core.security import new_request_id
from app.db.database import create_all, dispose_engine

logger = get_logger(__name__)

DESCRIPTION = """
An open-source, verification-first assistant for family and community
communication.

The workflow is **BRIDGE**: Begin with purpose, Rewrite plainly, Identify
protected items, Draft with context, Gauge meaning, Escalate when needed.

**This tool never certifies a translation.** For safety, health, legal rights,
discipline, disability services, or emergencies it routes to your
organisation's approved professional translation or interpretation process.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the schema on startup and release connections on shutdown.

    Production deployments should run ``alembic upgrade head`` as a release
    step instead. Creating tables here keeps the zero-infrastructure local
    experience working.
    """
    await create_all()
    logger.info("application started", environment=app.state.settings.app_env)
    yield
    await dispose_engine()
    logger.info("application stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Args:
        settings: Optional settings override. Tests use this to point the app
            at a temporary database and the mock provider.

    Returns:
        The configured :class:`FastAPI` instance.
    """
    active = settings or get_settings()
    configure_logging(active)

    app = FastAPI(
        title="Multilingual Communication Assistant",
        description=DESCRIPTION,
        version=active.version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.state.settings = active

    app.add_middleware(
        CORSMiddleware,
        allow_origins=active.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Attach a request id and log outcome and duration, never content."""
        request_id = new_request_id()
        request.state.request_id = request_id
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "unhandled error",
                request_id=request_id,
                path=request.url.path,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            raise

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return response

    _register_error_handlers(app)
    _register_routes(app, active)
    return app


def _register_routes(app: FastAPI, settings: Settings) -> None:
    """Mount every router under the configured API prefix."""
    prefix = settings.api_v1_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(messages.router, prefix=prefix)
    app.include_router(translations.router, prefix=prefix)
    app.include_router(verification.router, prefix=prefix)


def _error_payload(code: str, message: str, request_id: str) -> dict[str, object]:
    """The standard error envelope."""
    return {"error": {"code": code, "message": message}, "request_id": request_id}


def _register_error_handlers(app: FastAPI) -> None:
    """Map every error to a safe response.

    Technical detail goes to the log; the response carries a stable code and a
    message that is safe to show a user. Stack traces are never returned.
    """

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        request_id = str(getattr(request.state, "request_id", new_request_id()))
        logger.warning("application error", request_id=request_id, code=exc.code)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc.code, exc.message, request_id),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        del exc
        request_id = str(getattr(request.state, "request_id", new_request_id()))
        logger.info("request validation failed", request_id=request_id)
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                "VALIDATION_ERROR",
                "The request body failed validation. Check the highlighted fields.",
                request_id,
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _handle_database(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        request_id = str(getattr(request.state, "request_id", new_request_id()))
        logger.error("database error", request_id=request_id, error=type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content=_error_payload(
                "DATABASE_ERROR",
                "The service could not save your work. Please retry.",
                request_id,
            ),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        request_id = str(getattr(request.state, "request_id", new_request_id()))
        logger.error(
            "unhandled exception",
            request_id=request_id,
            error_type=type(exc).__name__,
            trace_id=str(uuid.uuid4()),
        )
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                "INTERNAL_ERROR",
                "Something went wrong. Your work was not sent. Please try again.",
                request_id,
            ),
        )


app = create_app()
