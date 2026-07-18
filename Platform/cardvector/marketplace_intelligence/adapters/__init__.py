"""Canonical marketplace normalization adapter API.

The proven implementations remain at their historical package path during the
delegation-first migration. These aliases create one approved import surface
without copying provider behavior.
"""

from Platform.Marketplace_Intelligence.marketplace_intelligence.providers import (
    CardUploaderInventoryProvider,
    CardUploaderSalesCacheProvider,
    CompositeProvider,
    MarketProvider,
    NullProvider,
    TCGtrackingProvider,
    build_provider,
)

__all__ = [
    "CardUploaderInventoryProvider",
    "CardUploaderSalesCacheProvider",
    "CompositeProvider",
    "MarketProvider",
    "NullProvider",
    "TCGtrackingProvider",
    "build_provider",
]
