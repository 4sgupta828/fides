"""The SMALL verifier manifest — copy Noesis's discipline (frozen typed slots), NOT its 65-slot
Q&A-product object. This is the per-use-case tuning surface: the domain supplies *vocabulary and
policy as data*; the kernel calculus stays domain-free.

Medical tunes `mg/mL/IU/mcg`; deep-tech tunes `nm/GHz/W/$/bps` + `crore/lakh`; marketing tunes a
looser policy table. The mechanism is identical — that's the whole platform bet.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional

from .finding import PolicyTable, DEFAULT_POLICY


@dataclass(frozen=True)
class UnitVocab:
    """Domain-tunable numeric vocabulary. The calculus (parse→canonicalize→compare→recompute) is
    fixed; only these tables vary by domain."""
    magnitudes: Dict[str, float]   # word/suffix -> factor ("bn"->1e9, "crore"->1e7)
    currencies: Dict[str, str]     # symbol or code -> ISO code ("$"->"USD", "₹"->"INR")


DEFAULT_MAGNITUDES = {
    "k": 1e3, "thousand": 1e3, "m": 1e6, "mm": 1e6, "mn": 1e6, "million": 1e6,
    "b": 1e9, "bn": 1e9, "billion": 1e9, "t": 1e12, "tn": 1e12, "trillion": 1e12,
}
DEFAULT_CURRENCIES = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR"}
DEFAULT_VOCAB = UnitVocab(magnitudes=dict(DEFAULT_MAGNITUDES), currencies=dict(DEFAULT_CURRENCIES))

# A deep-tech / India-aware example vocab (proves domain tuning threads through on day one).
INDIA_TECH_VOCAB = UnitVocab(
    magnitudes={**DEFAULT_MAGNITUDES, "lakh": 1e5, "crore": 1e7},
    currencies=dict(DEFAULT_CURRENCIES),
)


@dataclass(frozen=True)
class GateManifest:
    """Everything a use case tunes about verification — and nothing about the answer/UI/persona."""
    unit_vocab: UnitVocab = DEFAULT_VOCAB
    policy: PolicyTable = field(default_factory=lambda: dict(DEFAULT_POLICY))
    min_confidence: float = 0.0
    strict_surfaces: FrozenSet[str] = frozenset({"compliance"})          # unresolved ENTITY → fail
    require_period_surfaces: FrozenSet[str] = frozenset()                 # unresolved PERIOD → fail (opt-in)
    verbatim_surfaces: FrozenSet[str] = frozenset()                      # number must match source VERBATIM (table cells)
    proposal_source_classes: FrozenSet[str] = frozenset()               # authority floor: which source classes are proposal-grade
    slop_threshold: float = 0.5                                          # advisory quality bar (SEPARATE from faithfulness)
    enabled_dimensions: FrozenSet[str] = frozenset(
        {"numeric", "quote", "entailment", "attribution", "overgeneralization", "misinterpretation"}
    )
    # future slots (named, not built): judge_directives, source_eligibility, period_grammar, eval_gold


DEFAULT_MANIFEST = GateManifest()
