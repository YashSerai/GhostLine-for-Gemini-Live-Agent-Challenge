"""Environment-backed application settings for the Ghostline backend."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os

from .env_loader import load_repo_env

load_repo_env()

_VALID_VERIFICATION_RESULTS = frozenset(
    {"confirmed", "unconfirmed", "user_confirmed_only"}
)


def _parse_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_verification_result(value: str | None, *, default: str) -> str:
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in _VALID_VERIFICATION_RESULTS:
        return normalized
    return default


def _derive_local_client_origins(client_host: str, client_port: int) -> tuple[str, ...]:
    origins = {f"http://{client_host}:{client_port}"}

    if client_host == "localhost":
        origins.add(f"http://127.0.0.1:{client_port}")
    elif client_host == "127.0.0.1":
        origins.add(f"http://localhost:{client_port}")

    return tuple(sorted(origins))


def _is_cloud_run_runtime() -> bool:
    return bool(os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_SERVICE"))


def _default_server_host() -> str:
    if _is_cloud_run_runtime():
        return "0.0.0.0"
    return "127.0.0.1"


def _default_server_port() -> int:
    for key in ("SERVER_PORT", "PORT"):
        value = os.getenv(key)
        if value and value.strip():
            return int(value)
    return 8000


@dataclass(frozen=True)
class GeminiLiveSettings:
    project: str
    location: str
    model: str
    credentials_path: str | None
    voice_name: str | None
    voice_language_code: str | None
    input_audio_transcription_enabled: bool
    output_audio_transcription_enabled: bool

    @property
    def is_configured(self) -> bool:
        return bool(self.project and self.location and self.model)


@dataclass(frozen=True)
class MockVerificationSettings:
    enabled: bool
    force_failure: bool
    tier1_result: str
    tier2_result: str
    tier3_result: str
    unknown_tier_result: str


@dataclass(frozen=True)
class DemoModeSettings:
    enabled_by_default: bool


@dataclass(frozen=True)
class FirestoreSettings:
    project: str
    database: str
    collection: str
    credentials_path: str | None

    @property
    def is_configured(self) -> bool:
        return bool(self.project and self.collection)


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    log_level: str
    server_host: str
    server_port: int
    client_host: str
    client_port: int
    cors_origins: tuple[str, ...]
    gemini_live: GeminiLiveSettings
    mock_verification: MockVerificationSettings
    demo_mode: DemoModeSettings
    firestore: FirestoreSettings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_name = os.getenv("APP_NAME", "ghostline")
    app_env = os.getenv("APP_ENV", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    server_host = os.getenv("SERVER_HOST", _default_server_host())
    server_port = _default_server_port()
    client_host = os.getenv("CLIENT_HOST", "127.0.0.1")
    client_port = int(os.getenv("CLIENT_PORT", "5173"))

    cors_origins_value = os.getenv("SERVER_CORS_ORIGINS", "")
    if cors_origins_value.strip():
        cors_origins = _parse_csv(cors_origins_value)
    else:
        cors_origins = _derive_local_client_origins(client_host, client_port)

    gemini_live = GeminiLiveSettings(
        project=os.getenv("GOOGLE_CLOUD_PROJECT", "").strip(),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1").strip()
        or "us-central1",
        model=os.getenv(
            "VERTEX_AI_MODEL",
            "gemini-live-2.5-flash-native-audio",
        ).strip()
        or "gemini-live-2.5-flash-native-audio",
        credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        or None,
        voice_name=os.getenv("GEMINI_LIVE_VOICE_NAME", "").strip() or None,
        voice_language_code=os.getenv(
            "GEMINI_LIVE_VOICE_LANGUAGE_CODE", ""
        ).strip()
        or None,
        input_audio_transcription_enabled=_parse_bool(
            os.getenv("GEMINI_LIVE_INPUT_TRANSCRIPTION"),
            default=True,
        ),
        output_audio_transcription_enabled=_parse_bool(
            os.getenv("GEMINI_LIVE_OUTPUT_TRANSCRIPTION"),
            default=True,
        ),
    )
    mock_verification = MockVerificationSettings(
        enabled=_parse_bool(
            os.getenv("MOCK_VERIFICATION_ENABLED"),
            default=False,
        ),
        force_failure=_parse_bool(
            os.getenv("MOCK_VERIFICATION_FORCE_FAILURE"),
            default=False,
        ),
        tier1_result=_parse_verification_result(
            os.getenv("MOCK_VERIFICATION_TIER1_RESULT"),
            default="confirmed",
        ),
        tier2_result=_parse_verification_result(
            os.getenv("MOCK_VERIFICATION_TIER2_RESULT"),
            default="user_confirmed_only",
        ),
        tier3_result=_parse_verification_result(
            os.getenv("MOCK_VERIFICATION_TIER3_RESULT"),
            default="user_confirmed_only",
        ),
        unknown_tier_result=_parse_verification_result(
            os.getenv("MOCK_VERIFICATION_UNKNOWN_TIER_RESULT"),
            default="user_confirmed_only",
        ),
    )
    demo_mode = DemoModeSettings(
        enabled_by_default=_parse_bool(
            os.getenv("DEMO_MODE_DEFAULT"),
            default=False,
        ),
    )
    firestore = FirestoreSettings(
        project=os.getenv("GOOGLE_CLOUD_PROJECT", "").strip(),
        database=os.getenv("FIRESTORE_DATABASE", "(default)").strip() or "(default)",
        collection=(
            os.getenv("FIRESTORE_SESSIONS_COLLECTION", "ghostline_sessions").strip()
            or "ghostline_sessions"
        ),
        credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        or None,
    )

    return Settings(
        app_name=app_name,
        app_env=app_env,
        log_level=log_level,
        server_host=server_host,
        server_port=server_port,
        client_host=client_host,
        client_port=client_port,
        cors_origins=cors_origins,
        gemini_live=gemini_live,
        mock_verification=mock_verification,
        demo_mode=demo_mode,
        firestore=firestore,
    )
