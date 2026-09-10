# Extraction + cleaning for placement documents (PDF/TXT).

import re
from pathlib import Path

from pypdf import PdfReader


def extract_pages(path: str | Path) -> list[tuple[int, str]]:
    """Return list of (page_number, text) — page numbers are 1-indexed."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return [
            (i + 1, page.extract_text() or "")
            for i, page in enumerate(reader.pages)
        ]
    return [(1, path.read_text(encoding="utf-8"))]


_HEADER_FOOTER = re.compile(
    r"^(page\s*\d+(\s*/\s*\d+)?|\d+|placement\s+cell.*|confidential.*)\s*$",
    re.IGNORECASE,
)


def clean_text(text: str) -> str:
    """Strip headers/footers, normalize whitespace and bullet artifacts."""
    lines = text.splitlines()
    kept = [ln for ln in lines if not _HEADER_FOOTER.match(ln.strip())]
    text = "\n".join(kept)
    text = re.sub(r"-\n(?=\w)", "", text)  # de-hyphenate line breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_document(path: str | Path) -> list[tuple[int, str]]:
    """Extract + clean, returning (page_number, cleaned_text) per page."""
    return [(page_no, clean_text(text)) for page_no, text in extract_pages(path)]
