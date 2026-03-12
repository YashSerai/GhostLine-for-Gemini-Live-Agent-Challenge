"""Minimal structured logging helpers for backend infrastructure events."""

from __future__ import annotations

import json
import logging
from typing import Any


class JsonFormatter(logging.Formatter):
    """Formats log records as a single JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }

        event = getattr(record, "event", None)
        if event:
            payload["event"] = event

        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)

        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    app_logger = logging.getLogger("ghostline")
    app_logger.handlers.clear()
    app_logger.setLevel(level.upper())
    app_logger.addHandler(handler)
    app_logger.propagate = False


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    logger.log(level, event, extra={"event": event, "fields": fields})
