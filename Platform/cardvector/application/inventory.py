from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from .runtime import ExecutionContext


class InventoryOperations(Protocol):
    def load_inventory(self, path: str | Path) -> Any: ...

    def search_inventory(self, path: str | Path, query: Any = None) -> Any: ...

    def get_inventory_item(self, path: str | Path, inventory_id: str) -> Any: ...

    def normalize_export_row(self, row: Mapping[str, Any]) -> dict[str, str]: ...

    def normalize_export_rows(
        self,
        rows: list[Mapping[str, Any]],
    ) -> list[dict[str, str]]: ...

    def require_export_columns(self, rows: list[Mapping[str, Any]]) -> None: ...


@dataclass(frozen=True)
class InventoryProjectionDelegates:
    list_locations: Callable[..., list[dict[str, Any]]]
    create_location: Callable[..., dict[str, Any]]
    update_location_status: Callable[..., dict[str, Any]]
    complete_location: Callable[..., dict[str, Any]]
    next_location_code: Callable[..., str]
    resolve_qr: Callable[..., dict[str, Any]]
    format_qr: Callable[[dict[str, Any]], str]


class InventoryApplication:
    """Coordinates CardVector inventory views over CardUploader-owned data."""

    def __init__(
        self,
        inventory: InventoryOperations,
        location_projection: InventoryProjectionDelegates | None = None,
    ) -> None:
        self._inventory = inventory
        self._location_projection = location_projection

    @property
    def capabilities(self) -> Any:
        return getattr(self._inventory, "capabilities", None)

    def load_inventory(
        self,
        path: str | Path,
        context: ExecutionContext | None = None,
    ) -> Any:
        execution = context or ExecutionContext.create()
        execution.cancellation.raise_if_cancelled()
        execution.report("carduploader_inventory_loading")
        result = self._inventory.load_inventory(path)
        execution.publish(
            "inventory.snapshot_loaded",
            provider=str(getattr(result, "provider", "CardUploader")),
            item_count=len(getattr(result, "items", ())),
        )
        return result

    def search_inventory(
        self,
        path: str | Path,
        query: Any = None,
        context: ExecutionContext | None = None,
    ) -> Any:
        execution = context or ExecutionContext.create()
        execution.cancellation.raise_if_cancelled()
        return self._inventory.search_inventory(path, query)

    def get_inventory_item(self, path: str | Path, inventory_id: str) -> Any:
        return self._inventory.get_inventory_item(path, inventory_id)

    def require_export_columns(self, rows: list[Mapping[str, Any]]) -> None:
        self._inventory.require_export_columns(rows)

    def normalize_export_row(self, row: Mapping[str, Any]) -> dict[str, str]:
        return self._inventory.normalize_export_row(row)

    def normalize_export_rows(
        self,
        rows: list[Mapping[str, Any]],
    ) -> list[dict[str, str]]:
        return self._inventory.normalize_export_rows(rows)

    def _projection(self) -> InventoryProjectionDelegates:
        if self._location_projection is None:
            raise RuntimeError("Legacy inventory location projection is not configured.")
        return self._location_projection

    def list_location_projection(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return self._projection().list_locations(*args, **kwargs)

    def create_location_projection(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._projection().create_location(*args, **kwargs)

    def update_location_projection(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self._projection().update_location_status(*args, **kwargs)

    def complete_location_projection(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self._projection().complete_location(*args, **kwargs)

    def next_location_projection_code(self, *args: Any, **kwargs: Any) -> str:
        return self._projection().next_location_code(*args, **kwargs)

    def resolve_location_qr(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._projection().resolve_qr(*args, **kwargs)

    def format_location_qr(self, resolved: dict[str, Any]) -> str:
        return self._projection().format_qr(resolved)


__all__ = [
    "InventoryApplication",
    "InventoryOperations",
    "InventoryProjectionDelegates",
]
