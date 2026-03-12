"""Environment-backed application settings for the Ghostline backend."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


def _parse_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _derive_local_client_origins(client_host: str, client_port: int) -> tuple[str, ...]:
    origins = {f"http://{client_host}:{client_port}"}

    if client_host == "localhost":
        origins.add(f"http://127.0.0.1:{client_port}")
    elif client_host == "127.0.0.1":
        origins.add(f"http://localhost:{client_port}")

    return tuple(sorted(origins))


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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_name = os.getenv("APP_NAME", "ghostline")
    app_env = os.getenv("APP_ENV", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    server_host = os.getenv("SERVER_HOST", "127.0.0.1")
    server_port = int(os.getenv("SERVER_PORT", "8000"))
    client_host = os.getenv("CLIENT_HOST", "127.0.0.1")
    client_port = int(os.getenv("CLIENT_PORT", "5173"))

    cors_origins_value = os.getenv("SERVER_CORS_ORIGINS", "")
    if cors_origins_value.strip():
        cors_origins = _parse_csv(cors_origins_value)
    else:
        cors_origins = _derive_local_client_origins(client_host, client_port)

    return Settings(
        app_name=app_name,
        app_env=app_env,
        log_level=log_level,
        server_host=server_host,
        server_port=server_port,
        client_host=client_host,
        client_port=client_port,
        cors_origins=cors_origins,
    )
