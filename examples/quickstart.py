"""Quickstart — verify a mini research answer against its evidence with ONE Gate call.
Run: python3 examples/quickstart.py   (no API key needed; uses a deterministic demo judge.)"""
from fides import Gate, NumericCheck, EntailmentCheck, format_gate_report
from fides.numeric import ledger

# 1. Evidence extracted from the source corpus (Layer 1) — typed Fact cells.
facts = {f["id"]: f for f in [
    ledger.materialize_fact({"id": "f1", "value": "12.4%", "subject": "Apex", "metric": "net return",
                             "period": "FY2024", "locatorText": "Apex Growth returned 12.4% net of fees in FY2024."}),
    ledger.materialize_fact({"id": "f2", "value": "$950M", "subject": "Apex", "metric": "AUM",
                             "period": "FY2023", "locatorText": "AUM was $950M at the end of 2023."}),
    ledger.materialize_fact({"id": "f3", "value": "$1.2B", "subject": "Apex", "metric": "AUM",
                             "period": "FY2024", "locatorText": "AUM reached $1.2B by year-end 2024."}),
]}

# 2. A deterministic demo "judge" (swap for fides.adapters.openai_judge.make_openai_entailment_judge()).
def demo_judge(text, evidence):
    if "best" in text.lower() or "guarantee" in text.lower():
        return {"verdict": "violated", "confidence": 0.9, "reason": "unsupported superlative/claim"}
    return {"verdict": "supported", "confidence": 0.9, "reason": "entailed by evidence"}

gate = Gate(checks=[NumericCheck(), EntailmentCheck(judge=demo_judge)])

# 3. The generated answer, one span per claim.
def span(id, text, emitted, binding, ctx):
    return {"id": id, "surface": "compliance", "text": text, "facts_by_id": facts,
            "numeric_claims": [{"emitted": emitted, "binding": binding,
                                "context": dict({"surface": "compliance"}, **ctx)}],
            "evidence_texts": [f["locatorText"] for f in facts.values()]}

spans = [
    span("s1", "Apex returned 12.4% net in FY2024.", "12.4%", {"kind": "source", "factId": "f1"},
         {"subject": "Apex", "metric": "net return", "period": "FY2024"}),
    span("s2", "Apex grew AUM 26% year over year.", "26%",
         {"kind": "derived", "derivation": {"op": "growth_pct", "operandFactIds": ["f2", "f3"]}}, {"subject": "Apex"}),
    span("s3", "Apex delivered a 20% return.", "20%", {"kind": "unbound"}, {}),          # fabricated number
    span("s4", "Apex is the best fund ever.", "12.4%", {"kind": "source", "factId": "f1"},
         {"subject": "Apex", "metric": "net return"}),                                   # unsupported superlative
]

print(format_gate_report(gate.run(spans)))
