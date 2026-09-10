# RAG Demo Transcript (Phase 1)

Corpus: 5 sample documents (1 placement policy PDF, 2 job descriptions, 2 interview experiences) → 9 chunks in Weaviate `DocumentChunk`, embedded with `sentence-transformers/all-MiniLM-L6-v2`, LLM via Groq (`openai/gpt-oss-120b`).

---

**Q: What is the stipend for the QuantAlpha internship?**
> The QuantAlpha Analytics internship offers a stipend of **₹35,000 per month** for the six‑month internship period [jd_quantalpha_data_analyst.txt p.1].

**Q: How many active backlogs are allowed to stay eligible for placement?**
> A student may have **no more than one active backlog** to remain eligible for campus placement [placement_policy_2026.pdf p.1].

**Q: What is the minimum CGPA required by Nimbus Software?**
> Nimbus Software requires a minimum CGPA of 7.0 for the Software Engineer (Fresher) role [jd_nimbus_software_engineer.txt p.1].

**Q: How long do students get to accept an offer?**
> Students have 5 working days to accept or decline an offer [placement_policy_2026.pdf p.1].

**Q: What does the Nimbus selection process look like?**
> 1. **Online assessment** – 90 minutes, DSA + SQL + aptitude (October 12, 2026). 2. **Two technical interviews** – DSA, system design basics, projects deep‑dive. 3. **HR discussion**. [jd_nimbus_software_engineer.txt p.1, ie_nimbus_sde_intern.txt p.1]

**Q: What happens if a student receives a third offer?**
> If a student receives a third offer, the two earlier offers are automatically forfeited, leaving the student with only the most recent offer [placement_policy_2026.pdf p.1].

---

**Out-of-corpus (must be declined):**

**Q: What is the capital of France?**
> I don't have that information in the placement documents I was given.

**Q: Who won the last cricket world cup?**
> I don't have that information in the placement documents I was given.

---

Exit criteria status: **met** — correct chunks retrieved and cited for all in-corpus questions; out-of-corpus questions correctly declined (both at retrieval threshold and by LLM fallback instruction).
