"""FastAPI application entry point."""

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.contracts import router as contracts_router
from app.api.employees import router as employees_router
from app.api.health import router as health_router
from app.api.me import router as me_router
from app.core.config import get_settings

logger = logging.getLogger("tat")


async def _security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    # Responses hold personal data and salaries: browsers and proxies must not
    # keep a copy. Applied to everything so a new endpoint is safe by default.
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


async def _unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    # The details stay in the server log; the client learns nothing internal.
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={"Cache-Control": "no-store"},
    )


def create_app() -> FastAPI:
    # A no-op if the server already configured logging.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    settings = get_settings()
    # The interactive docs describe the whole API to anyone: development only.
    public_docs = settings.environment != "production"

    app = FastAPI(
        title="TAT API",
        version="0.1.0",
        docs_url="/docs" if public_docs else None,
        redoc_url="/redoc" if public_docs else None,
        openapi_url="/openapi.json" if public_docs else None,
    )

    app.middleware("http")(_security_headers)
    app.add_exception_handler(Exception, _unhandled_error)

    app.add_middleware(
        CORSMiddleware,
        # Explicit origins: browsers reject "*" when credentials are allowed.
        allow_origins=settings.cors_origins,
        # Lets the browser send/receive our HttpOnly auth cookie.
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(audit_router)
    # Before employees_router, whose "/{employee_id}" would catch fixed paths.
    app.include_router(contracts_router)
    app.include_router(employees_router)
    app.include_router(me_router)

    return app


app = create_app()
