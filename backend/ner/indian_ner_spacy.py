from __future__ import annotations

import re
from typing import Any, Dict, List

INDIAN_RULER_PATTERNS = [
    {"label": "PAN", "pattern": [{"TEXT": {"REGEX": "^[A-Z]{5}[0-9]{4}[A-Z]$"}}]},
    {"label": "AADHAAR", "pattern": [{"TEXT": {"REGEX": "^\\d{4}\\s\\d{4}\\s\\d{4}$"}}]},
    {"label": "AADHAAR", "pattern": [{"TEXT": {"REGEX": "^\\d{12}$"}}]},
    {"label": "GSTIN", "pattern": [{"TEXT": {"REGEX": "^\\d{2}[A-Z]{5}\\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"}}]},
    {"label": "IFSC", "pattern": [{"TEXT": {"REGEX": "^[A-Z]{4}0[A-Z0-9]{6}$"}}]},
    {"label": "PIN", "pattern": [{"TEXT": {"REGEX": "^\\d{6}$"}}]},
    {"label": "VPA", "pattern": [{"TEXT": {"REGEX": "^[\\w.-]+@[\\w.-]+$"}}]},
    {"label": "DL", "pattern": [{"TEXT": {"REGEX": "^[A-Z]{2}\\d{2}(?:19|20)\\d{7}$"}}]},
    {"label": "PASSPORT", "pattern": [{"TEXT": {"REGEX": "^[A-Z]\\d{7}$"}}]},
]

CITY_ALIASES = {
    "bangalore": "bengaluru", "bombay": "mumbai", "calcutta": "kolkata",
    "madras": "chennai", "poona": "pune", "banaras": "varanasi",
    "mysore": "mysuru", "mangalore": "mangaluru", "hubli": "hubballi",
    "gurgaon": "gurugram", "baroda": "vadodara", "allahabad": "prayagraj",
    "cochin": "kochi", "trivandrum": "thiruvananthapuram", "tanjore": "thanjavur",
    "trichy": "tiruchirappalli", "simla": "shimla", "cannanore": "kannur",
    "bellary": "ballari", "calicut": "kozhikode", "trichur": "thrissur",
    "quilon": "kollam", "salem": "selam", "tirupathi": "tirupati",
    "pondicherry": "puducherry", "coimbatore": "kovai",
    "vizag": "visakhapatnam", "vishakhapatnam": "visakhapatnam",
}


def normalize_city(city: str) -> str:
    return CITY_ALIASES.get(city.lower().strip(), city.lower().strip())


def add_entity_ruler(nlp) -> Any | None:
    try:
        ruler = nlp.add_pipe("entity_ruler", before="ner")
        ruler.add_patterns(INDIAN_RULER_PATTERNS)
        return ruler
    except Exception:
        try:
            from spacy.pipeline import EntityRuler
            ruler = EntityRuler(nlp, before="ner")
            ruler.add_patterns(INDIAN_RULER_PATTERNS)
            nlp.add_pipe(ruler, before="ner")
            return ruler
        except Exception:
            return None


def normalize_address_cities(address: str) -> str:
    result = address.lower()
    for alias, canonical in CITY_ALIASES.items():
        result = re.sub(r'\b' + re.escape(alias) + r'\b', canonical, result)
    return result
