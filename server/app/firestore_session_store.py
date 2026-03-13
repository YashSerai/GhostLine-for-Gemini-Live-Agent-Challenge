"""Firestore-backed session persistence for Prompt 37."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from google.cloud import firestore

from .config import FirestoreSettings
from .logging_utils import log_event

LOGGER = logging.getLogger("ghostline.backend.firestore")
_PERSISTENCE_VERSION = "prompt37_firestore_v1"


class FirestoreSessionStore:
    """Persists inspectable session snapshots to Firestore."""

    def __init__(
        self,
        settings: FirestoreSettings,
        *,
        app_name: str,
        app_env: str,
    ) -> None:
        self._settings = settings
        self._app_name = app_name
        self._app_env = app_env
        self._client: firestore.AsyncClient | None = None
        self._disabled_logged = False

    @property
    def is_configured(self) -> bool:
        return self._settings.is_configured

    async def create_session_document(
        self,
        session_id: str,
        snapshot: dict[str, Any],
    ) -> bool:
        document = self._get_document(session_id)
        if document is None:
            return False

        payload = self._build_document(
            session_id=session_id,
            snapshot=snapshot,
            include_created_at=True,
        )
        try:
            await document.set(payload, merge=True)
        except Exception as exc:
            log_event(
                LOGGER,
                logging.ERROR,
                "firestore_session_create_failed",
                session_id=session_id,
                collection=self._settings.collection,
                database=self._settings.database,
                detail=str(exc),
            )
            return False

        log_event(
            LOGGER,
            logging.INFO,
            "firestore_session_created",
            session_id=session_id,
            collection=self._settings.collection,
            database=self._settings.database,
            state=snapshot.get("state"),
        )
        return True

    async def persist_session_snapshot(
        self,
        session_id: str,
        snapshot: dict[str, Any],
    ) -> bool:
        document = self._get_document(session_id)
        if document is None:
            return False

        payload = self._build_document(
            session_id=session_id,
            snapshot=snapshot,
            include_created_at=False,
        )
        try:
            await document.set(payload, merge=True)
        except Exception as exc:
            log_event(
                LOGGER,
                logging.ERROR,
                "firestore_session_persist_failed",
                session_id=session_id,
                collection=self._settings.collection,
                database=self._settings.database,
                detail=str(exc),
            )
            return False

        log_event(
            LOGGER,
            logging.INFO,
            "firestore_session_persisted",
            session_id=session_id,
            collection=self._settings.collection,
            database=self._settings.database,
            state=snapshot.get("state"),
            current_step=snapshot.get("currentStep"),
            task_id=_task_context_value(snapshot.get("currentTaskContext"), "taskId"),
            verification_status=snapshot.get("verificationStatus"),
        )
        return True

    async def close(self) -> None:
        client = self._client
        self._client = None
        if client is None:
            return

        close_method = getattr(client, "close", None)
        if close_method is None:
            return

        result = close_method()
        if hasattr(result, "__await__"):
            await result

    def _get_document(self, session_id: str):
        if not self.is_configured:
            if not self._disabled_logged:
                self._disabled_logged = True
                log_event(
                    LOGGER,
                    logging.WARNING,
                    "firestore_session_store_disabled",
                    reason="missing_firestore_configuration",
                    collection=self._settings.collection,
                    database=self._settings.database,
                )
            return None

        if self._client is None:
            self._client = firestore.AsyncClient(
                project=self._settings.project,
                database=self._settings.database,
            )

        return self._client.collection(self._settings.collection).document(session_id)

    def _build_document(
        self,
        *,
        session_id: str,
        snapshot: dict[str, Any],
        include_created_at: bool,
    ) -> dict[str, Any]:
        now = _utc_now_iso()
        document: dict[str, Any] = {
            "sessionId": session_id,
            "caseId": session_id,
            "product": {
                "name": self._app_name,
                "environment": self._app_env,
                "persistenceVersion": _PERSISTENCE_VERSION,
            },
            "state": snapshot.get("state"),
            "currentStep": snapshot.get("currentStep"),
            "currentPathMode": snapshot.get("currentPathMode"),
            "currentTask": snapshot.get("currentTaskContext"),
            "classification": {
                "label": snapshot.get("classificationLabel"),
                "reason": snapshot.get("classificationReason"),
            },
            "verification": {
                "status": snapshot.get("verificationStatus"),
                "blockReason": snapshot.get("blockReason"),
                "lastVerifiedItem": snapshot.get("lastVerifiedItem"),
            },
            "recovery": {
                "step": snapshot.get("recoveryStep"),
                "attemptCount": snapshot.get("recoveryAttemptCount"),
                "attemptLimit": snapshot.get("recoveryAttemptLimit"),
                "rerouteRequired": snapshot.get("recoveryRerouteRequired"),
            },
            "counters": {
                "swapCount": snapshot.get("swapCount"),
                "interruptionCount": snapshot.get("interruptionCount"),
            },
            "media": {
                "cameraReady": snapshot.get("cameraReady"),
                "microphoneStreaming": snapshot.get("microphoneStreaming"),
                "turnStatus": snapshot.get("turnStatus"),
            },
            "plan": {
                "activeTaskIndex": snapshot.get("activeTaskIndex"),
                "plannedTasks": snapshot.get("plannedTasks") or [],
                "protocolStepMapping": snapshot.get("protocolStepMapping") or [],
            },
            "taskHistory": snapshot.get("taskHistory") or [],
            "verificationHistory": snapshot.get("verificationHistory") or [],
            "transitionHistory": snapshot.get("transitionHistory") or [],
            "transcriptReferences": snapshot.get("transcriptReferences") or [],
            "finalVerdict": snapshot.get("finalVerdict"),
            "caseReport": snapshot.get("caseReport"),
            "endedReason": snapshot.get("endedReason"),
            "proof": {
                "activeTaskId": _task_context_value(
                    snapshot.get("currentTaskContext"),
                    "taskId",
                ),
                "activeTaskName": _task_context_value(
                    snapshot.get("currentTaskContext"),
                    "taskName",
                ),
                "classificationLabel": snapshot.get("classificationLabel"),
                "currentStep": snapshot.get("currentStep"),
                "state": snapshot.get("state"),
                "verificationStatus": snapshot.get("verificationStatus"),
            },
            "timing": {
                "updatedAt": now,
            },
        }
        if include_created_at:
            document["timing"]["createdAt"] = now

        return document


def _task_context_value(task_context: Any, key: str) -> Any:
    if isinstance(task_context, dict):
        return task_context.get(key)
    return None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = ["FirestoreSessionStore"]


