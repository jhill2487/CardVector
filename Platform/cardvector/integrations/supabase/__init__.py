"""Supabase integration adapters for CardVector shared registry data."""

from .registry import (
    CANONICAL_CAPTURE_IMAGES_TABLE,
    CANONICAL_CAPTURE_SESSIONS_TABLE,
    CANONICAL_INVENTORY_RELATIONSHIPS_TABLE,
    CANONICAL_LOCATIONS_TABLE,
    CanonicalCaptureImage,
    CanonicalCaptureSession,
    CanonicalLocation,
    SupabaseRegistryClient,
    SupabaseRegistryError,
    canonical_rows_to_legacy_etb_rows,
    environment_config,
    legacy_status_to_canonical,
)

__all__ = [
    "CANONICAL_CAPTURE_IMAGES_TABLE",
    "CANONICAL_CAPTURE_SESSIONS_TABLE",
    "CANONICAL_INVENTORY_RELATIONSHIPS_TABLE",
    "CANONICAL_LOCATIONS_TABLE",
    "CanonicalCaptureImage",
    "CanonicalCaptureSession",
    "CanonicalLocation",
    "SupabaseRegistryClient",
    "SupabaseRegistryError",
    "canonical_rows_to_legacy_etb_rows",
    "environment_config",
    "legacy_status_to_canonical",
]
