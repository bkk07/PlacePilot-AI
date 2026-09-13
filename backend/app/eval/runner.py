# Eval runner: sends each dataset question through the full agent pipeline and scores
# correctness, groundedness, retrieval recall, citation accuracy, hallucination, latency,
# token usage, and estimated cost.
#
# Usage (from backend/, with MCP servers + Weaviate + Postgres up):
#   python -m app.eval.runner                 # full run + writes docs/eval-baseline.md
#   python -m app.eval.runner --limit 5       # quick slice
#   python -m app.eval.runner --delay 3       # extra seconds between questions (rate limits)
#   python -m app.eval.runner --json          # machine-readable report on stdout

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from sqlalchemy import select

from app.ai.llm_service import track_usage
from app.core.security import create_token
from app.db.db import get_session_factory
from app.db.models import User
from app.eval.dataset import (
    DATASET_PATH,
    JSONL_DATASET_PATH,
    EvalQuestion,
    load_dataset,
)
from app.eval.metrics import citation_accuracy, correctness, hallucination, is_declined, retrieval_recall

# Approximate Groq list prices (USD per 1M tokens) — update if Groq changes them.
PRICING = {
    "openai/gpt-oss-120b": {"input": 0.15, "output": 0.75},
    "openai/gpt-oss-20b": {"input": 0.075, "output": 0.30},
}
DEFAULT_PRICE = {"input": 0.15, "output": 0.75}

BASELINE_PATH = Path(__file__).resolve().parents[3] / "docs" / "eval-baseline.md"
DEFAULT_STUDENT = "asha@college.edu"

# Groq's on-demand tier rate-limits by tokens/minute; a full question can burn several
# thousand tokens, so space questions out and back off hard when a 429 surfaces.
DEFAULT_DELAY_S = 2.0
RATE_LIMIT_SLEEP_S = 30.0


@dataclass
class QuestionResult:
    id: str
    type: str
    question: str
    answer: str
    latency_s: float
    declined: bool
    correct: bool
    hallucinated: bool
    citation_ok: bool | None = None
    recall_ok: bool | None = None
    tools: list = field(default_factory=list)
    error: str | None = None


def _token_for(email: str) -> tuple[str, str]:
    session = get_session_factory()()
    try:
        user = session.scalar(select(User).where(User.email == email))
        return str(user.id), create_token(str(user.id), user.role)
    finally:
        session.close()


def _retrieved_sources_for(question: str) -> list[str]:
    try:
        from app.ai.retriever import retrieve

        return [c.source for c in retrieve(question, top_k=3)]
    except Exception:
        return []


def _is_rate_limit(exc: Exception) -> bool:
    return "429" in str(exc) or "rate limit" in str(exc).lower()


def run_eval(
    questions: list[EvalQuestion] | None = None,
    write_baseline: bool = True,
    progress: bool = False,
    delay_s: float = DEFAULT_DELAY_S,
) -> dict:
    from app.agent.runner import run_turn

    questions = questions or load_dataset()
    results: list[QuestionResult] = []

    with track_usage() as usage:
        for idx, q in enumerate(questions):
            email = q.student_id or DEFAULT_STUDENT
            try:
                student_id, token = _token_for(email)
            except Exception:
                student_id, token = "", ""

            start = time.perf_counter()
            out: dict = {}
            error: str | None = None
            for attempt in range(3):
                try:
                    out = run_turn(q.question, student_id=student_id, thread_id=f"eval-{q.id}", token=token)
                    error = None
                    break
                except Exception as exc:
                    error = str(exc)
                    if _is_rate_limit(exc) and attempt < 2:
                        if progress:
                            print(f"      rate limited on {q.id}; sleeping {RATE_LIMIT_SLEEP_S:.0f}s", flush=True)
                        time.sleep(RATE_LIMIT_SLEEP_S)
                        continue
                    break
            latency = time.perf_counter() - start

            if error:
                answer, tools, citations, declined = f"[agent error: {error}]", [], [], False
                correct = hallucinated = False
            else:
                answer = out.get("reply", "")
                tools = [t["name"] for t in out.get("planned_tools", [])]
                declined = is_declined(answer)
                citations = []
                for tr in out.get("tool_results", []):
                    res = tr.get("result") or {}
                    if isinstance(res, dict) and res.get("chunks"):
                        citations.extend(res["chunks"])
                correct = correctness(answer, q.expected_contains, q.expect_decline)
                hallucinated = hallucination(q.expect_decline, answer, q.expected_contains)

            recall_sources = _retrieved_sources_for(q.question) if q.expected_source else []

            results.append(
                QuestionResult(
                    id=q.id,
                    type=q.type,
                    question=q.question,
                    answer=answer.strip(),
                    latency_s=round(latency, 2),
                    declined=declined,
                    correct=correct,
                    hallucinated=hallucinated,
                    citation_ok=citation_accuracy(citations, q.expected_source) if not error else None,
                    recall_ok=retrieval_recall(recall_sources, q.expected_source) if not error else None,
                    tools=tools,
                    error=error,
                )
            )
            if progress:
                mark = "E" if error else ("Y" if correct else "N")
                print(f"  [{len(results)}/{len(questions)}] {q.id:<14} {mark}  {latency:5.1f}s", flush=True)
            if delay_s and idx < len(questions) - 1:
                time.sleep(delay_s)

    report = _build_report(results, usage.summary())
    if write_baseline:
        _write_baseline(report)
    return report


