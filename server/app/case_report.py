"""Case report artifact generation for Prompt 39."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, cast

from .incident_classification import format_incident_label_for_report
from .protocol_planner import ProtocolPlan
from .task_helpers import get_task_by_id

CaseReportTaskOutcome = Literal[
    "confirmed",
    "user_confirmed_only",
    "unverified",
    "skipped",
]
CaseReportVerdict = Literal["secured", "partial", "inconclusive"]
CaseReportTaskOrigin = Literal["planned", "substitute"]
CaseReportTemplateTone = Literal["secured", "partial", "inconclusive"]


@dataclass(frozen=True)
class CaseReportTaskEntry:
    task_id: str
    task_name: str
    protocol_step: str | None
    task_tier: int
    task_role_category: str
    outcome: CaseReportTaskOutcome
    origin: CaseReportTaskOrigin

    def to_payload(self) -> dict[str, Any]:
        return {
            "taskId": self.task_id,
            "taskName": self.task_name,
            "protocolStep": self.protocol_step,
            "taskTier": self.task_tier,
            "taskRoleCategory": self.task_role_category,
            "outcome": self.outcome,
            "origin": self.origin,
        }


@dataclass(frozen=True)
class CaseReportArtifact:
    case_id: str
    session_id: str
    generated_at: str
    incident_classification_label: str
    incident_classification_summary: str
    final_verdict: CaseReportVerdict
    closing_template: dict[str, str]
    tasks: tuple[CaseReportTaskEntry, ...]

    def to_payload(self) -> dict[str, Any]:
        counts = {
            "confirmed": 0,
            "user_confirmed_only": 0,
            "unverified": 0,
            "skipped": 0,
        }
        for task in self.tasks:
            counts[task.outcome] += 1

        return {
            "caseId": self.case_id,
            "sessionId": self.session_id,
            "generatedAt": self.generated_at,
            "incidentClassificationLabel": self.incident_classification_label,
            "incidentClassificationSummary": self.incident_classification_summary,
            "finalVerdict": self.final_verdict,
            "closingTemplate": self.closing_template,
            "tasks": [task.to_payload() for task in self.tasks],
            "counts": counts,
        }


def build_case_report_artifact(
    *,
    session_id: str,
    plan: ProtocolPlan | None,
    active_task_index: int,
    current_task_context: dict[str, Any] | None,
    task_history: list[dict[str, Any]],
    verification_history: list[dict[str, Any]],
    classification_label: str | None,
    generated_at: str | None = None,
    state: str | None = None,
) -> CaseReportArtifact:
    ordered_task_refs = _build_ordered_task_refs(
        plan=plan,
        current_task_context=current_task_context,
        task_history=task_history,
        verification_history=verification_history,
    )
    resolved_outcomes = _build_resolved_outcomes(verification_history)
    reached_task_ids = _build_reached_task_ids(
        current_task_context=current_task_context,
        task_history=task_history,
        verification_history=verification_history,
    )
    current_task_id = _task_context_value(current_task_context, "taskId")
    report_tasks: list[CaseReportTaskEntry] = []

    for ref in ordered_task_refs:
        if ref["taskId"] in resolved_outcomes:
            outcome = resolved_outcomes[ref["taskId"]]
        elif ref["taskId"] == current_task_id:
            outcome = "unverified"
        elif ref["taskId"] in reached_task_ids:
            outcome = "unverified"
        elif _planned_index(ref) > active_task_index and state in {"ended", "case_report", "completed"}:
            outcome = "skipped"
        else:
            outcome = "skipped"

        report_tasks.append(
            CaseReportTaskEntry(
                task_id=ref["taskId"],
                task_name=ref["taskName"],
                protocol_step=cast(str | None, ref.get("protocolStep")),
                task_tier=cast(int, ref["taskTier"]),
                task_role_category=cast(str, ref["taskRoleCategory"]),
                outcome=outcome,
                origin=cast(CaseReportTaskOrigin, ref["origin"]),
            )
        )

    final_verdict = _derive_final_verdict(report_tasks)
    resolved_classification_label = classification_label or "unclassified incident"
    classification_summary = _build_classification_summary(resolved_classification_label)
    closing_template = _build_closing_template(final_verdict)

    return CaseReportArtifact(
        case_id=session_id,
        session_id=session_id,
        generated_at=generated_at or _utc_now_iso(),
        incident_classification_label=resolved_classification_label,
        incident_classification_summary=classification_summary,
        final_verdict=final_verdict,
        closing_template=closing_template,
        tasks=tuple(report_tasks),
    )


def _build_ordered_task_refs(
    *,
    plan: ProtocolPlan | None,
    current_task_context: dict[str, Any] | None,
    task_history: list[dict[str, Any]],
    verification_history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered_refs: list[dict[str, Any]] = []
    seen: set[str] = set()

    if plan is not None:
        assignment_by_task_id = {
            assignment.task_id: assignment for assignment in plan.protocol_step_mapping
        }
        for index, task in enumerate(plan.selected_tasks):
            assignment = assignment_by_task_id.get(task.id)
            ordered_refs.append(
                {
                    "taskId": task.id,
                    "taskName": task.name,
                    "taskTier": task.tier,
                    "taskRoleCategory": task.role_category,
                    "protocolStep": assignment.step if assignment is not None else None,
                    "origin": "planned",
                    "plannedIndex": index,
                }
            )
            seen.add(task.id)

    for source in (*task_history, *verification_history):
        task_id = source.get("taskId")
        if not isinstance(task_id, str) or task_id in seen:
            continue
        task = get_task_by_id(task_id)
        ordered_refs.append(
            {
                "taskId": task.id,
                "taskName": task.name,
                "taskTier": task.tier,
                "taskRoleCategory": task.role_category,
                "protocolStep": _string_or_none(source.get("protocolStep")),
                "origin": "substitute",
                "plannedIndex": len(ordered_refs),
            }
        )
        seen.add(task.id)

    current_task_id = _task_context_value(current_task_context, "taskId")
    if current_task_id is not None and current_task_id not in seen:
        task = get_task_by_id(current_task_id)
        ordered_refs.append(
            {
                "taskId": task.id,
                "taskName": task.name,
                "taskTier": task.tier,
                "taskRoleCategory": task.role_category,
                "protocolStep": _task_context_value(current_task_context, "protocolStep"),
                "origin": "substitute",
                "plannedIndex": len(ordered_refs),
            }
        )

    return ordered_refs


def _build_resolved_outcomes(
    verification_history: list[dict[str, Any]],
) -> dict[str, CaseReportTaskOutcome]:
    resolved: dict[str, CaseReportTaskOutcome] = {}
    for item in verification_history:
        task_id = item.get("taskId")
        status = item.get("status")
        if not isinstance(task_id, str):
            continue
        if status == "confirmed":
            resolved[task_id] = "confirmed"
        elif status == "user_confirmed_only" and resolved.get(task_id) != "confirmed":
            resolved[task_id] = "user_confirmed_only"
    return resolved


def _build_reached_task_ids(
    *,
    current_task_context: dict[str, Any] | None,
    task_history: list[dict[str, Any]],
    verification_history: list[dict[str, Any]],
) -> set[str]:
    reached: set[str] = set()
    current_task_id = _task_context_value(current_task_context, "taskId")
    if current_task_id is not None:
        reached.add(current_task_id)

    for source in (*task_history, *verification_history):
        task_id = source.get("taskId")
        if isinstance(task_id, str):
            reached.add(task_id)

    return reached


def _derive_final_verdict(tasks: list[CaseReportTaskEntry]) -> CaseReportVerdict:
    if not tasks:
        return "inconclusive"

    resolved_count = sum(
        1 for task in tasks if task.outcome in {"confirmed", "user_confirmed_only"}
    )
    unresolved_count = sum(
        1 for task in tasks if task.outcome in {"unverified", "skipped"}
    )

    if resolved_count == 0:
        return "inconclusive"
    if unresolved_count == 0:
        return "secured"
    return "partial"


def _build_closing_template(final_verdict: CaseReportVerdict) -> dict[str, str]:
    if final_verdict == "secured":
        return {
            "heading": "Containment Secured",
            "closingLine": "Containment Desk is marking this incident secured. Keep the final boundary in place until the room settles fully.",
            "tone": "secured",
        }
    if final_verdict == "partial":
        return {
            "heading": "Partial Containment Logged",
            "closingLine": "Containment Desk is logging partial containment. Maintain the stabilized setup and avoid disturbing the room until the residue clears.",
            "tone": "partial",
        }
    return {
        "heading": "Contained For Now",
        "closingLine": "Containment Desk cannot mark this case secured. Hold the room quiet, preserve distance, and treat the incident as contained for now.",
        "tone": "inconclusive",
    }
def _build_classification_summary(classification_label: str) -> str:
    class _ClassificationDecision:
        def __init__(self, display_label: str) -> None:
            self.display_label = display_label

    return format_incident_label_for_report(_ClassificationDecision(classification_label))


def _planned_index(task_ref: dict[str, Any]) -> int:
    value = task_ref.get("plannedIndex")
    if isinstance(value, int):
        return value
    return 0


def _task_context_value(context: dict[str, Any] | None, key: str) -> str | None:
    if isinstance(context, dict):
        return _string_or_none(context.get(key))
    return None


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "CaseReportArtifact",
    "CaseReportTemplateTone",
    "CaseReportTaskEntry",
    "CaseReportTaskOutcome",
    "CaseReportVerdict",
    "build_case_report_artifact",
]









