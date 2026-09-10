# Ingestion script: load documents from data/sample_docs/, chunk, embed, insert into Weaviate.
#
# Usage (from backend/):  python -m app.ai.ingest

import sys
import uuid
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.ai.chunker import chunk_text
from app.ai.document_loader import load_document
from app.ai.embeddings import embed_texts
from app.ai.weaviate_client import get_client, get_collection

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_docs"


def _ensure_sample_docs() -> None:
    """Create the sample corpus (1 policy PDF, 2 JDs, 2 interview experiences) if missing."""
    if SAMPLE_DIR.exists():
        return
    SAMPLE_DIR.mkdir(parents=True)
    _make_policy_pdf(SAMPLE_DIR / "placement_policy_2026.pdf")
    (SAMPLE_DIR / "jd_nimbus_software_engineer.txt").write_text(JD_NIMBUS, encoding="utf-8")
    (SAMPLE_DIR / "jd_quantalpha_data_analyst.txt").write_text(JD_QUANTALPHA, encoding="utf-8")
    (SAMPLE_DIR / "ie_nimbus_sde_intern.txt").write_text(IE_NIMBUS, encoding="utf-8")
    (SAMPLE_DIR / "ie_quantalpha_analyst.txt").write_text(IE_QUANTALPHA, encoding="utf-8")


def _make_policy_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    lines = PLACEMENT_POLICY_TEXT.splitlines()
    y = 800
    for line in lines:
        if y < 50:
            c.showPage()
            y = 800
        c.drawString(50, y, line)
        y -= 16
    c.save()


def ingest() -> None:
    _ensure_sample_docs()
    client = get_client()
    collection = get_collection(client)
    try:
        if len(collection) > 0:
            print(f"Collection already populated ({len(collection)} chunks) — skipping. Delete the collection to re-ingest.")
            return

        docs = [
            {
                "path": SAMPLE_DIR / "placement_policy_2026.pdf",
                "company": "",
                "year": 2026,
                "document_type": "placement_policy",
                "role": "",
                "source": "placement_policy_2026.pdf",
            },
            {
                "path": SAMPLE_DIR / "jd_nimbus_software_engineer.txt",
                "company": "Nimbus Software",
                "year": 2026,
                "document_type": "job_description",
                "role": "Software Engineer",
                "source": "jd_nimbus_software_engineer.txt",
            },
            {
                "path": SAMPLE_DIR / "jd_quantalpha_data_analyst.txt",
                "company": "QuantAlpha Analytics",
                "year": 2026,
                "document_type": "job_description",
                "role": "Data Analyst",
                "source": "jd_quantalpha_data_analyst.txt",
            },
            {
                "path": SAMPLE_DIR / "ie_nimbus_sde_intern.txt",
                "company": "Nimbus Software",
                "year": 2025,
                "document_type": "interview_experience",
                "role": "Software Engineer",
                "source": "ie_nimbus_sde_intern.txt",
            },
            {
                "path": SAMPLE_DIR / "ie_quantalpha_analyst.txt",
                "company": "QuantAlpha Analytics",
                "year": 2025,
                "document_type": "interview_experience",
                "role": "Data Analyst",
                "source": "ie_quantalpha_analyst.txt",
            },
        ]

        total = 0
        for doc in docs:
            document_id = str(uuid.uuid4())
            pages = load_document(doc["path"])
            chunks = chunk_text(
                pages,
                document_id=document_id,
                metadata={k: v for k, v in doc.items() if k != "path"},
            )
            if not chunks:
                print(f"WARNING: no chunks produced for {doc['path'].name}")
                continue
            vectors = embed_texts([c.text for c in chunks])
            with collection.batch.dynamic() as batch:
                for chunk, vector in zip(chunks, vectors):
                    batch.add_object(
                        properties={
                            "text": chunk.text,
                            **chunk.metadata,
                        },
                        vector=vector,
                    )
            total += len(chunks)
            print(f"Ingested {len(chunks):3d} chunks from {doc['path'].name}")
        print(f"Done. {total} chunks in collection.")
    finally:
        client.close()


