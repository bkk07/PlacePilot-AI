# Scoring helpers for the eval runner. Pure functions — unit-testable without any services.

import re
import unicodedata

DECLINE_MARKERS = (
    "don't have that information",
    "do not have that information",
    "couldn't find",
    "could not find",
    "no relevant",
    "not in the placement documents",
)


def normalize(text: str) -> str:
    """Fold unicode variants (₹-style hyphens, non-breaking spaces, NFKC digits) and
    drop digit-group separators so '35,000' matches '35000' and '35 000'."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"(?<=\d)[,\s\u00a0\u202f](?=\d)", "", text)
    return text


def is_declined(answer: str) -> bool:
    """True when the answer is a grounded decline rather than an attempted answer."""
    low = normalize(answer)
    return any(marker in low for marker in DECLINE_MARKERS)


def correctness(answer: str, expected_contains: list, expect_decline: bool = False) -> bool:
    """Pass if every expectation is satisfied, after unicode normalization.

    Out-of-corpus questions are only "correct" when the answer is an explicit decline.
    Each expectation entry is either a string (must appear) or a list of alternatives
    (any must appear): AND across entries, OR within one.
    """
    if expect_decline:
        return is_declined(answer)
    if not expected_contains:
        return True
    norm = normalize(answer)
    for expected in expected_contains:
        if isinstance(expected, list):
            if not any(normalize(alt) in norm for alt in expected):
                return False
        elif normalize(expected) not in norm:
            return False
    return True


def citation_accuracy(citations: list, expected_source: str | None) -> bool | None:
    """True if the expected source appears among citations. None when not applicable."""
    if expected_source is None:
        return None
    if not citations:
        return False
    for c in citations:
        text = c if isinstance(c, str) else " ".join(str(v) for v in c.values())
        if expected_source.lower() in text.lower():
            return True
    return False


def retrieval_recall(retrieved_sources: list[str], expected_source: str | None) -> bool | None:
    if expected_source is None:
        return None
    return any(expected_source.lower() in s.lower() for s in retrieved_sources)


def hallucination(expect_decline: bool, answer: str, expected_contains: list[str]) -> bool:
    """A hallucination is answering an out-of-corpus question, or fabricating when
    the expected keyword(s) are absent from an in-corpus answer."""
    if expect_decline:
        return not is_declined(answer)
    if expected_contains and is_declined(answer):
        return True
    return False