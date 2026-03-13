"""Minimal .env loading for the monorepo without adding extra dependencies."""

from __future__ import annotations

from pathlib import Path
import os

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SERVER_ROOT = Path(__file__).resolve().parents[1]
_LOADED = False


def _parse_env_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None

    if line.startswith("export "):
        line = line[7:].strip()

    if "=" not in line:
        return None

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()

    if not key:
        return None

    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
        value = value[1:-1]
    else:
        value = value.split(" #", 1)[0].strip()

    return key, value


def _apply_env_file(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(raw_line)
        if parsed is None:
            continue

        key, value = parsed
        os.environ.setdefault(key, value)


def _resolve_repo_relative_path(raw_value: str) -> str:
    path = Path(raw_value)
    if path.is_absolute():
        return str(path)

    candidates = (
        _REPO_ROOT / path,
        _SERVER_ROOT / path,
        Path.cwd() / path,
    )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())

    return str((_REPO_ROOT / path).resolve())


def load_repo_env() -> None:
    global _LOADED

    if _LOADED:
        return

    for candidate in (_REPO_ROOT / ".env", _SERVER_ROOT / ".env"):
        if candidate.is_file():
            _apply_env_file(candidate)
            break

    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if credentials_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _resolve_repo_relative_path(
            credentials_path
        )

    _LOADED = True
