# Eval Baseline (Phase 5)

Generated: 2026-09-11 09:55:10

Full agent pipeline (intent -> tool selection -> MCP tools -> synthesis) with the
real Postgres, Weaviate, and Groq stack.

## Summary

| Metric | Value |
|---|---|
| Questions | 27 |
| Scored (excl. agent errors) | 27 |
| Agent errors (rate limits etc.) | 0 |
| Correctness | 100.0% |
| Groundedness (citation accuracy) | 78.6% |
| Retrieval recall | 100.0% |
| Hallucination rate | 0.0% |
| Latency avg / p50 / p95 (s) | 9.17 / 7.33 / 17.38 |
| LLM calls | 79 |
| Tokens (prompt / completion) | 50866 / 15415 |
| Estimated cost (USD) | 0.019051 |

## Per-question results

| id | type | correct | declined | hallucinated | latency (s) | tools | error |
|---|---|---|---|---|---|---|---|
| stipend-01 | stipend_lookup | Y | N | N | 20.81 | search_policy_docs |  |
| stipend-02 | stipend_lookup | Y | Y | N | 5.32 | get_drive_details |  |
| stipend-03 | stipend_lookup | Y | N | N | 7.21 | search_policy_docs |  |
| branch-01 | eligible_branches | Y | N | N | 7.48 | get_drive_details |  |
| branch-02 | eligible_branches | Y | N | N | 13.61 | get_drive_details, check_eligibility |  |
| elig-01 | am_i_eligible | Y | N | N | 17.38 | get_student_profile, get_drive_details, check_eligibility |  |
| elig-02 | am_i_eligible | Y | N | N | 10.68 | check_eligibility |  |
| elig-03 | am_i_eligible | Y | N | N | 10.44 | check_eligibility |  |
| elig-04 | am_i_eligible | Y | N | N | 4.43 | check_eligibility |  |
| why-01 | why_not_eligible | Y | N | N | 4.5 | check_eligibility |  |
| why-02 | why_not_eligible | Y | N | N | 6.12 | get_drive_details, check_eligibility |  |
| ctc-01 | cross_company_ctc | Y | N | N | 8.89 | get_drive_details, get_drive_details, get_drive_details |  |
| ctc-02 | cross_company_ctc | Y | N | N | 17.31 | get_drive_details, get_drive_details, get_drive_details |  |
| ctc-03 | cross_company_ctc | Y | N | N | 13.54 | get_drive_details |  |
| policy-01 | policy_question | Y | N | N | 16.39 | search_policy_docs |  |
| policy-02 | policy_question | Y | N | N | 16.89 | search_policy_docs |  |
| policy-03 | policy_question | Y | N | N | 9.33 | search_policy_docs |  |
| policy-04 | policy_question | Y | N | N | 6.72 | search_policy_docs |  |
| policy-05 | policy_question | Y | N | N | 6.17 | search_policy_docs |  |
| policy-06 | policy_question | Y | N | N | 6.73 | search_policy_docs |  |
| process-01 | selection_process | Y | N | N | 7.33 | search_policy_docs |  |
| process-02 | selection_process | Y | N | N | 6.18 | search_policy_docs |  |
| interview-01 | interview_experience | Y | N | N | 9.42 | search_policy_docs |  |
| recommend-01 | recommendation | Y | N | N | 6.24 | get_recommendations |  |
| out-01 | out_of_corpus | Y | Y | N | 1.21 | - |  |
| out-02 | out_of_corpus | Y | Y | N | 6.01 | search_policy_docs |  |
| out-03 | out_of_corpus | Y | Y | N | 1.35 | - |  |

## Known gaps

- `stipend-02`: the DevOps intern stipend lives only in Postgres, not in any ingested
  document, so the RAG path declines. Needs a DB-backed stipend tool (Phase 8).
- Groq on-demand tier rate-limits by tokens/minute; keep `--delay` when running the
  full suite, and note agent errors are excluded from the scored metrics above.

Re-run after any prompt/retrieval/model change and diff against this baseline.
