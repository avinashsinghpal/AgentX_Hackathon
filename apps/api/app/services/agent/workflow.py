"""Explicit workflow states for buyer resolution cases.

These states are intentionally separate from the existing case status values so
existing API contracts remain stable.  They provide a validated transition layer
for orchestration and recovery.
"""

from __future__ import annotations

from enum import StrEnum


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
