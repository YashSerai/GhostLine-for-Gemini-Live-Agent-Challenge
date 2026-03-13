import type {
  SessionPlannedTaskEntry,
  SessionStateSnapshot,
  SessionTaskHistoryEntry,
} from "../session/useSessionState";

export const EXPECTED_DEMO_TASK_IDS = ["T1", "T2", "T3", "T4", "T6", "T7"] as const;

type HarnessStatus = "pending" | "active" | "passed" | "failed";
type TaskProgressStatus = "pending" | "active" | "complete" | "issue";

export interface DemoHarnessCheck {
  detail: string;
  label: string;
  status: HarnessStatus;
}

export interface DemoHarnessTaskProgress {
  detail: string;
  status: TaskProgressStatus;
  taskId: string;
  taskName: string;
}

export interface DemoHarnessSnapshot {
  checks: DemoHarnessCheck[];
  summary: string;
  taskProgress: DemoHarnessTaskProgress[];
}

function isExpectedDemoPath(plannedTasks: readonly SessionPlannedTaskEntry[]): boolean {
  const plannedIds = plannedTasks.map((task) => task.taskId);
  return (
    plannedIds.length === EXPECTED_DEMO_TASK_IDS.length &&
    plannedIds.every((taskId, index) => taskId === EXPECTED_DEMO_TASK_IDS[index])
  );
}

function buildPathCheck(plannedTasks: readonly SessionPlannedTaskEntry[]): DemoHarnessCheck {
  if (plannedTasks.length === 0) {
    return {
      label: "Fixed demo path",
      status: "pending",
      detail: "Waiting for the demo planner to publish the fixed rehearsal sequence.",
    };
  }

  if (!isExpectedDemoPath(plannedTasks)) {
    return {
      label: "Fixed demo path",
      status: "failed",
      detail: `Expected ${EXPECTED_DEMO_TASK_IDS.join(" -> ")} but received ${plannedTasks.map((task) => task.taskId).join(" -> ")}.`,
    };
  }

  return {
    label: "Fixed demo path",
    status: "passed",
    detail: plannedTasks.map((task) => task.taskId).join(" -> "),
  };
}

function buildBargeInCheck(sessionState: SessionStateSnapshot): DemoHarnessCheck {
  const status = sessionState.demoBargeIn?.status ?? "idle";

  if (status === "restated") {
    return {
      label: "Controlled barge-in",
      status: "passed",
      detail:
        sessionState.demoBargeIn?.matchedTranscript ??
        "Rehearsed interruption triggered and the restatement completed.",
    };
  }

  if (status === "armed" || status === "triggered") {
    return {
      label: "Controlled barge-in",
      status: "active",
      detail:
        status === "armed"
          ? "Cue is armed. Interrupt on the scripted line to validate Prompt 45."
          : "Interruption fired. Waiting for the shorter restatement to complete.",
    };
  }

  return {
    label: "Controlled barge-in",
    status: "pending",
    detail:
      sessionState.demoBargeIn?.targetLine ??
      "Waiting for the scripted interruption beat.",
  };
}

function buildRecoveryCheck(sessionState: SessionStateSnapshot): DemoHarnessCheck {
  const status = sessionState.demoNearFailure?.status ?? "idle";

  if (status === "recovered") {
    return {
      label: "Near-failure recovery beat",
      status: "passed",
      detail: `${sessionState.demoNearFailure?.taskId ?? "T3"} recovered after the scripted failure.`,
    };
  }

  if (status === "failed_once") {
    return {
      label: "Near-failure recovery beat",
      status: "active",
      detail: `${sessionState.demoNearFailure?.failureType?.replace(/_/g, " ") ?? "temporary low light"} triggered. Run the second verification attempt now.`,
    };
  }

  return {
    label: "Near-failure recovery beat",
    status: "pending",
    detail: `${sessionState.demoNearFailure?.taskId ?? "T3"} has not hit the scripted demo failure yet.`,
  };
}

