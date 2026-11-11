"""Explicit workflow states for buyer resolution cases.

These states are intentionally separate from the existing case status values so
existing API contracts remain stable.  They provide a validated transition layer
for orchestration and recovery.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class InvalidWorkflowTransition(ValueError):
    """Raised when a requested workflow transition is not allowed."""



class WorkflowState(StrEnum):
    INTAKE = "intake"
    CLARIFICATION_REQUIRED = "clarification_required"
    INVESTIGATION = "investigation"
    DECISION_PENDING = "decision_pending"
    APPROVAL_PENDING = "approval_pending"
    ACTION_EXECUTION = "action_execution"
    VERIFICATION = "verification"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    FAILED_RETRYABLE = "failed_retryable"


VALID_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.INTAKE: {WorkflowState.CLARIFICATION_REQUIRED, WorkflowState.INVESTIGATION},
    WorkflowState.CLARIFICATION_REQUIRED: {WorkflowState.INTAKE, WorkflowState.INVESTIGATION},
    WorkflowState.INVESTIGATION: {WorkflowState.DECISION_PENDING},
    WorkflowState.DECISION_PENDING: {
        WorkflowState.APPROVAL_PENDING,
        WorkflowState.ACTION_EXECUTION,
        WorkflowState.ESCALATED,
        WorkflowState.RESOLVED,
    },
    WorkflowState.APPROVAL_PENDING: {WorkflowState.ACTION_EXECUTION, WorkflowState.ESCALATED},
    WorkflowState.ACTION_EXECUTION: {WorkflowState.VERIFICATION, WorkflowState.FAILED_RETRYABLE},
    WorkflowState.VERIFICATION: {WorkflowState.RESOLVED, WorkflowState.FAILED_RETRYABLE, WorkflowState.ESCALATED},
    WorkflowState.FAILED_RETRYABLE: {WorkflowState.INVESTIGATION, WorkflowState.DECISION_PENDING},
    WorkflowState.RESOLVED: set(),
    WorkflowState.ESCALATED: set(),
}


def can_transition(current: WorkflowState, target: WorkflowState) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())


def workflow_state_for_status(status: str) -> WorkflowState:
    """Map a legacy case status to the closest explicit workflow state."""
    mapping = {
        "open": WorkflowState.INTAKE,
        "investigating": WorkflowState.INVESTIGATION,
        "pending_approval": WorkflowState.APPROVAL_PENDING,
        "resolved": WorkflowState.RESOLVED,
        "rejected": WorkflowState.RESOLVED,
    }
    return mapping.get(status, WorkflowState.INTAKE)


def current_workflow_state(case: Any) -> WorkflowState:
    value = getattr(case, "workflow_state", None)
    if value is None:
        return workflow_state_for_status(getattr(case, "status", "open"))
    try:
        return WorkflowState(value)
    except ValueError:
        return workflow_state_for_status(getattr(case, "status", "open"))


def transition_workflow(case: Any, target: WorkflowState | str, *, allow_same: bool = True) -> WorkflowState:
    """Validate and apply a workflow transition to a case-like object."""
    target_state = WorkflowState(target)
    current = current_workflow_state(case)
    if current != target_state and not can_transition(current, target_state):
        raise InvalidWorkflowTransition(
            f"Cannot transition workflow from {current.value} to {target_state.value}"
        )
    if hasattr(case, "workflow_state"):
        case.workflow_state = target_state.value
    return target_state
