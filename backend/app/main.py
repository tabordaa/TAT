"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="TAT API", version="0.1.0")

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

    return app


app = create_app()
