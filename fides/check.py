"""The Check protocol — the plugin seam. Numeric is the first (deterministic); entailment/congruence/
slop join later (llm_judge, canonical in Python). Every check maps (claims, evidence, manifest) to
Findings; the policy layer composes them. Copy Noesis's runtime_checkable-Protocol discipline."""
from __future__ import annotations
from typing import List, Protocol, runtime_checkable

from .finding import Finding
from .manifest import GateManifest


@runtime_checkable
class Check(Protocol):
    id: str
    dimension: str
    kind: str  # 'deterministic' | 'llm_judge'

    def run(self, claims: list, evidence: dict, manifest: GateManifest) -> List[Finding]:
        """Verify emitted claims against evidence; return one Finding per claim. Fail-safe: on any
        internal error a check returns an `abstain` finding, never raises into the gate."""
        ...
