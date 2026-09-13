# Integration test — requires a running Weaviate (docker start weaviate), the embedding
# model, and an ingested corpus. Skips cleanly when any of those are unavailable (e.g. CI,
# where the heavy sentence-transformers/torch extras are intentionally not installed).

import pytest

from app.ai.retriever import retrieve


def _deps_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        import weaviate
    except Exception:
        return False
    try:
        client = weaviate.connect_to_local()
        try:
            return client.is_ready()
        finally:
            client.close()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _deps_available(), reason="Weaviate and/or sentence-transformers not available"
)


def test_in_corpus_questions_hit_expected_sources():
    cases = [
        ("What is the stipend for the QuantAlpha internship?", "jd_quantalpha_data_analyst.txt"),
        # FAQ/matrix docs answer this in Q&A form, so either is a correct top hit
        ("How many active backlogs are allowed?", {"placement_policy_2026.pdf", "placement_policy_faq_2026.txt", "eligibility_matrix_2026.txt"}),
        ("What is the minimum CGPA required by Nimbus Software?", "jd_nimbus_software_engineer.txt"),
        ("What is TCS Ninja CTC?", "jd_tcs_ninja_2026.txt"),
    ]
    for question, expected_source in cases:
        chunks = retrieve(question, top_k=3)
        assert chunks, f"nothing retrieved for: {question}"
        expected = expected_source if isinstance(expected_source, set) else {expected_source}
        assert chunks[0].source in expected, (
            f"expected one of {expected} as top hit for {question!r}, got {chunks[0].source}"
        )


def test_out_of_corpus_question_declined():
    # hybrid fusion scores unrelated text ~0.65; threshold 0.70 must drop it
    assert retrieve("What is the capital of France?", top_k=3) == []
    assert retrieve("Who won the last cricket world cup?", top_k=3) == []
    assert retrieve("What is the weight of the moon?", top_k=3) == []
