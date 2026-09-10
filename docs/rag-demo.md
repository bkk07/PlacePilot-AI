# RAG Demo Transcript (Phase 1, updated Phase 2)

Corpus: 5 sample documents (1 placement policy PDF, 2 job descriptions, 2 interview experiences) → 9 chunks in Weaviate `DocumentChunk`, embedded with `sentence-transformers/all-MiniLM-L6-v2`, LLM via Groq (`openai/gpt-oss-120b`).

Since Phase 2, answers are schema-validated `PolicyAnswer` objects and every citation carries an exact supporting quote.

---

**Q: What is the stipend for the QuantAlpha internship?**
> The QuantAlpha internship offers a stipend of ₹35,000 per month during the 6-month internship.
> — `jd_quantalpha_data_analyst.txt` p.1: *"Stipend: 35000 rupees per month during the 6-month internship"*

**Q: How many active backlogs are allowed to stay eligible for placement?**
> A student may have at most one active backlog to remain eligible for placement.
> — `placement_policy_2026.pdf` p.1: *"A student is eligible for campus placement if they have a CGPA of 6.0 or above and no more than one active backlog at the time of registration."*

**Q: What is the minimum CGPA required by Nimbus Software?**
> Nimbus Software requires a minimum CGPA of 7.0.
> — `jd_nimbus_software_engineer.txt` p.1: *"B.E./B.Tech in Computer Science, IT, or ECE with CGPA 7.0 or above"*

**Q: How long do students get to accept an offer?**
> Students have 5 working days to accept or decline an offer.
> — `placement_policy_2026.pdf` p.1: *"Students have 5 working days to accept or decline an offer."*

**Q: What does the Nimbus selection process look like?**
> (1) An online assessment lasting 90 minutes covering DSA, SQL, and aptitude (October 12, 2026); (2) two technical interviews on DSA, system-design basics, and projects deep-dive; (3) an HR discussion.
> — `jd_nimbus_software_engineer.txt` p.1, `ie_nimbus_sde_intern.txt` p.1

**Q: What happens if a student receives a third offer?**
> If a student receives a third offer, the earlier offers are considered forfeited.
> — `placement_policy_2026.pdf` p.1: *"A student may hold at most two active offers at any point. On receiving a third offer, the earlier offers are considered forfeited."*

---

**Out-of-corpus (must be declined):**

**Q: What is the capital of France?**
> I don't have that information in the placement documents I was given. *(no citations, grounded=false)*

**Q: Who won the last cricket world cup?**
> I don't have that information in the placement documents I was given. *(no citations, grounded=false)*

---

Exit criteria status: **met** — correct chunks retrieved and cited (with exact quotes) for all in-corpus questions; out-of-corpus questions correctly declined.
