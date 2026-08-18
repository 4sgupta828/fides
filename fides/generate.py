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


class GroundedGenerator:
    def __init__(self, gate: Gate, drafter: Drafter, repairer: Optional[Repairer] = None, max_repairs: int = 2):
        self.gate = gate
        self.drafter = drafter
        self.repairer = repairer
        self.max_repairs = max_repairs

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
