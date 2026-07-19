from __future__ import annotations

from .exceptions import InvalidStatusTransitionError
from .models import WorkflowStepStatus


LEGAL_TRANSITIONS: dict[WorkflowStepStatus, frozenset[WorkflowStepStatus]] = {
    WorkflowStepStatus.NOT_STARTED: frozenset(
        {
            WorkflowStepStatus.IN_PROGRESS,
            WorkflowStepStatus.COMPLETE,
            WorkflowStepStatus.FAILED,
            WorkflowStepStatus.BLOCKED,
            WorkflowStepStatus.NOT_REQUIRED,
            WorkflowStepStatus.NEEDS_REVIEW,
        }
    ),
    WorkflowStepStatus.IN_PROGRESS: frozenset(
        {
            WorkflowStepStatus.COMPLETE,
            WorkflowStepStatus.FAILED,
            WorkflowStepStatus.BLOCKED,
            WorkflowStepStatus.NEEDS_REVIEW,
        }
    ),
    WorkflowStepStatus.FAILED: frozenset({WorkflowStepStatus.IN_PROGRESS}),
    WorkflowStepStatus.BLOCKED: frozenset(
        {WorkflowStepStatus.IN_PROGRESS, WorkflowStepStatus.FAILED}
    ),
    WorkflowStepStatus.NEEDS_REVIEW: frozenset(
        {
            WorkflowStepStatus.IN_PROGRESS,
            WorkflowStepStatus.COMPLETE,
            WorkflowStepStatus.FAILED,
            WorkflowStepStatus.BLOCKED,
        }
    ),
    WorkflowStepStatus.COMPLETE: frozenset(),
    WorkflowStepStatus.NOT_REQUIRED: frozenset(),
}


def validate_transition(
    step: str,
    current: WorkflowStepStatus,
    target: WorkflowStepStatus,
) -> None:
    if current == target:
        return
    if target not in LEGAL_TRANSITIONS[current]:
        raise InvalidStatusTransitionError(
            f"Invalid {step} transition: {current.value} -> {target.value}"
        )


__all__ = ["LEGAL_TRANSITIONS", "validate_transition"]
