# Single source of truth for company names/aliases used by both the ingestion
# metadata inference (filename heuristics) and the knowledge tool's filter
# normalization. Adding a company means editing ONLY this module.

CANONICAL_COMPANIES: dict[str, str] = {
    "tcs": "TCS",
    "infosys": "Infosys",
    "nimbus": "Nimbus Software",
    "quantalpha": "QuantAlpha Analytics",
    "mercedes": "Mercedes-Benz",
    "accenture": "Accenture",
    "wipro": "Wipro",
}


def normalize_company(raw: str) -> str:
    """Map a user/LLM-provided company string to the canonical indexed value.
    Returns '' when no known company matches (filter is then omitted)."""
    key = raw.strip().lower()
    for frag, canonical in CANONICAL_COMPANIES.items():
        if frag in key:
            return canonical
    return ""