function buildCaseReportCheck(sessionState: SessionStateSnapshot): DemoHarnessCheck {
  if (sessionState.caseReport !== null) {
    return {
      label: "Final case report",
      status: "passed",
      detail: `${sessionState.caseReport.caseId} / ${sessionState.caseReport.finalVerdict}`,
    };
  }

  if (
    sessionState.state === "completed" ||
    sessionState.state === "case_report" ||
    sessionState.state === "ended"
  ) {
    return {
      label: "Final case report",
      status: "active",
      detail: "Session reached the closing states. Waiting for the report artifact to render.",
    };
  }

  return {
    label: "Final case report",
    status: "pending",
    detail: "Complete the scripted path to generate the final report artifact.",
  };
}

function findTaskHistoryEntries(
  taskHistory: readonly SessionTaskHistoryEntry[],
  taskId: string,
): readonly SessionTaskHistoryEntry[] {
  return taskHistory.filter((entry) => entry.taskId === taskId);
}

function buildTaskProgress(
  sessionState: SessionStateSnapshot,
  plannedTasks: readonly SessionPlannedTaskEntry[],
): DemoHarnessTaskProgress[] {
  const sourceTasks =
    plannedTasks.length > 0
      ? plannedTasks
      : EXPECTED_DEMO_TASK_IDS.map((taskId) => ({
          taskId,
          taskName: taskId,
          taskRoleCategory: "unknown",
          taskTier: 0,
        }));

  return sourceTasks.map((task, index) => {
    const reportTask =
      sessionState.caseReport?.tasks.find((entry) => entry.taskId === task.taskId) ?? null;
    const history = findTaskHistoryEntries(sessionState.taskHistory, task.taskId);
    const hasConfirmedHistory = history.some(
      (entry) => entry.outcome === "confirmed" || entry.outcome === "user_confirmed_only",
    );
    const hasIssueHistory = history.some(
      (entry) => entry.outcome === "unconfirmed" || entry.outcome === "partial_handling",
    );

    if (reportTask !== null) {
      if (reportTask.outcome === "confirmed" || reportTask.outcome === "user_confirmed_only") {
        return {
          taskId: task.taskId,
          taskName: task.taskName,
          status: "complete",
          detail: reportTask.outcome.replace(/_/g, " "),
        };
      }

      return {
        taskId: task.taskId,
        taskName: task.taskName,
        status: "issue",
        detail: reportTask.outcome.replace(/_/g, " "),
      };
    }

    if (sessionState.currentTaskContext?.taskId === task.taskId) {
      return {
        taskId: task.taskId,
        taskName: task.taskName,
        status: "active",
        detail: sessionState.currentTaskContext.taskName ?? "Active task",
      };
    }

    if (hasConfirmedHistory || ((sessionState.activeTaskIndex ?? -1) > index && !hasIssueHistory)) {
      return {
        taskId: task.taskId,
        taskName: task.taskName,
        status: "complete",
        detail: "Completed during the current rehearsal take.",
      };
    }

    if (hasIssueHistory) {
      return {
        taskId: task.taskId,
        taskName: task.taskName,
        status: "issue",
        detail: "This task hit a recovery or unconfirmed state during rehearsal.",
      };
    }

    return {
      taskId: task.taskId,
      taskName: task.taskName,
      status: "pending",
      detail: "Not reached yet.",
    };
  });
}

export function buildDemoRehearsalHarnessSnapshot(
  sessionState: SessionStateSnapshot,
): DemoHarnessSnapshot {
  const plannedTasks = sessionState.plannedTasks;
  const checks = [
    buildPathCheck(plannedTasks),
    buildBargeInCheck(sessionState),
    buildRecoveryCheck(sessionState),
    buildCaseReportCheck(sessionState),
  ];
  const passedCount = checks.filter((check) => check.status === "passed").length;

  return {
    checks,
    summary: `${passedCount} of ${checks.length} rehearsal checks passed in this take.`,
    taskProgress: buildTaskProgress(sessionState, plannedTasks),
  };
}
