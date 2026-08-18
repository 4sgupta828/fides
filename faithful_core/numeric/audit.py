"""Audit export — the compliance artifact ('source documentation for figures'). Pure; caller stamps
the time. Records verified figures (emitted → source cell → verbatim locator → derivation) AND
withheld ones with the typed reason."""
from __future__ import annotations
from typing import List

from ..manifest import UnitVocab, DEFAULT_VOCAB
from . import ledger


def build_audit_report(claims: list, facts_by_id: dict, opts: dict = None, vocab: UnitVocab = DEFAULT_VOCAB) -> dict:
    opts = opts or {}
    entries = []
    by_code = {}
    for c in claims:
        v = ledger.verify_claim(c, facts_by_id, opts, vocab)
        by_code[v["code"]] = by_code.get(v["code"], 0) + 1
        srcs = []
        for fid in v["bound_fact_ids"]:
            f = facts_by_id.get(fid)
            if f:
                srcs.append({"fact_id": f["id"], "locator": f["locatorText"],
                             "subject": f["entity"]["subject"], "metric": f["entity"]["metric"],
                             "period": f["period"]["raw"] or f["period"]["kind"]})
        entries.append({
            "emitted": c["emitted"], "status": "verified" if v["ok"] else "withheld",
            "code": v["code"], "method": c["binding"]["kind"], "sources": srcs,
            "derivation": (c["binding"].get("derivation") if c["binding"]["kind"] == "derived" else None),
        })
    verified = sum(1 for e in entries if e["status"] == "verified")
    return {"summary": {"total": len(entries), "verified": verified,
                        "withheld": len(entries) - verified, "by_code": by_code},
            "entries": entries}


def render_audit_markdown(report: dict, title: str = "", stamped_at: str = "") -> str:
    L = ["# Numeric Source Documentation" + (" — " + title if title else "")]
    if stamped_at:
        L.append("_Generated %s_" % stamped_at)
    s = report["summary"]
    L.append("")
    L.append("**%d/%d figures verified against source cells; %d withheld.**" % (s["verified"], s["total"], s["withheld"]))
    L.append("")
    L.append("| Figure | Status | Basis | Source cell (verbatim locator) |")
    L.append("|---|---|---|---|")
    for e in report["entries"]:
        if e["status"] == "verified":
            basis = ("%s(%s)" % (e["derivation"]["op"], ", ".join(e["derivation"]["operandFactIds"]))
                     if e["derivation"] else "direct")
            loc = " + ".join("%s · %s: \"%s\"" % (x["subject"], x["metric"], x["locator"]) for x in e["sources"]) or "—"
            L.append("| %s | ✓ verified | %s | %s |" % (e["emitted"], basis, loc.replace("|", "\\|")))
        else:
            L.append("| %s | ✗ withheld (%s) | — | — |" % (e["emitted"], e["code"]))
    return "\n".join(L)
