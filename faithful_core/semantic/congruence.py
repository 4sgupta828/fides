"""Congruence Check (stub) — the anti-MISATTRIBUTION + anti-OVER-GENERALIZATION check, mirroring
Noesis/Eigen's 3-axis binding judge (`on_subject` / `kind_ok`). One claim yields up to TWO findings
on the same span — dimension 'attribution' (is the number/quote about the subject the evidence is
actually about?) and 'overgeneralization' (does the claim's assertion-kind match the evidence's
kind, or broaden beyond it?). The judge is injected; fail-safe → abstain; llm_judge never auto-drops.
"""
from __future__ import annotations
from typing import List, Protocol, runtime_checkable

from ..finding import Finding, ContentSpan
from ..manifest import GateManifest, DEFAULT_MANIFEST

VERDICTS = ("supported", "violated", "abstain")
_MAP = {"supported": "in_corpus", "violated": "false", "abstain": "abstain"}


@runtime_checkable
class CongruenceJudge(Protocol):
    def __call__(self, claim_text: str, evidence_texts: List[str]) -> dict:
        """Return {'on_subject': verdict, 'kind_ok': verdict, 'confidence': float, 'reason': str}
        where verdict ∈ supported|violated|abstain."""
        ...


def abstaining_congruence_judge(claim_text: str, evidence_texts: List[str]) -> dict:
    return {"on_subject": "abstain", "kind_ok": "abstain", "confidence": 0.0, "reason": "no congruence judge configured"}


class CongruenceCheck:
    id = "congruence-judge"
    kind = "llm_judge"
    # emits findings on these two dimensions
    dimension = "attribution"  # primary; also emits 'overgeneralization'

    def __init__(self, judge: CongruenceJudge = abstaining_congruence_judge, min_confidence: float = 0.0):
        self.judge = judge
        self.min_confidence = min_confidence

    def _finding(self, claim, surface, dimension, verdict, conf, reason):
        if verdict not in VERDICTS:
            verdict = "abstain"
        if verdict != "abstain" and conf is not None and conf < self.min_confidence:
            verdict = "abstain"
        g = _MAP[verdict]
        return Finding(check_id=self.id, dimension=dimension, kind=self.kind,
                       span=ContentSpan(text=claim.get("text", "?"), surface=surface),
                       groundedness=g, severity="high" if g == "false" else "low",
                       confidence=conf, reason=reason, source_locators=tuple(claim.get("source_locators", [])))

    def run(self, claims: list, evidence: dict, manifest: GateManifest = DEFAULT_MANIFEST) -> List[Finding]:
        surface = evidence.get("surface", "compliance")
        floor = max(self.min_confidence, manifest.min_confidence)
        self.min_confidence = floor
        out: List[Finding] = []
        for c in claims:
            ev = c.get("evidence_texts") or evidence.get("evidence_texts", [])
            try:
                r = self.judge(c["text"], ev)
                conf = r.get("confidence")
                out.append(self._finding(c, surface, "attribution", r.get("on_subject"), conf, r.get("reason", "")))
                out.append(self._finding(c, surface, "overgeneralization", r.get("kind_ok"), conf, r.get("reason", "")))
            except Exception as e:  # fail-safe
                for dim in ("attribution", "overgeneralization"):
                    out.append(Finding(check_id=self.id, dimension=dim, kind=self.kind,
                                       span=ContentSpan(text=c.get("text", "?"), surface=surface),
                                       groundedness="abstain", severity="medium", confidence=0.0,
                                       reason="judge_error:%s" % type(e).__name__))
        return out
