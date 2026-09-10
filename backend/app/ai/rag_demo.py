# Demo Q&A over the ingested sample corpus.
#
# Usage (from backend/, with .env containing GROQ_API_KEY):  python -m app.ai.rag_demo
# Without a GROQ_API_KEY the demo runs in retrieval-only mode (no LLM answers).

import os
import sys

from app.ai.grounded_answer import answer_question
from app.ai.retriever import retrieve

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

QUESTIONS = [
    # in-corpus
    "What is the stipend for the QuantAlpha internship?",
    "How many active backlogs are allowed to stay eligible for placement?",
    "What is the minimum CGPA required by Nimbus Software?",
    "How long do students get to accept an offer?",
    "What does the Nimbus selection process look like?",
    "What happens if a student receives a third offer?",
    # out-of-corpus — must be declined
    "What is the capital of France?",
    "Who won the last cricket world cup?",
]


def main() -> None:
    has_key = bool(os.environ.get("GROQ_API_KEY"))
    if not has_key:
        print("NOTE: GROQ_API_KEY not set — running in retrieval-only mode.\n")
    for q in QUESTIONS:
        print("=" * 80)
        print("Q:", q)
        if has_key:
            result = answer_question(q)
            print("A:", result["answer"])
            print("citations:", result["citations"])
        else:
            chunks = retrieve(q, top_k=3)
            if not chunks:
                print("A: (declined — no relevant chunks)")
            for c in chunks:
                print(f"   {c.score:.2f} | {c.source} p.{c.page_number}")
        print()


if __name__ == "__main__":
    main()
