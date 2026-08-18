"""Entailment Check (stub) — the first SEMANTIC (llm_judge) check. Does the cited evidence SUPPORT
the claim, not merely share a topic? The judge is INJECTED (a callable) so the core stays LLM-
provider-agnostic and fully testable without an API; the real judge adopts Noesis/Eigen's
`_ENTAIL_SYSTEM` prompt over the OpenAI boundary (Python-canonical).

Panel invariants baked in:
  * a judge returns supported | violated | abstain (+confidence +reason) — NEVER a bare bool;
  * FAIL-SAFE — any error, malformed output, or below-floor confidence → abstain, never a guess;
  * llm_judge findings NEVER auto-drop (the policy layer holds/flags them; only deterministic
    checks drop). abstain is a deferral the surface policy resolves.
"""
from __future__ import annotations
from typing import List, Protocol, runtime_checkable

from ..finding import Finding, ContentSpan
from ..manifest import GateManifest, DEFAULT_MANIFEST

VERDICTS = ("supported", "violated", "abstain")
_MAP = {"supported": "in_corpus", "violated": "false", "abstain": "abstain"}


@runtime_checkable
class EntailmentJudge(Protocol):
    def __call__(self, claim_text: str, evidence_texts: List[str]) -> dict:
        """Return {'verdict': 'supported'|'violated'|'abstain', 'confidence': float, 'reason': str}."""
        ...


def abstaining_judge(claim_text: str, evidence_texts: List[str]) -> dict:
    """Default when no real judge is wired: ABSTAIN — never guesses 'supported'. On compliance
    abstain→hold, on marketing abstain→flag, so nothing ships as verified without a real judge."""
    return {"verdict": "abstain", "confidence": 0.0, "reason": "no entailment judge configured"}


class EntailmentCheck:
    id = "entailment-judge"
    dimension = "entailment"
    kind = "llm_judge"

    def __init__(self, judge: EntailmentJudge = abstaining_judge, min_confidence: float = 0.0):
        self.judge = judge
        self.min_confidence = min_confidence

    def run(self, claims: list, evidence: dict, manifest: GateManifest = DEFAULT_MANIFEST) -> List[Finding]:
        surface = evidence.get("surface", "compliance")
        floor = max(self.min_confidence, manifest.min_confidence)
        out: List[Finding] = []
        for c in claims:
            ev = c.get("evidence_texts") or evidence.get("evidence_texts", [])
            conf = None
            try:
                r = self.judge(c["text"], ev)
                verdict = r.get("verdict")
                conf = r.get("confidence")
                if verdict not in VERDICTS:
                    verdict = "abstain"
                # a non-abstain verdict below the confidence floor becomes abstain (calibration, not a guess)
                if verdict != "abstain" and conf is not None and conf < floor:
                    verdict = "abstain"
                grounded = _MAP[verdict]
                reason = r.get("reason", "")
            except Exception as e:  # fail-safe: never raise into the gate
                grounded, conf, reason = "abstain", 0.0, "judge_error:%s" % type(e).__name__
            out.append(Finding(
                check_id=self.id, dimension=self.dimension, kind=self.kind,
                span=ContentSpan(text=c.get("text", "?"), surface=surface),
                groundedness=grounded, severity="high" if grounded == "false" else "low",
                confidence=conf, reason=reason, source_locators=tuple(c.get("source_locators", [])),
            ))
        return out
