from __future__ import annotations

import json
from pathlib import Path
import re
from threading import RLock
from typing import Protocol

from .exceptions import (
    BatchWorkflowNotFoundError,
    BatchWorkflowPersistenceError,
    DuplicateBatchError,
    InvalidBatchIdError,
)
from .models import BatchWorkflow


_BATCH_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def validate_batch_id(batch_id: str) -> str:
    value = str(batch_id or "").strip()
    if not value or not _BATCH_ID.fullmatch(value):
        raise InvalidBatchIdError(
            "Batch ID must contain only letters, numbers, periods, underscores, or hyphens."
        )
    return value


class BatchWorkflowRepository(Protocol):
    def create(self, batch: BatchWorkflow) -> BatchWorkflow: ...

    def get(self, batch_id: str) -> BatchWorkflow: ...

    def save(self, batch: BatchWorkflow) -> BatchWorkflow: ...

    def list(self) -> list[BatchWorkflow]: ...


class JsonBatchWorkflowRepository:
    """Atomic local JSON persistence for batch workflow state only."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._lock = RLock()

    def path_for(self, batch_id: str) -> Path:
        return self.root / f"{validate_batch_id(batch_id)}.json"

    def create(self, batch: BatchWorkflow) -> BatchWorkflow:
        path = self.path_for(batch.batch_id)
        with self._lock:
            if path.exists():
                raise DuplicateBatchError(
                    f"Batch workflow already exists: {batch.batch_id}"
                )
            return self._write(path, batch)

    def get(self, batch_id: str) -> BatchWorkflow:
        path = self.path_for(batch_id)
        with self._lock:
            if not path.exists():
                raise BatchWorkflowNotFoundError(
                    f"Batch workflow not found: {batch_id}"
                )
            return self._read(path)

    def save(self, batch: BatchWorkflow) -> BatchWorkflow:
        path = self.path_for(batch.batch_id)
        with self._lock:
            if not path.exists():
                raise BatchWorkflowNotFoundError(
                    f"Batch workflow not found: {batch.batch_id}"
                )
            return self._write(path, batch)

    def list(self) -> list[BatchWorkflow]:
        if not self.root.exists():
            return []
        with self._lock:
            batches = [self._read(path) for path in self.root.glob("*.json")]
        return sorted(batches, key=lambda item: item.updated_at, reverse=True)

    def _read(self, path: Path) -> BatchWorkflow:
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(value, dict):
                raise ValueError("record is not a JSON object")
            return BatchWorkflow.from_dict(value)
        except BatchWorkflowPersistenceError:
            raise
        except Exception as exc:
            raise BatchWorkflowPersistenceError(
                f"Could not read batch workflow {path.name}: {exc}"
            ) from exc

    def _write(self, path: Path, batch: BatchWorkflow) -> BatchWorkflow:
        temp = path.with_suffix(path.suffix + ".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp.write_text(
                json.dumps(batch.to_dict(), indent=2) + "\n",
                encoding="utf-8",
            )
            temp.replace(path)
        except Exception as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise BatchWorkflowPersistenceError(
                f"Could not write batch workflow {path.name}: {exc}"
            ) from exc
        return batch


__all__ = [
    "BatchWorkflowRepository",
    "JsonBatchWorkflowRepository",
    "validate_batch_id",
]
