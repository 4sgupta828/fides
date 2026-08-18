"""Evaluate a semantic JUDGE against a held-out labeled set — its OWN confusion matrix, before it's
trusted in the gate (panel: "do not evaluate an LLM judge using only another LLM judge"). Works with
any judge callable (a real OpenAI judge, or a deterministic fake in tests). No LLM dependency here.
"""
from __future__ import annotations
from typing import Callable, List


def run_entailment_eval(judge: Callable[[str, List[str]], dict], cases: List[dict]) -> dict:
    """`judge(claim, evidence) -> {'verdict': ...}`; `cases` = [{id, claim, evidence, expected}]."""
    rows = []
    confusion = {}
    correct = 0
    for c in cases:
        r = judge(c["claim"], c["evidence"])
        got = r.get("verdict", "abstain")
        exp = c["expected"]
        ok = got == exp
        correct += ok
        confusion[(exp, got)] = confusion.get((exp, got), 0) + 1
        rows.append({"id": c["id"], "expected": exp, "got": got, "ok": ok, "confidence": r.get("confidence")})

    # panel metrics: of the 'violated' the judge flagged, how many were truly violated (precision);
    # of truly-supported claims, how many the judge kept as supported (recall).
    flagged_violated = sum(1 for r in rows if r["got"] == "violated")
    true_violated_flagged = sum(1 for r in rows if r["got"] == "violated" and r["expected"] == "violated")
    true_supported = sum(1 for c in cases if c["expected"] == "supported")
    supported_kept = sum(1 for r in rows if r["expected"] == "supported" and r["got"] == "supported")
    return {
        "total": len(cases),
        "correct": correct,
        "accuracy": correct / len(cases) if cases else 1.0,
        "violated_precision": (true_violated_flagged / flagged_violated) if flagged_violated else None,
        "supported_recall": (supported_kept / true_supported) if true_supported else None,
        "confusion": confusion,
        "rows": rows,
    }


def format_entailment_eval(r: dict) -> str:
    L = ["Entailment judge eval — %d/%d correct (%.0f%%)" % (r["correct"], r["total"], r["accuracy"] * 100)]
    vp = "n/a" if r["violated_precision"] is None else "%.0f%%" % (r["violated_precision"] * 100)
    sr = "n/a" if r["supported_recall"] is None else "%.0f%%" % (r["supported_recall"] * 100)
    L.append("  violated-precision: %s   supported-recall: %s" % (vp, sr))
    for row in r["rows"]:
        mark = "OK " if row["ok"] else "XX "
        L.append("  %s %-28s exp=%-9s got=%s" % (mark, row["id"], row["expected"], row["got"]))
    return "\n".join(L)
