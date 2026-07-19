"""Canonical CardVector batch-level workflow contracts."""

from .exceptions import (
    BatchWorkflowError,
    BatchWorkflowNotFoundError,
    BatchWorkflowPersistenceError,
    DuplicateBatchError,
    InvalidBatchIdError,
    InvalidStatusTransitionError,
)
from .models import (
    BatchWorkflow,
    BatchWorkflowQuery,
    BatchWorkflowResult,
    OverallBatchStatus,
    WorkflowStepStatus,
)
from .repository import (
    BatchWorkflowRepository,
    JsonBatchWorkflowRepository,
    validate_batch_id,
)
from .service import BatchWorkflowService
from .status import LEGAL_TRANSITIONS, validate_transition

__all__ = [
    "BatchWorkflow",
    "BatchWorkflowError",
    "BatchWorkflowNotFoundError",
    "BatchWorkflowPersistenceError",
    "BatchWorkflowQuery",
    "BatchWorkflowRepository",
    "BatchWorkflowResult",
    "BatchWorkflowService",
    "DuplicateBatchError",
    "InvalidBatchIdError",
    "InvalidStatusTransitionError",
    "JsonBatchWorkflowRepository",
    "LEGAL_TRANSITIONS",
    "OverallBatchStatus",
    "WorkflowStepStatus",
    "validate_batch_id",
    "validate_transition",
]