def _build_report(results: list[QuestionResult], usage_summary: dict) -> dict:
    ok = [r for r in results if not r.error]
    errored = [r for r in results if r.error]
    total = len(results)
    correct = sum(1 for r in ok if r.correct)
    halluc = sum(1 for r in ok if r.hallucinated)
    cits = [r for r in ok if r.citation_ok is not None]
    recs = [r for r in ok if r.recall_ok is not None]
    latencies = sorted(r.latency_s for r in ok)

    def pct(n: int, d: int) -> float:
        return round(n / d, 3) if d else 0.0

    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_questions": total,
        "scored_questions": len(ok),
        "errors": len(errored),
        "correctness": pct(correct, len(ok)),
        "hallucination_rate": pct(halluc, len(ok)),
        "citation_accuracy": pct(sum(1 for r in cits if r.citation_ok), len(cits)) if cits else None,
        "retrieval_recall": pct(sum(1 for r in recs if r.recall_ok), len(recs)) if recs else None,
        "latency_s": {
            "avg": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            "p50": latencies[len(latencies) // 2] if latencies else 0.0,
            "p95": latencies[min(int(len(latencies) * 0.95), len(latencies) - 1)] if latencies else 0.0,
            "max": latencies[-1] if latencies else 0.0,
        },
        "usage": usage_summary,
        "estimated_cost_usd": _estimate_cost(usage_summary),
        "results": [asdict(r) for r in results],
    }


def _estimate_cost(usage_summary: dict) -> float:
    total = 0.0
    for model, rec in usage_summary.get("models", {}).items():
        price = PRICING.get(model, DEFAULT_PRICE)
        total += rec["prompt_tokens"] / 1_000_000 * price["input"]
        total += rec["completion_tokens"] / 1_000_000 * price["output"]
    return round(total, 6)


def _write_baseline(report: dict) -> None:
    lines = [
        "# Eval Baseline (Phase 5)",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "Full agent pipeline (intent -> tool selection -> MCP tools -> synthesis) with the",
        "real Postgres, Weaviate, and Groq stack.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Questions | {report['total_questions']} |",
        f"| Scored (excl. agent errors) | {report['scored_questions']} |",
        f"| Agent errors (rate limits etc.) | {report['errors']} |",
        f"| Correctness | {report['correctness']:.1%} |",
        f"| Groundedness (citation accuracy) | {_pct(report['citation_accuracy'])} |",
        f"| Retrieval recall | {_pct(report['retrieval_recall'])} |",
        f"| Hallucination rate | {report['hallucination_rate']:.1%} |",
        f"| Latency avg / p50 / p95 (s) | {report['latency_s']['avg']} / {report['latency_s']['p50']} / {report['latency_s']['p95']} |",
        f"| LLM calls | {report['usage']['calls']} |",
        f"| Tokens (prompt / completion) | {report['usage']['prompt_tokens']} / {report['usage']['completion_tokens']} |",
        f"| Estimated cost (USD) | {report['estimated_cost_usd']} |",
        "",
        "## Per-question results",
        "",
        "| id | type | correct | declined | hallucinated | latency (s) | tools | error |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in report["results"]:
        lines.append(
            f"| {r['id']} | {r['type']} | {'Y' if r['correct'] else 'N'} | "
            f"{'Y' if r['declined'] else 'N'} | {'Y' if r['hallucinated'] else 'N'} | "
            f"{r['latency_s']} | {', '.join(r['tools']) or '-'} | {r['error'] or ''} |"
        )
    lines.append("")
    lines.append("## Known gaps")
    lines.append("")
    lines.append("- `stipend-02`: the DevOps intern stipend lives only in Postgres, not in any ingested")
    lines.append("  document, so the RAG path declines. Needs a DB-backed stipend tool (Phase 8).")
    lines.append("- Groq on-demand tier rate-limits by tokens/minute; keep `--delay` when running the")
    lines.append("  full suite, and note agent errors are excluded from the scored metrics above.")
    lines.append("")
    lines.append("Re-run after any prompt/retrieval/model change and diff against this baseline.")
    lines.append("")
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text("\n".join(lines), encoding="utf-8")


def _pct(value) -> str:
    return f"{value:.1%}" if isinstance(value, float) else "n/a"


def main() -> None:
    as_json = "--json" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    delay = DEFAULT_DELAY_S
    if "--delay" in sys.argv:
        delay = float(sys.argv[sys.argv.index("--delay") + 1])
    dataset_path = DATASET_PATH
    if "--set" in sys.argv:
        name = sys.argv[sys.argv.index("--set") + 1]
        if name == "jsonl":
            dataset_path = JSONL_DATASET_PATH
        else:
            dataset_path = Path(name)
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    questions = load_dataset(dataset_path)
    if limit:
        questions = questions[:limit]
    print(f"running eval on {len(questions)} questions (delay {delay}s)...", flush=True)
    report = run_eval(questions, write_baseline=not as_json, progress=True, delay_s=delay)
    if as_json:
        print(json.dumps(report, indent=2))
        return
    print(f"questions : {report['total_questions']}  (scored {report['scored_questions']}, errors {report['errors']})")
    print(f"correct   : {report['correctness']:.1%}")
    print(f"hallucin. : {report['hallucination_rate']:.1%}")
    print(f"citations : {_pct(report['citation_accuracy'])}")
    print(f"recall    : {_pct(report['retrieval_recall'])}")
    print(f"latency   : avg {report['latency_s']['avg']}s p95 {report['latency_s']['p95']}s")
    print(f"tokens    : {report['usage']['prompt_tokens']}p / {report['usage']['completion_tokens']}c, {report['usage']['calls']} calls")
    print(f"cost      : ${report['estimated_cost_usd']}")
    print(f"baseline  : {BASELINE_PATH}")


if __name__ == "__main__":
    main()