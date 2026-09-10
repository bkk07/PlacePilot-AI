# Grounded answering: retrieved chunks -> prompt template -> Groq LLM -> cited answer.

import os

from groq import Groq

from app.ai.retriever import RetrievedChunk, retrieve

MODEL = os.getenv("GROQ_REASONING_MODEL", "openai/gpt-oss-120b")

SYSTEM_PROMPT = """You are a placement-cell assistant. Answer ONLY from the provided context chunks.
Rules:
- Cite sources inline as [source p.N] for every factual claim.
- If the context does not contain the answer, reply exactly: I don't have that information in the placement documents I was given.
- Never invent company names, CTC figures, stipends, dates, or selection rounds."""


def _build_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for c in chunks:
        label = f"{c.company or c.document_type} [{c.source or c.document_id} p.{c.page_number}]"
        parts.append(f"--- {label} ---\n{c.text}")
    return "\n\n".join(parts)


def answer_question(question: str, top_k: int = 5) -> dict:
    """Retrieve, then generate a grounded answer. Returns {answer, citations, grounded}."""
    chunks = retrieve(question, top_k=top_k)
    if not chunks:
        return {
            "answer": "I don't have that information in the placement documents I was given.",
            "citations": [],
            "grounded": False,
        }

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context chunks:\n\n{_build_context(chunks)}\n\nQuestion: {question}",
            },
        ],
        temperature=0.1,
        max_tokens=600,
    )
    return {
        "answer": response.choices[0].message.content,
        "citations": [f"{c.source or c.document_id} p.{c.page_number}" for c in chunks],
        "grounded": True,
    }
