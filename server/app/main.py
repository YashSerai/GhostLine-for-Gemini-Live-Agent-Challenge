from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .logging_utils import configure_logging, log_event
from .websocket_gateway import register_websocket_gateway

LOGGER = logging.getLogger("ghostline.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.settings = settings

    log_event(
        LOGGER,
        logging.INFO,
        "app_startup",
        app_name=settings.app_name,
        environment=settings.app_env,
        server_host=settings.server_host,
        server_port=settings.server_port,
        cors_origins=list(settings.cors_origins),
    )

    yield

    log_event(
        LOGGER,
        logging.INFO,
        "app_shutdown",
        app_name=settings.app_name,
        environment=settings.app_env,
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Ghostline Backend",
        description=(
            "Prompt 6 backend scaffold with environment-backed config, health "
            "endpoints, local CORS, and a session WebSocket gateway."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def read_root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "status": "scaffold-ready",
            "environment": settings.app_env,
        }

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.app_name,
        }

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        ready_settings: Settings = (
            app.state.settings if hasattr(app.state, "settings") else settings
        )
        return {
            "status": "ready",
            "service": ready_settings.app_name,
            "environment": ready_settings.app_env,
        }

    register_websocket_gateway(app)
    return app


app = create_app()
