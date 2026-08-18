"""QuoteCheck — a DETERMINISTIC no-fabrication text gate. A quoted span survives only if it is
verbatim (fuzzy-tolerant) present in a CITED passage. LLM-free, so it grounds quotes without a judge
and without spend. Absorbed from factra's hard span-check; fills fides's empty 'quote'
dimension. A failure is a proven fabrication → the policy invariant drops it."""
from __future__ import annotations
from typing import List

from ..finding import Finding, ContentSpan
from ..manifest import GateManifest, DEFAULT_MANIFEST
from .span import verify_span_any


class QuoteCheck:
    id = "quote-span"
    dimension = "quote"
    kind = "deterministic"

    def run(self, claims: list, evidence: dict, manifest: GateManifest = DEFAULT_MANIFEST) -> List[Finding]:
        surface = evidence.get("surface", "compliance")
        default_passages = evidence.get("evidence_texts", [])
        out: List[Finding] = []
        for c in claims:
            quote = c.get("quote") or c.get("text")
            if not quote:
                continue
            passages = c.get("evidence_texts") or default_passages
            r = verify_span_any(passages, quote)
            verified = r["verified"]
            out.append(Finding(
                check_id=self.id, dimension=self.dimension, kind=self.kind,
                span=ContentSpan(text=quote, surface=surface),
                groundedness="in_corpus" if verified else "false",
                severity="low" if verified else "high",
                confidence=1.0, reason=r["method"],
                source_locators=tuple(c.get("source_locators", [])),
            ))
        return out
