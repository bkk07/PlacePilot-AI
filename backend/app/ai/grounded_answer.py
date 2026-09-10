# Grounded answering: retrieved chunks -> prompt -> Groq LLM -> cited, schema-validated answer.

from app.ai.llm_use_cases import answer_policy_question
from app.ai.retriever import retrieve


def answer_question(question: str, top_k: int = 5) -> dict:
    """Retrieve, then generate a grounded answer. Returns {answer, citations, grounded}."""
    chunks = retrieve(question, top_k=top_k)
    if not chunks:
        return {
            "answer": "I don't have that information in the placement documents I was given.",
            "citations": [],
            "grounded": False,
        }

    context = [
        {"source": c.source or c.document_id, "page_number": c.page_number, "text": c.text}
        for c in chunks
    ]
    result = answer_policy_question(question, context)
    return {
        "answer": result.answer,
        "citations": [c.model_dump() for c in result.citations],
        "grounded": result.grounded,
    }
