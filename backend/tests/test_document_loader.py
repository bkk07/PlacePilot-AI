from app.ai.document_loader import clean_text, extract_pages, load_document


def test_clean_text_strips_headers_footers():
    raw = "Page 1/3\nPlacement Cell\nCGPA of 6.0 or above\nconfidential\n\n\n\nNext section"
    cleaned = clean_text(raw)
    assert "Page 1/3" not in cleaned
    assert "confidential" not in cleaned
    assert "CGPA of 6.0 or above" in cleaned
    assert "Next section" in cleaned
    assert "\n\n\n" not in cleaned


def test_clean_text_normalizes_whitespace_and_hyphensation():
    raw = "inter-\nnational   engineering    college"
    cleaned = clean_text(raw)
    assert "international" in cleaned
    assert "  " not in cleaned


def test_extract_pages_txt(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("hello world", encoding="utf-8")
    pages = extract_pages(f)
    assert pages == [(1, "hello world")]


def test_load_document_txt(tmp_path):
    f = tmp_path / "policy.txt"
    f.write_text("1. Eligibility\nCGPA of 6.0 or above\n\n\n\n2. Registration", encoding="utf-8")
    pages = load_document(f)
    assert pages == [(1, "1. Eligibility\nCGPA of 6.0 or above\n\n2. Registration")]