PLACEMENT_POLICY_TEXT = """Placement Policy 2026

1. Eligibility
1.1 A student is eligible for campus placement if they have a CGPA of 6.0 or above and no more than one active backlog at the time of registration.
1.2 Students with more than one active backlog must clear them before the start of the placement season.
1.3 Branch-specific cutoffs may be applied by companies; these are listed on each drive.

2. Registration
2.1 Students must register with the placement cell by 30 August 2026. Late registrations will not be accepted.
2.2 Registration requires a verified resume and faculty advisor approval.

3. Application Rules
3.1 A student may hold at most two active offers at any point. On receiving a third offer, the earlier offers are considered forfeited.
3.2 Once placed, a student is withdrawn from all future drives.
3.3 Students must attend all scheduled interviews. Two no-shows disqualify the student from the remainder of the season.

4. Offers
4.1 Offers are released by companies to the placement cell and communicated within 48 hours.
4.2 Students have 5 working days to accept or decline an offer.

5. Stipends
5.1 Internship stipends below 10000 rupees per month require a written justification from the company.
5.2 The cell publishes the median stipend for each sector annually.

6. Code of Conduct
6.1 Sharing company assessment material is grounds for disqualification.
6.2 Reneging on an accepted offer requires placement-cell approval and is recorded on the student's record.
"""

JD_NIMBUS = """Nimbus Software — Job Description

Role: Software Engineer (Fresher, 2026 batch)
Location: Bangalore (hybrid, 3 days in office)
CTC: 12 LPA. Internship conversion offers carry a retention bonus of 1 LPA after one year.

About: Nimbus Software builds cloud-native analytics infrastructure used by 400+ enterprise clients.

Requirements:
- B.E./B.Tech in Computer Science, IT, or ECE with CGPA 7.0 or above
- Strong Python and data structures; SQL fundamentals
- Experience with at least one cloud platform (AWS preferred)

Selection Process:
1. Online assessment: 90 minutes, DSA + SQL + aptitude (October 12, 2026)
2. Two technical interviews: DSA, system design basics, projects deep-dive
3. HR discussion

Perks: health insurance for self and dependents, 5000 rupees monthly learning stipend, annual offsite.
"""

JD_QUANTALPHA = """QuantAlpha Analytics — Job Description

Role: Data Analyst (2026 batch)
Location: Mumbai (on-site)
Stipend: 35000 rupees per month during the 6-month internship; PPO at 9.5 LPA on conversion.

About: QuantAlpha Analytics provides quantitative research and market-data platforms to institutional clients.

Requirements:
- Any engineering branch with CGPA 6.5 or above; Mathematics or Statistics coursework preferred
- SQL is mandatory; Python (pandas) strongly preferred
- Strong written communication for research notes

Selection Process:
1. SQL + case-study assessment (45 minutes)
2. Case interview: market-sizing and data interpretation
3. Final round with research head

Note: candidates with prior market-data internships are fast-tracked to the case interview.
"""

IE_NIMBUS = """Interview Experience — Nimbus Software, Software Engineer (Intern converted to FTE), 2025

The online round had two medium DSA problems (one on sliding window, one on graph BFS) and 10 SQL queries. Around 180 students appeared and 34 were shortlisted.

Technical Round 1 focused purely on DSA. I was asked to implement an LRU cache and then optimize it, followed by a discussion on time complexity. The interviewer asked why I chose a heap in my project's scheduler.

Technical Round 2 was project-heavy. Expect deep questions on anything on your resume. I discussed my REST API's indexing strategy and was asked to sketch a rate limiter.

The HR round was conversational: relocation willingness, why Nimbus, and a discussion of the learning stipend program. The whole process took one week. Tip: practice writing SQL by hand without autocomplete.
"""

IE_QUANTALPHA = """Interview Experience — QuantAlpha Analytics, Data Analyst (Internship), 2025

The assessment was 15 SQL questions and one market-sizing case: estimate daily transactions on a UPI platform. 90 minutes total, calculators allowed.

Round 2 was the case interview. The interviewer gave me a churn dataset and asked what I would investigate first. I walked through cohort analysis and he pushed me to quantify confidence in my conclusions. He cared more about structure than the exact numbers.

The final round with the research head was mostly resume walkthrough plus a discussion on a market event from the previous quarter. He asked how I would validate a data pipeline silently producing wrong aggregates.

Advice: know your resume projects cold, and brush up on percentile math and basic probability. Conversion to the 9.5 LPA PPO required a strong internship review and a final SQL practical.
"""


if __name__ == "__main__":
    ingest()
    sys.exit(0)
