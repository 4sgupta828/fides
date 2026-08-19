"""End-to-end proof: every fides subsystem on one coherent scenario (an asset-manager fund answer).
Run: python3 examples/end_to_end.py   (uses real OpenAI judges if OPENAI_API_KEY is set, else a
deterministic fallback — so it runs for anyone). Each block prints what happened and why."""
import os

from fides import (
    Gate, NumericCheck, EntailmentCheck, CongruenceCheck, QuoteCheck,
    build_audit_report, render_audit_markdown, run_gate_eval, format_gate_eval, format_gate_report,
    assess_slop, GroundedGenerator, verify_span, GateManifest, leaked_values,
)
from fides.numeric import ledger

USE_LLM = bool(os.environ.get("OPENAI_API_KEY"))
if USE_LLM:
    from fides.adapters.openai_judge import make_openai_entailment_judge, make_openai_congruence_judge
    entail_judge = make_openai_entailment_judge()
    congru_judge = make_openai_congruence_judge()
    JUDGE = "REAL gpt-4o-mini"
else:
    entail_judge = lambda t, e: {"verdict": "violated", "confidence": 0.9, "reason": "unsupported"} if ("best" in t.lower() or "guarantee" in t.lower()) else {"verdict": "supported", "confidence": 0.9, "reason": "entailed"}
    congru_judge = lambda t, e: {"on_subject": "violated", "kind_ok": "supported", "confidence": 0.9, "reason": "wrong subject"} if "sitagliptin" in t.lower() else {"on_subject": "supported", "kind_ok": "supported", "confidence": 0.9, "reason": "ok"}
    JUDGE = "deterministic fallback (no key)"


def hdr(n, t):
    print("\n" + "=" * 78 + "\n%s. %s\n" % (n, t) + "-" * 78)


# ---- source evidence (Layer 1): typed Fact cells extracted from the fund's commentary -----------
F = {f["id"]: f for f in [
    ledger.materialize_fact({"id": "ret", "value": "12.4%", "subject": "Apex", "metric": "net return", "period": "FY2024", "locatorText": "Apex Growth returned 12.4% net of fees in FY2024."}),
    ledger.materialize_fact({"id": "aum23", "value": "$950M", "subject": "Apex", "metric": "AUM", "period": "FY2023", "locatorText": "AUM was $950M at the end of 2023."}),
    ledger.materialize_fact({"id": "aum24", "value": "$1.2B", "subject": "Apex", "metric": "AUM", "period": "FY2024", "locatorText": "AUM reached $1.2B by year-end 2024."}),
    ledger.materialize_fact({"id": "exp", "value": "65 bps", "subject": "Apex", "metric": "expense ratio", "locatorText": "The fund's expense ratio is 65 bps."}),
    ledger.materialize_fact({"id": "bmk", "value": "9.8%", "subject": "benchmark", "metric": "return", "period": "FY2024", "locatorText": "The benchmark returned 9.8% over the same period."}),
]}
PASSAGE = "Apex Growth returned 12.4% net of fees in FY2024, beating its benchmark's 9.8% return."
ALL_EVIDENCE = [PASSAGE] + [f["locatorText"] for f in F.values()]

print("Semantic judge:", JUDGE)

# ================================================================================================
hdr(1, "NUMERIC LEDGER — direct, derived, and every failure mode")
def num(label, emitted, binding, **ctx):
    v = ledger.verify_claim({"emitted": emitted, "binding": binding, "context": dict({"surface": "cell"}, **ctx)}, F, ctx.pop("_opts", {}) or {})
    print("  %-42s %-6s %s" % (label, "OK" if v["ok"] else "DROP", "" if v["ok"] else "(%s)" % v["code"]))

