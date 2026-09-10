# MCP Demo Transcript (Phase 4)

Tools now run on three MCP servers over streamable-http, backed by PostgreSQL (structured) and Weaviate (RAG). Every tool call re-verifies the caller's JWT and role before executing, and every call is audit-logged.

Servers: `placement-mcp` (8101), `student-mcp` (8102), `knowledge-mcp` (8103).

---

**Workflow 1 — eligibility check**

**Q: Am I eligible for the Nimbus Software Engineer drive?**
- intent: `eligibility_check` · tools: `check_eligibility`
> You are eligible for the **Nimbus Software Engineer (2026 batch)** drive. The eligibility check returned **"eligible: true"** with the reason **"All eligibility criteria are met."**

**Workflow 2 — policy question**

**Q: How many active backlogs are allowed for placement?**
- intent: `policy_question` · tools: `search_policy_docs`
> A student may have at most one active backlog to be eligible for placement. *(grounded in placement_policy_2026.pdf)*

**Workflow 3 — cross-company query**

**Q: Compare the CTC offered by Nimbus and QuantAlpha**
- intent: `cross_company_query` · tools: `get_drive_details`, `get_drive_details`
> Nimbus Software offers a **CTC of 12 LPA** for its Software Engineer role, while QuantAlpha Analytics offers a **CTC of 9.5 LPA** for its Data Analyst position. Thus, Nimbus's package is higher by 2.5 LPA.

**Workflow 4 — recommendation**

**Q: Which drives should I apply to?**
- intent: `recommendation` · tools: `get_recommendations`
> 1. **Nimbus Software Engineer** (python, aws, sql — eligible, 0.6)
> 2. **QuantAlpha Data Analyst** (sql, python — eligible, 0.6)
> 3. **Nimbus DevOps Intern** (aws — eligible, 0.4)

**Follow-up (same thread — persistence)**

**Q: What about the QuantAlpha one?**
- intent: `cross_company_query` · tools: `get_drive_details`
> QuantAlpha Data Analyst (2026 batch), Mumbai, CTC 9.5 LPA, stipend 35,000/month, deadline 20 Sept 2026, open. Required skills: SQL, Python. Eligibility: min CGPA 6.5, max 1 backlog.

---

**Negative authz test — student A's token requesting student B's profile**

```
get_student_profile(rohan) with asha's token
-> {'error': 'forbidden: students may only access their own data'}
```

Blocked at the MCP tool layer, independently of the agent, and recorded in the audit log.

---

Exit criteria status: **met** — all four Phase 3 workflows now run through MCP servers; unauthorized cross-student access and admin-only tools are blocked with a passing negative test (11/11 authz tests, 64/64 total).