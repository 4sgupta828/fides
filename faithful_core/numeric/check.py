"""NumericCheck — adapts the numeric ledger to the shared Check/Finding interface. Deterministic:
a verified number → in_corpus; any typed failure → false (a proven fabrication, which the policy
invariant always drops). Emits the source locators for the audit trail."""
from __future__ import annotations
from typing import List

from ..finding import Finding, ContentSpan
from ..manifest import GateManifest, DEFAULT_MANIFEST
from . import ledger


class NumericCheck:
    id = "numeric-ledger"
    dimension = "numeric"
    kind = "deterministic"

    def run(self, claims: list, evidence: dict, manifest: GateManifest = DEFAULT_MANIFEST) -> List[Finding]:
        facts_by_id = evidence.get("facts_by_id", {})
        surface = evidence.get("surface", "compliance")
        opts = {
            "strict": surface in manifest.strict_surfaces,
            "strict_period": surface in manifest.require_period_surfaces,
            "minConfidence": manifest.min_confidence,
            "rounding": evidence.get("rounding", True),
        }
        out: List[Finding] = []
        for c in claims:
            try:
                v = ledger.verify_claim(c, facts_by_id, opts, manifest.unit_vocab)
                out.append(Finding(
                    check_id=self.id, dimension=self.dimension, kind=self.kind,
                    span=ContentSpan(text=c["emitted"], surface=surface),
                    groundedness="in_corpus" if v["ok"] else "false",
                    severity="low" if v["ok"] else "high",
                    confidence=1.0, reason=v["code"], source_locators=tuple(v["locators"]),
                ))
            except Exception as e:  # fail-safe: never raise into the gate; abstain instead
                out.append(Finding(
                    check_id=self.id, dimension=self.dimension, kind=self.kind,
                    span=ContentSpan(text=c.get("emitted", "?"), surface=surface),
                    groundedness="abstain", severity="medium", confidence=0.0,
                    reason="check_error:%s" % type(e).__name__,
                ))
        return out
