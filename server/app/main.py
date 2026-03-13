from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .gemini_live import GeminiLiveSessionManager
from .flavor_text_state_model import FlavorTextStateModel
from .incident_classification import IncidentClassificationStore
from .logging_utils import configure_logging, log_event
from .mock_verification import MockVerificationEngine
from .real_verification import RealVerificationEngine
from .verification_engine import VerificationEngine
from .websocket_gateway import register_websocket_gateway

LOGGER = logging.getLogger("ghostline.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.settings = settings
    app.state.gemini_live_session_manager = GeminiLiveSessionManager(
        settings.gemini_live
    )
    app.state.incident_classification_store = IncidentClassificationStore()
    app.state.flavor_text_state_model = FlavorTextStateModel()
    app.state.verification_engine = (
        MockVerificationEngine(settings.mock_verification)
        if settings.mock_verification.enabled
        else RealVerificationEngine()
    )

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
    log_event(
        LOGGER,
        logging.INFO,
        "gemini_live_manager_ready",
        configured=settings.gemini_live.is_configured,
        credentials_configured=bool(settings.gemini_live.credentials_path),
        project=settings.gemini_live.project or None,
        location=settings.gemini_live.location,
        model=settings.gemini_live.model,
        input_audio_transcription=settings.gemini_live.input_audio_transcription_enabled,
        output_audio_transcription=settings.gemini_live.output_audio_transcription_enabled,
    )
    log_event(
        LOGGER,
        logging.WARNING if settings.mock_verification.enabled else logging.INFO,
        "verification_engine_ready",
        verification_engine_kind=("mock" if settings.mock_verification.enabled else "real"),
        mock_mode_enabled=settings.mock_verification.enabled,
        mock_force_failure=settings.mock_verification.force_failure,
        mock_tier1_result=settings.mock_verification.tier1_result,
        mock_tier2_result=settings.mock_verification.tier2_result,
        mock_tier3_result=settings.mock_verification.tier3_result,
        mock_unknown_tier_result=settings.mock_verification.unknown_tier_result,
    )
    log_event(
        LOGGER,
        logging.INFO,
        "incident_classifier_ready",
        primary_label_store="in_memory_session_store",
        supported_labels=[
            "threshold disturbance",
            "reflective anomaly",
            "low-visibility anchor",
            "passive echo",
            "reactive presence",
        ],
    )
    log_event(
        LOGGER,
        logging.INFO,
        "flavor_text_state_model_ready",
        supported_states=[
            "opening_intake",
            "camera_request",
            "task_assignment",
            "task_in_progress",
            "verification_pending",
            "verification_success",
            "verification_failure",
            "substitution",
            "escalation",
            "final_closure",
        ],
        selection_mode="bounded_deterministic_rotation",
    )

    yield

    gemini_live_session_manager: GeminiLiveSessionManager | None = getattr(
        app.state,
        "gemini_live_session_manager",
        None,
    )
    if gemini_live_session_manager is not None:
        await gemini_live_session_manager.shutdown()

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
            "Ghostline backend with health endpoints, local CORS, a session "
            "WebSocket gateway, environment-loaded Gemini Live integration, a "
            "bounded Ready-to-Verify flow, an isolated mock verifier, and a "
            "real task-aware verification engine."
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
        verification_engine: VerificationEngine | None = getattr(
            app.state,
            "verification_engine",
            None,
        )
        verification_engine_kind = (
            "mock"
            if ready_settings.mock_verification.enabled
            else ("real" if verification_engine is not None else "none")
        )
        return {
            "status": "ready",
            "service": ready_settings.app_name,
            "environment": ready_settings.app_env,
            "mockVerificationEnabled": str(ready_settings.mock_verification.enabled).lower(),
            "verificationEngine": verification_engine_kind,
        }

    register_websocket_gateway(app)
    return app


app = create_app()