num("direct 12.4% net return", "12.4%", {"kind": "source", "factId": "ret"}, subject="Apex", metric="net return")
num("derived AUM growth 26% (950M→1.2B)", "26%", {"kind": "derived", "derivation": {"op": "growth_pct", "operandFactIds": ["aum23", "aum24"]}}, subject="Apex")
num("WRONG CELL: expense-ratio value as 'net return'", "0.65%", {"kind": "source", "factId": "exp"}, subject="Apex", metric="net return")
num("unit swap: $12.4M vs a % fact", "$12.4M", {"kind": "source", "factId": "ret"}, subject="Apex", metric="net return")
num("period swap: FY figure shown as Q2", "12.4%", {"kind": "source", "factId": "ret"}, subject="Apex", metric="net return", period="Q2 2024")
num("fabricated: 18% with no source", "18%", {"kind": "unbound"})
num("cross-subject spread (Apex - benchmark) incoherent", "2.6%", {"kind": "derived", "derivation": {"op": "difference", "operandFactIds": ["ret", "bmk"]}})
# verbatim / display-drift: 0.65% is canonically equal to 65 bps but NOT the exact source string
v_ok = ledger.verify_claim({"emitted": "0.65%", "binding": {"kind": "source", "factId": "exp"}, "context": {"surface": "cell", "subject": "Apex", "metric": "expense ratio"}}, F, {})
v_vb = ledger.verify_claim({"emitted": "0.65%", "binding": {"kind": "source", "factId": "exp"}, "context": {"surface": "cell", "subject": "Apex", "metric": "expense ratio"}}, F, {"verbatim": True})
print("  %-42s %-6s / verbatim %-4s %s" % ("verbatim: 0.65% vs a '65 bps' cell", "OK" if v_ok["ok"] else "DROP", "OK" if v_vb["ok"] else "DROP", "(%s)" % v_vb["code"] if not v_vb["ok"] else ""))

# ================================================================================================
hdr(2, "QUOTE SPAN GATE — deterministic, LLM-free")
for label, quote in [("real quote (fuzzy-tolerant)", "returned 12.4% net of fees in FY 2024"),
                     ("fabricated quote", "guaranteed a 30% return to every investor")]:
    r = verify_span(PASSAGE, quote)
    print("  %-42s %-8s (%s)" % (label, "GROUND" if r["verified"] else "ABSENT", r["method"]))

# ================================================================================================
hdr(3, "SEMANTIC JUDGES — entailment + congruence (%s)" % JUDGE)
for label, text in [("supported inference", "Apex beat its benchmark"),
                    ("unsupported superlative", "Apex is the best-performing fund in the world")]:
    r = entail_judge(text, [PASSAGE])
    print("  entailment: %-32s -> %-9s %s" % (label, r["verdict"], r.get("reason", "")[:34]))
c = congru_judge("Sitagliptin requires no renal dose adjustment", ["Metformin should be dose-adjusted in renal impairment."])
print("  congruence: sitagliptin/metformin       -> on_subject=%s (%s)" % (c["on_subject"], c.get("reason", "")[:34]))

# ================================================================================================
hdr(4, "UNIFIED GATE — one verdict across all checks over a generated answer")
gate = Gate(checks=[NumericCheck(), EntailmentCheck(judge=entail_judge)])
def span(id, text, emitted, binding, **ctx):
    return {"id": id, "surface": "compliance", "text": text, "facts_by_id": F, "evidence_texts": ALL_EVIDENCE,
            "numeric_claims": [{"emitted": emitted, "binding": binding, "context": dict({"surface": "compliance"}, **ctx)}]}
answer = [
    span("s1", "Apex returned 12.4% net in FY2024.", "12.4%", {"kind": "source", "factId": "ret"}, subject="Apex", metric="net return", period="FY2024"),
    span("s2", "Apex grew its assets year over year.", "26%", {"kind": "derived", "derivation": {"op": "growth_pct", "operandFactIds": ["aum23", "aum24"]}}, subject="Apex"),
    span("s3", "Apex delivered a 20% return.", "20%", {"kind": "unbound"}),
    span("s4", "Apex is the best fund ever.", "12.4%", {"kind": "source", "factId": "ret"}, subject="Apex", metric="net return"),
]
print(format_gate_report(gate.run(answer)))

