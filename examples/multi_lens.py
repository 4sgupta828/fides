"""Multi-lens judge — perspective-diverse verification. Shows (1) a live catch: an over-generalized
fabrication a single pass rubber-stamps, that the adversarial lens catches; and (2) the P/R harness
A/B that gates it — 'unanimous' drives fabrication-escape to 0, 'any' trades it back for recall.
Run: python3 examples/multi_lens.py   (live part needs OPENAI_API_KEY; the A/B runs offline.)"""
import os
from fides import make_multi_lens_judge, EntailmentCheck, run_gate_eval

LENSES = [
    "LITERAL — does the evidence state or directly entail this, outright?",
    "ADVERSARIAL — actively try to find why the evidence does NOT support this; if you can, it is violated.",
    "SCOPE/PRECISION — does the claim over-generalize, or assert a specific/superlative the evidence does not show?",
]

# ---- (1) live catch (real judge) ----------------------------------------------------------------
if os.environ.get("OPENAI_API_KEY"):
    from fides.adapters.openai_judge import make_openai_entailment_judge
    base = make_openai_entailment_judge()
    multi = make_multi_lens_judge(base, LENSES, survival="unanimous")
    EV = ["Apex Growth returned 12.4% net of fees in FY2024, beating its benchmark's 9.8% return."]
    print("=== LIVE (gpt-4o-mini): single pass vs unanimous multi-lens ===")
    for claim in ["Apex outperformed its benchmark in FY2024.", "Apex is a top-tier fund."]:
        s = base(claim, EV)["verdict"]
        m = multi(claim, EV)
        print("  %-42s single=%-9s  multi=%-9s  lenses=%s" % (claim[:42], s, m["verdict"], m["lens_verdicts"]))
    print()
else:
    print("(set OPENAI_API_KEY for the live catch demo)\n")

# ---- (2) offline harness A/B — the ship-gate ----------------------------------------------------
SCRIPT = {("fab_sneaky", "LITERAL"): "supported", ("fab_sneaky", "ADVERSARIAL"): "abstain", ("fab_sneaky", "SCOPE"): "abstain",
          ("genuine_missed", "LITERAL"): "abstain", ("genuine_missed", "ADVERSARIAL"): "abstain", ("genuine_missed", "SCOPE"): "supported",
          ("clean_true", "LITERAL"): "supported", ("clean_true", "ADVERSARIAL"): "supported", ("clean_true", "SCOPE"): "supported"}
LK = ["LITERAL", "ADVERSARIAL", "SCOPE"]
def base_j(c, e):
    case = next(x for x in ("fab_sneaky", "genuine_missed", "clean_true") if x in c)
    lens = next((L for L in LK if L in c), "LITERAL")
    return {"verdict": SCRIPT[(case, lens)], "confidence": 0.9}
CASES = [("fab_sneaky", "false"), ("genuine_missed", "in_corpus"), ("clean_true", "in_corpus")]

def score(judge):
    chk = EntailmentCheck(judge=judge)
    spans = [{"id": c, "dimension": "entailment", "truth": t, "findings": chk.run([{"text": c, "evidence_texts": []}], {"surface": "compliance"})} for c, t in CASES]
    cell = next(x for x in run_gate_eval(spans)["cells"] if x["tier"] == "compliance")
    recall = (cell["should_publish"] - cell["recall_losses"]) / cell["should_publish"]
    return cell["escapes"], recall

print("=== HARNESS A/B (offline) — 1 fabrication + 2 genuine claims ===")
print("  %-24s escapes(must be 0)   genuine-recall" % "config")
for label, judge in [("single pass (literal)", base_j),
                     ("multi-lens UNANIMOUS", make_multi_lens_judge(base_j, LK, "unanimous")),
                     ("multi-lens ANY (opt-in)", make_multi_lens_judge(base_j, LK, "any"))]:
    e, r = score(judge)
    print("  %-24s %-19s %.0f%%%s" % (label, e, r * 100, "   <- ships (escape 0)" if (e == 0 and "UNAN" in label) else ("   <- escape!" if e else "")))
