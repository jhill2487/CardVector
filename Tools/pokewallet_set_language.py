"""Conservative PokéWallet set language scope for CardVector's English-first phase.

The provider set directory does not expose a reliable language field in the
current checkpoint. Known Japanese sets are deferred; unknown sets are held
for review rather than guessed to be English. Never infer language from
the Pokémon card's character names or from English-looking Japanese set names.
"""
import re

ENGLISH_EXACT={
    "delta reign",
    "chaos rising",
    "30th celebration - classic collection",
    "crown zenith",
    "crown zenith: galarian gallery",
    "dragon",
    "deoxys",
    "pokemon go",
    "battle academy",
    "battle academy 2024",
    "trading card game classic",
    "my first battle",
    "trick or trade booster bundle",
    "trick or trade booster bundle 2023",
    "trick or trade booster bundle 2024",
}
ENGLISH_PATTERNS=(
    r"^ME0[1-9]: ",
    r"^ME: (?:Mega Evolution Promo|Ascended Heroes)",
    r"^MEE: Mega Evolution Energies$",
    r"^SV(?:0[1-9]|1[0-9]): ",
    r"^SV: (?!.*(?:Deck Build Box|ex Starter Set|ex Special Set))",
    r"^SVE: ",
    r"^SWSH\d{1,2}: ",
    r"^SWSH: ",
    r"^SM\d{1,2}: ",
    r"^XY\d{1,2}: ",
    r"^BW\d{1,2}: ",
    r"^DP\d{1,2}: ",
    r"^HGSS\d{1,2}: ",
)
JAPANESE_MARKERS=(
    "japanese","ninja spinner","nihil zero","mega dream ex","inferno x",
    "mega brave","mega symphonia","paradigm trigger","battle partners",
    "glory of team rocket","heat wave arena","shiny treasure ex",
    "stellar miracle","super electric breaker","ruler of the black flame",
    "night wanderer","crimson haze","wild force","cyber judge",
    "raging surf","clay burst","snow hazard","triplet beat",
    "scarlet ex","violet ex","vstar universe","lost abyss",
    "incandescent arcana","pokemon card 151","abyss eye",
    "premium deck set","starter set","deck build box","special set",
)
JAPANESE_PREFIXES=(
    r"^(?:M[1-9]|m[1-9][SL]|SV\d+[a-zA-Z]|SV\d+[KMWDP]|S\d+[a-zA-Z]?|SM\d+[a-zA-Z]|s\d+[a-zA-Z]|sp\d+): ",
    r"^M(?:BD|BG): ",
)

def set_language(item):
    name=str(item.get("name") or "").strip()
    lower=name.lower()
    if any(token in lower for token in JAPANESE_MARKERS):
        return "jpn"
    if any(re.search(pattern,name,re.I) for pattern in JAPANESE_PREFIXES):
        return "jpn"
    if lower in ENGLISH_EXACT or any(re.search(pattern,name) for pattern in ENGLISH_PATTERNS):
        return "eng"
    return "und"
