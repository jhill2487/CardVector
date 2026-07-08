from __future__ import annotations

import re

from .models import Listing, ListingIdentity
from .utils import normalize_title


class ListingMatcher:
    """Builds provider lookup identities without depending on one marketplace."""

    def identify(self, listing: Listing) -> ListingIdentity:
        if listing.sku:
            return ListingIdentity(
                lookup_key=listing.sku,
                match_method="sku",
                confidence="high",
                details={"title_key": normalize_title(listing.title)},
            )
        specifics_key = self._item_specifics_key(listing.raw)
        if specifics_key:
            return ListingIdentity(
                lookup_key=specifics_key,
                match_method="item_specifics",
                confidence="medium",
                details={"title_key": normalize_title(listing.title)},
            )
        return ListingIdentity(
            lookup_key=normalize_title(listing.title),
            match_method="title_normalization",
            confidence="low",
            details={"original_title": listing.title},
        )

    def _item_specifics_key(self, row: dict[str, str]) -> str:
        candidates = []
        for key, value in row.items():
            normalized_key = str(key or "").lower()
            if not str(value or "").strip():
                continue
            if any(token in normalized_key for token in ["card name", "set", "card number", "number"]):
                candidates.append(str(value).strip())
        joined = " ".join(candidates)
        joined = re.sub(r"\s+", " ", joined).strip()
        return joined

