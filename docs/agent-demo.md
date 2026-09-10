# LangGraph Agent Demo Transcript (Phase 3)

Agent: intent → tool-selection → tool-execution → LLM-synthesis (Groq `openai/gpt-oss-120b` for all structured nodes; `gpt-oss-20b` was tried for selection but returned empty outputs on JSON-mode prompts, so the reliable reasoning model is used). Tools run over seeded data; policy questions go through the Weaviate RAG retriever. Conversation state persists per thread via an in-memory checkpointer.

---

**Workflow 1 — eligibility check**

**Q: Am I eligible for the Nimbus Software Engineer drive?**
- intent: `eligibility_check` · tools: `check_eligibility`
> You are eligible for the **Nimbus Software Engineer (2026 batch)** drive. The eligibility check returned **"eligible: true"** with the reason **"All eligibility criteria are met."**

**Workflow 2 — policy question**

**Q: How many active backlogs are allowed for placement?**
- intent: `policy_question` · tools: `search_policy_docs`
> At most one active backlog is allowed for placement eligibility. *(grounded in placement_policy_2026.pdf)*

**Workflow 3 — cross-company query**

**Q: Compare the CTC offered by Nimbus and QuantAlpha**
- intent: `cross_company_query` · tools: `search_policy_docs`
> Nimbus Software offers a **CTC of 12 LPA** for the fresh-grad Software Engineer role. QuantAlpha Analytics provides a **PPO of 9.5 LPA** after the internship for the Data Analyst position. Nimbus's package is higher (12 LPA vs 9.5 LPA).

**Workflow 4 — recommendation**

**Q: Which drives should I apply to?**
- intent: `recommendation` · tools: `get_recommendations`
> Top-scoring eligible drives: **Nimbus Software Engineer** (python, aws, sql — 0.6) and **QuantAlpha Data Analyst** (sql, python — 0.6), followed by Nimbus DevOps Intern (aws — 0.4).

**Follow-up (same thread — persistence)**

**Q: What about the QuantAlpha one?**
- intent: `policy_question` · tools: `search_policy_docs`
> QuantAlpha Analytics is hiring a Data Analyst (2026 batch) in Mumbai; six-month internship at ₹35,000/month with PPO at 9.5 LPA on conversion; CGPA 6.5+; SQL mandatory; selection: SQL + case-study assessment → case interview → research-head round. *(full details retrieved and synthesized correctly in the follow-up turn)*

---

Exit criteria status: **met** — all four example workflows pick the right tool and produce sensible final answers; conversation state persists across turns.
