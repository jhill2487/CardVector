from __future__ import annotations

import re

from .models import Listing, ListingIdentity
from .utils import normalize_title


RARITY_AND_CONDITION_WORDS = {
    "common", "uncommon", "rare", "super", "secret", "ultra", "double", "illustration",
    "holo", "foil", "reverse", "parallel", "alt", "art", "english", "japanese",
    "nm", "lp", "mp", "hp", "dmg", "mint", "near", "better", "graded",
}


class ListingMatcher:
    """Builds provider lookup identities without depending on one marketplace."""

    def identify(self, listing: Listing) -> ListingIdentity:
        title_identity = self._title_identity(listing.title)
        if listing.sku:
            return ListingIdentity(
                lookup_key=listing.sku,
                match_method="sku",
                confidence="high",
                details={"title_key": normalize_title(listing.title), **title_identity},
            )
        specifics_key = self._item_specifics_key(listing.raw)
        if specifics_key:
            return ListingIdentity(
                lookup_key=specifics_key,
                match_method="item_specifics",
                confidence="medium",
                details={"title_key": normalize_title(listing.title), **title_identity},
            )
        return ListingIdentity(
            lookup_key=normalize_title(listing.title),
            match_method="title_normalization",
            confidence="low",
            details={"original_title": listing.title, **title_identity},
        )

    def _item_specifics_key(self, row: dict[str, str]) -> str:
        candidates = []
        card_name = ""
        set_name = ""
        card_number = ""
        for key, value in row.items():
            normalized_key = str(key or "").lower()
            if not str(value or "").strip():
                continue
            if any(token in normalized_key for token in ["card name", "set", "card number", "number"]):
                candidates.append(str(value).strip())
            if "card name" in normalized_key:
                card_name = str(value).strip()
            elif normalized_key.endswith(":set") or normalized_key == "set":
                set_name = str(value).strip()
            elif "card number" in normalized_key:
                card_number = str(value).strip()
        joined = " ".join(candidates)
        joined = re.sub(r"\s+", " ", joined).strip()
        return joined

    def _title_identity(self, title: str) -> dict[str, str]:
        """Extract enough card identity from an active-listing title for provider lookup.

        eBay active-listing reports often omit card-specific columns. This parser is
        intentionally conservative: it extracts obvious card numbers and uses the text
        before that number as the card name candidate, but leaves uncertain set names
        as supporting evidence rather than authoritative identity.
        """
        raw = str(title or "").strip()
        number = self._find_card_number(raw)
        name = ""
        set_name = ""
        if number:
            prefix, suffix = self._split_around_first(raw, number)
            name = self._clean_name_candidate(prefix)
            set_name = self._clean_set_candidate(suffix)
        if not name:
            name = self._clean_name_candidate(raw)
        query_parts = [part for part in [name, set_name, number] if part]
        return {
            "parsed_card_name": name,
            "parsed_set": set_name,
            "parsed_card_number": number,
            "provider_query": " ".join(query_parts).strip(),
            "title_key": normalize_title(raw),
        }

    def _find_card_number(self, title: str) -> str:
        patterns = [
            r"#?\b[A-Z]{1,5}\s*-?\s*\d{1,5}\b",
            r"#?\b\d{1,5}\s*/\s*\d{1,5}\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, title, flags=re.IGNORECASE)
            if match:
                return match.group(0).replace("#", "").strip()
        return ""

    def _split_around_first(self, title: str, needle: str) -> tuple[str, str]:
        pattern = re.escape(needle)
        match = re.search(pattern, title, flags=re.IGNORECASE)
        if not match:
            return title, ""
        return title[:match.start()], title[match.end():]

    def _clean_name_candidate(self, value: str) -> str:
        text = re.sub(r"[-|]+", " ", str(value or ""))
        words = [word for word in re.split(r"\s+", text.strip()) if word]
        while words and normalize_title(words[-1]) in RARITY_AND_CONDITION_WORDS:
            words.pop()
        return re.sub(r"\s+", " ", " ".join(words)).strip()

    def _clean_set_candidate(self, value: str) -> str:
        text = re.sub(r"[-|]+", " ", str(value or ""))
        words = []
        for word in re.split(r"\s+", text.strip()):
            cleaned = normalize_title(word)
            if cleaned in RARITY_AND_CONDITION_WORDS:
                continue
            words.append(word)
        return re.sub(r"\s+", " ", " ".join(words)).strip()