# ================================================================================================
hdr(5, "PROSE VALUE-LEAK AUDIT — a withheld number must not survive in the prose")
leak_spans = [
    span("keep", "Apex returned 12.4%, with peers reportedly near 30%.", "12.4%", {"kind": "source", "factId": "ret"}, subject="Apex", metric="net return"),
    span("peer", "Peers returned 30%.", "30%", {"kind": "unbound"}),  # 30% dropped as a claim...
]
rep = Gate(checks=[NumericCheck()]).run(leak_spans)  # numeric-only: isolate the value-leak mechanic
print("  peer '30%' claim:", "published" if rep.decisions[1].published else "WITHHELD",
      "| leaked_values (survived in published prose):", rep.summary["leaked_values"])

# ================================================================================================
hdr(6, "FAIL-CLOSED COVERAGE — an unverifiable span does not silently publish")
r = gate.run([{"id": "x", "surface": "compliance", "text": "Something asserted with nothing to check it."}])
print("  uncheckable span ->", r.decisions[0].action, "(published=%s)" % r.decisions[0].published)

# ================================================================================================
hdr(7, "ANTI-SLOP — separate quality track (never drops on truth)")
for label, t in [("sloppy", "In today's fast-paced world, it's important to note that AI plays a crucial role. Let's dive into this rich tapestry."),
                 ("concrete", "Apex returned 12.4% net in FY2024, beating the 9.8% benchmark by 2.6 points.")]:
    s = assess_slop(t)
    print("  %-9s slop_score=%.2f is_slop=%s flags=%d" % (label, s["score"], s["is_slop"], len(s["flags"])))

# ================================================================================================
hdr(8, "GROUNDED GENERATION — plan -> draft -> verify -> repair (verifier as critic)")
def drafter(intent):
    return span(intent["id"], "Apex returned 15%.", "15%", {"kind": "source", "factId": "ret"}, subject="Apex", metric="net return")  # fabricated 15%
def repairer(intent, sp, decision):
    return span(intent["id"], "Apex returned 12.4% net.", "12.4%", {"kind": "source", "factId": "ret"}, subject="Apex", metric="net return")  # fixed to source
res = GroundedGenerator(gate, drafter, repairer, max_repairs=2).generate([{"id": "c1"}])
print("  fabricated draft '15%' ->", "repairs=%d ->" % res.repair_count, repr(res.text))

# ================================================================================================
hdr(9, "PRECISION / RECALL HARNESS — dimension x surface-tier matrix (Wilson CIs)")
from fides.finding import Finding, ContentSpan
def fnd(dim, kind, g): return Finding(check_id="c", dimension=dim, kind=kind, span=ContentSpan("x", "compliance"), groundedness=g, severity="high")
spans_labeled = [
    {"id": "n1", "dimension": "numeric", "truth": "in_corpus", "findings": [fnd("numeric", "deterministic", "in_corpus")]},
    {"id": "n2", "dimension": "numeric", "truth": "false", "findings": [fnd("numeric", "deterministic", "false")]},
    {"id": "e1", "dimension": "entailment", "truth": "false", "findings": [fnd("entailment", "llm_judge", "in_corpus")]},  # judge miss
]
print(format_gate_eval(run_gate_eval(spans_labeled)))

# ================================================================================================
hdr(10, "AUDIT EXPORT — FINRA-style 'source documentation for figures'")
audit_claims = [
    {"emitted": "12.4%", "binding": {"kind": "source", "factId": "ret"}, "context": {"surface": "compliance", "subject": "Apex", "metric": "net return"}},
    {"emitted": "26%", "binding": {"kind": "derived", "derivation": {"op": "growth_pct", "operandFactIds": ["aum23", "aum24"]}}, "context": {"surface": "compliance", "subject": "Apex"}},
    {"emitted": "20%", "binding": {"kind": "unbound"}, "context": {"surface": "compliance"}},
]
print(render_audit_markdown(build_audit_report(audit_claims, F), title="Apex Q4", stamped_at="2026-08-19"))
