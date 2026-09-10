# Text chunker: fixed-size sliding window over cleaned page text.

from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    page_number: int
    metadata: dict = field(default_factory=dict)


def chunk_text(
    pages: list[tuple[int, str]],
    document_id: str,
    metadata: dict,
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[Chunk]:
    """Split pages into overlapping chunks, attaching metadata to every chunk."""
    chunks: list[Chunk] = []
    for page_no, text in pages:
        if not text.strip():
            continue
        start = 0
        while start < len(text):
            end = start + chunk_size
            piece = text[start:end]
            if piece.strip():
                meta = {
                    "document_id": document_id,
                    "page_number": page_no,
                    **metadata,
                }
                chunks.append(Chunk(text=piece.strip(), page_number=page_no, metadata=meta))
            if end >= len(text):
                break
            start = end - overlap
    return chunks
