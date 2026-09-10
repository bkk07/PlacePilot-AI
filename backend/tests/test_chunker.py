from app.ai.chunker import Chunk, chunk_text


def test_chunks_have_expected_size_and_overlap():
    text = "word " * 400  # 2000 chars
    chunks = chunk_text([(1, text)], "doc-1", {"company": "X"}, chunk_size=800, overlap=120)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= 800
    assert chunks[0].text[-120:].strip() == chunks[1].text[:120].strip()


def test_metadata_attached_to_every_chunk():
    chunks = chunk_text(
        [(1, "some text " * 100), (2, "more text " * 100)],
        "doc-42",
        {"company": "Nimbus Software", "year": 2026, "document_type": "job_description", "role": "SDE", "source": "jd.txt"},
        chunk_size=500,
        overlap=50,
    )
    assert chunks
    for c in chunks:
        assert c.metadata["document_id"] == "doc-42"
        assert c.metadata["company"] == "Nimbus Software"
        assert c.metadata["year"] == 2026
        assert c.metadata["document_type"] == "job_description"
        assert c.metadata["source"] == "jd.txt"
    assert {c.page_number for c in chunks} == {1, 2}


def test_empty_pages_skipped():
    chunks = chunk_text([(1, ""), (2, "   "), (3, "real content here")], "doc-1", {})
    assert len(chunks) == 1
    assert chunks[0].text == "real content here"


def test_short_text_single_chunk():
    chunks = chunk_text([(1, "tiny")], "doc-1", {}, chunk_size=800, overlap=120)
    assert len(chunks) == 1
    assert isinstance(chunks[0], Chunk)
