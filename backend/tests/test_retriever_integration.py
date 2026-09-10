# Integration test — requires a running Weaviate (docker start weaviate) and an ingested corpus.

import pytest

from app.ai.retriever import retrieve


def _weaviate_up() -> bool:
    try:
        import weaviate

        client = weaviate.connect_to_local()
        try:
            return client.is_ready()
        finally:
            client.close()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _weaviate_up(), reason="Weaviate not running locally")


def test_in_corpus_questions_hit_expected_sources():
    cases = [
        ("What is the stipend for the QuantAlpha internship?", "jd_quantalpha_data_analyst.txt"),
        ("How many active backlogs are allowed?", "placement_policy_2026.pdf"),
        ("What is the minimum CGPA required by Nimbus Software?", "jd_nimbus_software_engineer.txt"),
    ]
    for question, expected_source in cases:
        chunks = retrieve(question, top_k=3)
        assert chunks, f"nothing retrieved for: {question}"
        assert chunks[0].source == expected_source, (
            f"expected {expected_source} as top hit for {question!r}, got {chunks[0].source}"
        )


def test_out_of_corpus_question_declined():
    assert retrieve("What is the capital of France?", top_k=3) == []
    assert retrieve("Who won the last cricket world cup?", top_k=3) == []
