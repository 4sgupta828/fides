"""Grounded generation — the endgame, built the panel's way. NOT per-token/emit-time gating (that
explodes latency and forces extractive, hedged output). Instead the verifier is a CRITIC in a
claim-granular loop: plan → draft → verify(Gate) → repair. You constrain the PLAN (what claims to
make) and drive TARGETED REPAIR (Finding.reason is the repair instruction), bounded, then abstain.

drafter/repairer are INJECTED (an LLM in production; deterministic fakes in tests), so the loop is
fully testable offline and provider-agnostic — same discipline as the Checks.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .gate import Gate, SpanDecision


@dataclass
class GenStep:
    intent_id: str
    outcome: str          # 'accepted' | 'dropped'
    repairs: int
    final_action: str
    reason: str = ""


@dataclass
class GenResult:
    text: str
    accepted: List[dict]
    dropped: List[dict]
    trace: List[GenStep]

    @property
    def repair_count(self) -> int:
        return sum(s.repairs for s in self.trace)


# a drafter turns a claim intent into a Gate span; a repairer takes the failing span + decision and
# returns a revised span (using decision.driver_reason as the repair instruction).
Drafter = Callable[[dict], dict]
Repairer = Callable[[dict, dict, SpanDecision], dict]


# a slop_repairer takes (intent, accepted_span, slop_report) and returns a de-slopped span.
SlopRepairer = Callable[[dict, dict, dict], dict]


class GroundedGenerator:
    def __init__(self, gate: Gate, drafter: Drafter, repairer: Optional[Repairer] = None, max_repairs: int = 2,
                 slop_repairer: Optional[SlopRepairer] = None, slop_threshold: float = 0.5):
        self.gate = gate
        self.drafter = drafter
        self.repairer = repairer
        self.max_repairs = max_repairs
        self.slop_repairer = slop_repairer
        self.slop_threshold = slop_threshold

    def _deslop(self, intent: dict, span: dict) -> dict:
        """After faithfulness passes, try ONE de-slop rewrite — but SUBORDINATE to faithfulness: the
        rewrite is accepted only if it still passes the fabrication gate AND is less sloppy. Slop
        never overrides truth; a rewrite that reintroduces an unverifiable claim is rejected."""
        from .slop import assess_slop
        if self.slop_repairer is None or not span.get("text"):
            return span
        report = assess_slop(span["text"], self.slop_threshold)
        if not report["is_slop"]:
            return span
        candidate = self.slop_repairer(intent, span, report)
        if not self.gate.run([candidate]).decisions[0].published:
            return span  # de-slop must not break faithfulness → keep the original
        if assess_slop(candidate.get("text", ""), self.slop_threshold)["score"] >= report["score"]:
            return span  # rewrite wasn't actually less sloppy → keep the original
        return candidate

    def generate(self, plan: List[dict]) -> GenResult:
        accepted: List[dict] = []
        dropped: List[dict] = []
        trace: List[GenStep] = []
        for intent in plan:
            span = self.drafter(intent)
            attempts = 0
            while True:
                decision = self.gate.run([span]).decisions[0]
                if decision.published:
                    span = self._deslop(intent, span)  # quality pass, subordinate to faithfulness
                    accepted.append(span)
                    trace.append(GenStep(intent.get("id", "?"), "accepted", attempts, decision.action))
                    break
                if self.repairer is None or attempts >= self.max_repairs:
                    dropped.append(span)
                    trace.append(GenStep(intent.get("id", "?"), "dropped", attempts, decision.action,
                                         reason=decision.driver_reason))
                    break
                # verifier-driven repair: the finding's reason IS the instruction
                span = self.repairer(intent, span, decision)
                attempts += 1
        text = " ".join(s.get("text", "") for s in accepted if s.get("text"))
        return GenResult(text=text, accepted=accepted, dropped=dropped, trace=trace)
