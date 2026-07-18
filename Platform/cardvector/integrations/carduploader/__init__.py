"""CardUploader integration contracts."""

from .inventory import (
    CARDUPLOADER_INVENTORY_COLUMNS,
    CardUploaderInventoryCapabilityUnavailable,
    CardUploaderInventoryService,
    InventoryCapabilities,
    InventoryItem,
    InventoryQuery,
    InventoryResult,
)
from .recognition import CardUploaderRecognitionAdapter, RecognitionHandoff

__all__ = [
    "CARDUPLOADER_INVENTORY_COLUMNS",
    "CardUploaderInventoryCapabilityUnavailable",
    "CardUploaderInventoryService",
    "CardUploaderRecognitionAdapter",
    "InventoryCapabilities",
    "InventoryItem",
    "InventoryQuery",
    "InventoryResult",
    "RecognitionHandoff",
]
