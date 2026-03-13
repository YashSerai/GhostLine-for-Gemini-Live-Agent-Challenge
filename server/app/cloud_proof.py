"""Operational helpers for cloud-proof session lookup and recording support."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

_EXPECTED_LOG_EVENTS = (
    "session_started",
    "gemini_live_session_created",
    "firestore_session_created",
    "firestore_session_persisted",
    "case_report_generated",
)


@dataclass
class CloudProofSessionRecord:
    sessionId: str
    state: str | None = None
    currentStep: str | None = None
    taskId: str | None = None
    verificationStatus: str | None = None
    firestoreDocumentPath: str | None = None
    logQueryHint: str | None = None
    startedAt: str | None = None
    updatedAt: str | None = None
    endedAt: str | None = None
    active: bool = True
    endedReason: str | None = None


class CloudProofSessionRegistry:
    """Tracks the latest session identifiers and lookup hints for proof recording."""

    def __init__(
        self,
        *,
        service_name: str | None,
        project: str | None,
        firestore_collection: str | None,
    ) -> None:
        self._service_name = service_name
        self._project = project
        self._firestore_collection = firestore_collection
        self._sessions: dict[str, CloudProofSessionRecord] = {}
        self._last_session_id: str | None = None

    def observe_snapshot(self, session_id: str, payload: dict[str, Any]) -> None:
        record = self._sessions.get(session_id)
        if record is None:
            now = _utc_now_iso()
            record = CloudProofSessionRecord(
                sessionId=session_id,
                startedAt=now,
                updatedAt=now,
                firestoreDocumentPath=self._build_document_path(session_id),
                logQueryHint=self._build_log_query_hint(session_id),
            )
            self._sessions[session_id] = record
        record.state = _string_or_none(payload.get("state"))
        record.currentStep = _string_or_none(payload.get("currentStep"))
        record.taskId = _task_context_value(payload.get("currentTaskContext"), "taskId")
        record.verificationStatus = _string_or_none(payload.get("verificationStatus"))
        record.updatedAt = _utc_now_iso()
        record.active = record.state != "ended"
        if record.state == "ended" and record.endedAt is None:
            record.endedAt = record.updatedAt
        self._last_session_id = session_id

    def end_session(self, session_id: str, *, reason: str | None = None) -> None:
        record = self._sessions.get(session_id)
        if record is None:
            record = CloudProofSessionRecord(
                sessionId=session_id,
                firestoreDocumentPath=self._build_document_path(session_id),
                logQueryHint=self._build_log_query_hint(session_id),
                startedAt=_utc_now_iso(),
                updatedAt=_utc_now_iso(),
            )
            self._sessions[session_id] = record
        record.active = False
        record.endedReason = reason
        record.endedAt = _utc_now_iso()
        record.updatedAt = record.endedAt
        self._last_session_id = session_id

    def build_active_session_payload(self) -> dict[str, Any]:
        active_session = self._select_active_session()
        last_session = self._sessions.get(self._last_session_id) if self._last_session_id else None
        return {
            "serviceName": self._service_name,
            "project": self._project,
            "firestoreCollection": self._firestore_collection,
            "activeSession": asdict(active_session) if active_session is not None else None,
            "lastSession": asdict(last_session) if last_session is not None else None,
            "expectedLogEvents": list(_EXPECTED_LOG_EVENTS),
        }

    def _select_active_session(self) -> CloudProofSessionRecord | None:
        active_records = [record for record in self._sessions.values() if record.active]
        if not active_records:
            return None
        active_records.sort(key=lambda record: record.updatedAt or "", reverse=True)
        return active_records[0]

    def _build_document_path(self, session_id: str) -> str | None:
        if not self._firestore_collection:
            return None
        return f"{self._firestore_collection}/{session_id}"

    def _build_log_query_hint(self, session_id: str) -> str:
        return f'jsonPayload.event="session_started" AND jsonPayload.session_id="{session_id}"'


def _task_context_value(task_context: Any, key: str) -> str | None:
    if isinstance(task_context, dict):
        return _string_or_none(task_context.get(key))
    return None


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = ["CloudProofSessionRegistry"]
