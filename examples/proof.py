"""fides — an EXTENSIVE proof that the machinery works across diverse domains and content types.

Two halves, both deterministic (no API key), both fully reproducible:

  PART A — Grounded production. Six domain datasets (finance, clinical, climate, SaaS, sports,
           elections). For each, fides brainstorms a POST, an INFOGRAPHIC, and a VIDEO TRANSCRIPT
           from the typed data. Every number is verified against the source → assets ship at 100%.

  PART B — Adversarial gate. A battery of hand-crafted distortions spanning the failure modes fides
           exists to catch — wrong-but-real cell, unit swap, period swap, derived-recompute mismatch,
           cross-subject leakage, verbatim mismatch — each paired with a GENUINE control. The proof:
           every genuine claim is KEPT and every fabricated one is DROPPED (fabrication escapes = 0).

Run:  python3 examples/proof.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fides import ContentStudio, Gate, NumericCheck
from fides.manifest import GateManifest, DEFAULT_MANIFEST
from fides.numeric import ledger

mf = ledger.materialize_fact
STUDIO = ContentStudio(Gate(checks=[NumericCheck()]))


def facts(rows):
    return {r["id"]: mf(r) for r in rows}


# ---- PART A: six diverse domains ----------------------------------------------------------------
DOMAINS = [
    ("Apex Growth Fund — FY2024", facts([
        {"id": "ret", "value": "12.4%", "subject": "Apex Growth", "metric": "net return", "period": "FY2024", "locatorText": "Apex returned 12.4% net of fees in FY2024."},
        {"id": "aum", "value": "$1.2B", "subject": "Apex Growth", "metric": "AUM", "period": "FY2024", "locatorText": "AUM reached $1.2B at year-end 2024."},
        {"id": "exp", "value": "65 bps", "subject": "Apex Growth", "metric": "expense ratio", "locatorText": "Expense ratio is 65 bps."},
    ])),
    ("Phase III trial — Drug DX-12", facts([
        {"id": "arr", "value": "34%", "subject": "DX-12", "metric": "absolute risk reduction", "period": "52 weeks", "locatorText": "DX-12 cut major events by 34% over 52 weeks."},
        {"id": "dose", "value": "100 mg", "subject": "DX-12", "metric": "daily dose", "locatorText": "Dosed at 100 mg once daily."},
        {"id": "n", "value": "4,182", "subject": "DX-12 trial", "metric": "enrollment", "locatorText": "4,182 patients enrolled."},
    ])),
    ("Grid decarbonization — 2024", facts([
        {"id": "solar", "value": "18.6 GW", "subject": "state grid", "metric": "solar capacity", "period": "2024", "locatorText": "Solar capacity hit 18.6 GW in 2024."},
        {"id": "cut", "value": "27%", "subject": "state grid", "metric": "emissions cut vs 2019", "period": "2024", "locatorText": "Emissions fell 27% versus 2019."},
        {"id": "price", "value": "$41/MWh", "subject": "state grid", "metric": "avg clearing price", "period": "2024", "locatorText": "Average clearing price was $41/MWh."},
    ])),
    ("NorthStar SaaS — Q4", facts([
        {"id": "arr", "value": "$48M", "subject": "NorthStar", "metric": "ARR", "period": "Q4-2024", "locatorText": "ARR crossed $48M in Q4."},
        {"id": "ndr", "value": "121%", "subject": "NorthStar", "metric": "net dollar retention", "period": "Q4-2024", "locatorText": "NDR held at 121%."},
        {"id": "churn", "value": "1.8%", "subject": "NorthStar", "metric": "gross monthly churn", "period": "Q4-2024", "locatorText": "Gross monthly churn was 1.8%."},
    ])),
    ("Striker FC — 2024 season", facts([
        {"id": "goals", "value": "89", "subject": "Striker FC", "metric": "goals scored", "period": "2024", "locatorText": "Struck 89 goals across the season."},
        {"id": "pts", "value": "78", "subject": "Striker FC", "metric": "points", "period": "2024", "locatorText": "Finished on 78 points."},
        {"id": "xg", "value": "1.94", "subject": "Striker FC", "metric": "xG per match", "period": "2024", "locatorText": "Averaged 1.94 xG per match."},
    ])),
    ("Metro ballot measure — 2024", facts([
        {"id": "yes", "value": "58.3%", "subject": "Measure 7", "metric": "yes vote share", "period": "2024", "locatorText": "Measure 7 passed with 58.3% yes."},
        {"id": "turn", "value": "62%", "subject": "Metro county", "metric": "turnout", "period": "2024", "locatorText": "Turnout was 62%."},
        {"id": "margin", "value": "94,204", "subject": "Measure 7", "metric": "vote margin", "period": "2024", "locatorText": "Passed by 94,204 votes."},
    ])),
]


def part_a():
    print("=" * 92)
    print("PART A — grounded production across 6 domains (post + infographic + video transcript)")
    print("=" * 92)
    all_ship = True
    for title, F in DOMAINS:
        assets = STUDIO.run(F, title, formats=("post", "image", "video"))
        by = {a.format: a for a in assets}
        ship = all(a.shippable for a in assets)
        all_ship &= ship
        print("\n### %s   [%s, %d figures each verified to source]"
              % (title, "ALL SHIPPABLE" if ship else "HELD", by["image"].audit["summary"]["total"]))
        print("  POST      : %s" % by["post"].spec["text"])
        print("  INFOGRAPHIC: " + " · ".join("%s %s" % (s["label"], s["value"]) for s in by["image"].spec["stats"]))
        vt = " ".join(sc.get("title") or ("%s, %s." % (sc["label"], sc["value"])) for sc in by["video"].spec["scenes"])
        print("  VIDEO VO   : " + vt)
    print("\n>>> PART A: every asset in every domain shipped at 100%% grounding: %s" % ("YES" if all_ship else "NO"))
    return all_ship


# ---- PART B: adversarial battery (genuine control + matched distortion) --------------------------
# Shared fact table the crafted claims bind against.
BF = facts([
    {"id": "r23", "value": "10.0%", "subject": "FundA", "metric": "return", "period": "2023"},
    {"id": "r24", "value": "12.4%", "subject": "FundA", "metric": "return", "period": "2024"},
    {"id": "exp", "value": "65 bps", "subject": "FundA", "metric": "expense ratio"},
    {"id": "peer", "value": "8.0%", "subject": "FundB", "metric": "return", "period": "2024"},
    {"id": "dose", "value": "100 mg", "subject": "DrugX", "metric": "dose"},
])

STRICT = GateManifest(**{**DEFAULT_MANIFEST.__dict__,
                         "strict_surfaces": ("compliance",), "require_period_surfaces": ("compliance",),
                         "verbatim_surfaces": ("compliance",)})
GATE = Gate(checks=[NumericCheck()], manifest=STRICT)


def _span(sid, emitted, binding, ctx):
    return {"id": sid, "surface": "compliance", "facts_by_id": BF,
            "numeric_claims": [{"emitted": emitted, "binding": binding, "context": dict({"surface": "compliance"}, **ctx)}]}


# (label, mode, expect_keep, span)
CASES = [
    ("finance: report FundA 2024 return", "genuine (direct)", True,
     _span("c1", "12.4%", {"kind": "source", "factId": "r24"}, {"subject": "FundA", "metric": "return", "period": "2024"})),
    ("finance: cite peer's number as FundA's", "WRONG-CELL (real value, wrong subject)", False,
     _span("c2", "8.0%", {"kind": "source", "factId": "r24"}, {"subject": "FundA", "metric": "return", "period": "2024"})),

    ("cost: state expense ratio 65 bps", "genuine (unit-aware)", True,
     _span("c3", "65 bps", {"kind": "source", "factId": "exp"}, {"subject": "FundA", "metric": "expense ratio"})),
    ("cost: inflate 65 bps -> '65%'", "UNIT SWAP (bps read as %)", False,
     _span("c4", "65%", {"kind": "source", "factId": "exp"}, {"subject": "FundA", "metric": "expense ratio"})),

    ("period: label the 2024 figure as 2024", "genuine (period-matched)", True,
     _span("c5", "12.4%", {"kind": "source", "factId": "r24"}, {"subject": "FundA", "metric": "return", "period": "2024"})),
    ("period: label the 2024 figure as 2023", "PERIOD SWAP (right value, wrong year)", False,
     _span("c6", "12.4%", {"kind": "source", "factId": "r24"}, {"subject": "FundA", "metric": "return", "period": "2023"})),

    ("derived: YoY growth of FundA (10.0->12.4)", "genuine (recomputed)", True,
     _span("c7", "24%", {"kind": "derived", "derivation": {"op": "growth_pct", "operandFactIds": ["r23", "r24"]}}, {"subject": "FundA"})),
    ("derived: 'growth' mixing FundB into FundA", "DERIVED CROSS-SUBJECT (incoherent operands)", False,
     _span("c8", "55%", {"kind": "derived", "derivation": {"op": "growth_pct", "operandFactIds": ["peer", "r24"]}}, {"subject": "FundA"})),

    ("clinical: state the 100 mg dose", "genuine (dose)", True,
     _span("c9", "100 mg", {"kind": "source", "factId": "dose"}, {"subject": "DrugX", "metric": "dose"})),
    ("clinical: 100 mg printed as '100 mcg'", "UNIT SWAP (1000x dose error)", False,
     _span("c10", "100 mcg", {"kind": "source", "factId": "dose"}, {"subject": "DrugX", "metric": "dose"})),

    ("compliance: verbatim 12.4%", "genuine (verbatim)", True,
     _span("c11", "12.4%", {"kind": "source", "factId": "r24"}, {"subject": "FundA", "metric": "return", "period": "2024"})),
    ("compliance: restate as '12.40%'", "VERBATIM MISMATCH (altered under strict)", False,
     _span("c12", "12.40%", {"kind": "source", "factId": "r24"}, {"subject": "FundA", "metric": "return", "period": "2024"})),

    ("fabrication: a number in no cell", "FABRICATED (unbound, absent)", False,
     _span("c13", "300%", {"kind": "unbound"}, {"subject": "FundA", "metric": "return"})),
]


def part_b():
    print("\n" + "=" * 92)
    print("PART B — adversarial gate: genuine controls KEPT, distortions DROPPED (escapes must be 0)")
    print("=" * 92)
    print("  %-42s %-38s %-7s %s" % ("case", "mode", "expect", "verdict"))
    print("  " + "-" * 88)
    escapes = recall_losses = 0
    for label, mode, keep, span in CASES:
        rep = GATE.run([span])
        d = rep.decisions[0]
        code = span["numeric_claims"][0]  # for reason
        reason = d.action  # action drop/flag/allow
        published = d.published
        ok = (published == keep)
        if keep and not published:
            recall_losses += 1
        if (not keep) and published:
            escapes += 1
        mark = "✓" if ok else "✗ MISS"
        verdict = ("KEPT" if published else "DROPPED")
        print("  %-42s %-38s %-7s %-8s %s" % (label[:42], mode[:38], "keep" if keep else "drop", verdict, mark))
    total = len(CASES)
    genuine = sum(1 for c in CASES if c[2])
    fab = total - genuine
    print("  " + "-" * 88)
    print("  genuine kept : %d/%d      fabricated dropped : %d/%d      FABRICATION ESCAPES : %d"
          % (genuine - recall_losses, genuine, fab - escapes, fab, escapes))
    return escapes == 0 and recall_losses == 0


if __name__ == "__main__":
    a = part_a()
    b = part_b()
    print("\n" + "=" * 92)
    print("RESULT: PART A grounded-production %s | PART B adversarial-gate %s"
          % ("PASS" if a else "FAIL", "PASS (escapes=0, no genuine lost)" if b else "FAIL"))
    print("=" * 92)
    sys.exit(0 if (a and b) else 1)
