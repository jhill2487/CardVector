from __future__ import annotations


class BatchWorkflowError(RuntimeError):
    """Base error for canonical batch-workflow operations."""


class InvalidBatchIdError(BatchWorkflowError):
    """Raised when a batch identifier is missing or unsafe."""


class DuplicateBatchError(BatchWorkflowError):
    """Raised when a batch workflow already exists."""


class BatchWorkflowNotFoundError(BatchWorkflowError):
    """Raised when a batch workflow cannot be found."""


class InvalidStatusTransitionError(BatchWorkflowError):
    """Raised when a workflow step attempts an unsupported transition."""


class BatchWorkflowPersistenceError(BatchWorkflowError):
    """Raised when a batch workflow cannot be read or written."""


__all__ = [
    "BatchWorkflowError",
    "BatchWorkflowNotFoundError",
    "BatchWorkflowPersistenceError",
    "DuplicateBatchError",
    "InvalidBatchIdError",
    "InvalidStatusTransitionError",
]
