from dataclasses import dataclass
import re

@dataclass(frozen=True)
class CardUploaderIdentity:
    card_name: str
    set_name: str
    card_number: str
    title: str = ""
    language: str = "EN"
    condition: str = "NM"

class IdentityTranslator:
    """Translate CardUploader's canonical identity into provider-specific queries.
    This class MUST NOT attempt to identify cards; it only adapts formatting.
    """

    @staticmethod
    def _base_name(name: str) -> str:
        n = re.sub(r"\([^)]*\)", "", str(name))
        n = re.sub(
            r"\b(cosmos holo|cracked ice holo|reverse holo|reverse foil|holo rare|holofoil|foil)\b",
            "",
            n,
            flags=re.IGNORECASE,
        )
        return " ".join(n.split())

    @staticmethod
    def _number(number: str) -> str:
        m = re.search(r"([A-Za-z]*)(\d+)([A-Za-z]*)(?:/(\d+))?", str(number).replace(" ",""))
        if not m:
            return str(number)
        p,num,s,d=m.groups()
        num=str(int(num))
        return f"{p}{num}{s}" + (f"/{int(d)}" if d else "")

    def tcgtracking(self, identity: CardUploaderIdentity) -> dict:
        return {
            "card_name": self._base_name(identity.card_name),
            "set_name": identity.set_name,
            "card_number": self._number(identity.card_number),
            "language": identity.language,
            "condition": identity.condition,
            "title": identity.title,
        }

    def ebay(self, identity: CardUploaderIdentity) -> dict:
        return {
            "query": " ".join([
                self._base_name(identity.card_name),
                self._number(identity.card_number),
                identity.set_name,
                "Pokemon"
            ]).strip()
        }
