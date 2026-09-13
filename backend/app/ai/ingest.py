# Ingestion pipeline: load documents, chunk, embed, and upsert into Weaviate.
# Incremental: each document is content-hashed; unchanged docs are skipped,
# changed docs are re-ingested (old chunks deleted first), and removed files
# have their chunks purged when re-scanned with prune=True.
#
# Usage (from backend/):
#   python -m app.ai.ingest              # incremental ingest of data/sample_docs
#   python -m app.ai.ingest --rebuild    # drop the collection and re-ingest everything
#   python -m app.ai.ingest --prune      # also delete chunks for files no longer present

import hashlib
import re
import sys
import uuid
from pathlib import Path

from app.ai.chunker import chunk_text
from app.ai.companies import normalize_company
from app.ai.document_loader import load_document
from app.ai.embeddings import embed_texts
from app.ai.weaviate_client import (
    delete_collection,
    delete_document_chunks,
    get_client,
    get_collection,
)
from app.core.config import settings

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_docs"

# Filename substrings -> canonical company (single source: app.ai.companies).
from app.ai.companies import CANONICAL_COMPANIES as _COMPANIES  # noqa: E402


def _content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _infer_metadata(path: Path) -> dict:
    """Infer company/year/document_type/role from filename for hybrid+filtered search."""
    name = path.name.lower()
    m = re.search(r"(20\d{2})", name)
    year = int(m.group(1)) if m else (2025 if name.startswith("ie_") or "statistics" in name else 2026)
    company = ""
    for frag, canonical in _COMPANIES.items():
        if frag in name:
            company = canonical
            break
    if "placement_policy" in name:
        document_type = "placement_policy"
    elif "faq" in name:
        document_type = "placement_policy"
    elif "eligibility_matrix" in name:
        document_type = "eligibility_matrix"
    elif "offer_process" in name:
        document_type = "offer_process"
    elif "document_requirements" in name:
        document_type = "document_requirement"
    elif "tnpc_calendar" in name:
        document_type = "schedule"
    elif "tnpc_announcements" in name:
        document_type = "announcement"
    elif "placement_statistics" in name:
        document_type = "placement_statistics"
    elif name.startswith("jd_"):
        document_type = "job_description"
    elif name.startswith("ie_"):
        document_type = "interview_experience"
    else:
        document_type = "general"
    # role hint (light)
    role = ""
    if "software_engineer" in name or "sde" in name or "ninja" in name:
        role = "Software Engineer"
    elif "data_analyst" in name:
        role = "Data Analyst"
    elif "specialist" in name or "sp" in name:
        role = "Specialist Programmer"
    elif "mechanical" in name or "mercedes" in name:
        role = "Mechanical Design Engineer"
    elif "embedded" in name or "ece" in name:
        role = "Embedded Engineer"
    elif "accenture" in name or "advanced" in name:
        role = "Advanced App Engineering Analyst"
    return {"company": company, "year": year, "document_type": document_type, "role": role, "source": path.name}


def _scan_docs() -> list[dict]:
    """Auto-scan SAMPLE_DIR for all supported files with inferred metadata."""
    docs = []
    for path in sorted(SAMPLE_DIR.glob("*")):
        if path.suffix.lower() not in settings.ALLOWED_DOC_TYPES:
            continue
        if path.name.startswith("."):
            continue
        meta = _infer_metadata(path)
        docs.append({"path": path, **meta})
    return docs


def _existing_hashes(collection) -> dict[str, str]:
    """Map source filename -> content_hash for every chunk already indexed."""
    manifest: dict[str, str] = {}
    try:
        for obj in collection.iterator():
            props = obj.properties
            src = props.get("source")
            if src and props.get("content_hash"):
                manifest[src] = props["content_hash"]
    except Exception:
        pass  # legacy collection without hash properties — treated as empty manifest
    return manifest


def ingest(prune: bool = False, rebuild: bool = False) -> None:
    _ensure_sample_docs()
    client = get_client()
    if rebuild:
        delete_collection(client)
        client = get_client()
    try:
        collection = get_collection(client)
        docs = _scan_docs()
        if not docs:
            print(f"No documents found in {SAMPLE_DIR}")
            return
        manifest = _existing_hashes(collection)

        ingested = unchanged = 0
        seen_sources: set[str] = set()
        for doc in docs:
            data = doc["path"].read_bytes()
            digest = _content_hash(data)
            seen_sources.add(doc["source"])
            if manifest.get(doc["source"]) == digest:
                unchanged += 1
                continue  # identical content — skip

            # Changed or new document: purge any previous chunks, then index.
            if doc["source"] in manifest:
                delete_document_chunks_by_source(client, doc["source"])

            document_id = str(uuid.uuid4())
            pages = load_document(doc["path"])
            chunks = chunk_text(
                pages,
                document_id=document_id,
                metadata={
                    k: v for k, v in doc.items() if k != "path"
                } | {"content_hash": digest, "embedding_model": settings.EMBEDDING_MODEL},
                chunk_size=settings.CHUNK_SIZE,
                overlap=settings.CHUNK_OVERLAP,
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
            ingested += 1
            print(f"Ingested {len(chunks):3d} chunks from {doc['path'].name}")

        pruned = 0
        if prune:
            for source in set(manifest) - seen_sources:
                pruned += delete_document_chunks_by_source(client, source)
                print(f"Pruned chunks for removed document: {source}")

        print(
            f"Done. ingested={ingested} unchanged={unchanged} pruned_docs={len(set(manifest) - seen_sources) if prune else 0}"
            + (f" pruned_chunks={pruned}" if prune and pruned else "")
            + f" (model: {settings.EMBEDDING_MODEL})."
        )
    finally:
        client.close()


def delete_document_chunks_by_source(client, source: str) -> int:
    """Delete every chunk whose source filename matches (old chunks of a changed doc)."""
    from weaviate.classes.query import Filter

    collection = get_collection(client)
    result = collection.data.delete_many(Filter.by_property("source").equal(source))
    return result.successful or 0


# ---------------------------------------------------------------------------
# Demo corpus bootstrap (only creates the sample files when the directory is
# entirely missing — production corpora arrive via the admin upload API).
# ---------------------------------------------------------------------------

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
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

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
    rebuild = "--rebuild" in sys.argv
    prune = "--prune" in sys.argv
    ingest(prune=prune, rebuild=rebuild)
    sys.exit(0)
