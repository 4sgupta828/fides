"""The shared verdict currency for every check — the ~1 file that makes this a platform.

A Finding is span-anchored, dimension-typed, deterministic-vs-judge, with a SURFACE-INVARIANT
groundedness. The compliance/creative difference is a PURE POLICY on top (a table), never baked into
a check. One immovable invariant (panel): a deterministic `false` — a proven fabrication — ALWAYS
drops; no dial can override it. Style is NOT a faithfulness axis and never appears here.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# --- the typed vocabulary of a verdict --------------------------------------------------------
Dimension = str      # 'numeric' | 'quote' | 'entailment' | 'attribution' | 'overgeneralization' | 'misinterpretation' | 'slop'
CheckKind = str      # 'deterministic' | 'llm_judge'
Groundedness = str   # 'in_corpus' | 'true_uncited' | 'false' | 'abstain'
SurfaceTier = str    # 'compliance' | 'marketing'  (extensible)
Severity = str       # 'low' | 'medium' | 'high' | 'critical'
Action = str         # 'keep' | 'flag' | 'downgrade' | 'hold' | 'drop'

GROUNDEDNESS = ("in_corpus", "true_uncited", "false", "abstain")
ACTIONS = ("keep", "flag", "downgrade", "hold", "drop")
_ACTION_RANK = {"keep": 0, "flag": 1, "downgrade": 2, "hold": 3, "drop": 4}


@dataclass(frozen=True)
class ContentSpan:
    """A span in the GENERATED content (not the source) — the thing prior gates lacked."""
    text: str
    surface: SurfaceTier = "compliance"
    start: Optional[int] = None
    end: Optional[int] = None


@dataclass(frozen=True)
class Finding:
    check_id: str
    dimension: Dimension
    kind: CheckKind
    span: ContentSpan
    groundedness: Groundedness
    severity: Severity = "low"
    confidence: Optional[float] = None  # 0..1 for llm_judge; deterministic omit/1.0
    reason: str = ""
    source_locators: Tuple[str, ...] = ()


# --- the policy TABLE (panel upgrade: not a 2-value enum) --------------------------------------
# Resolves (tier, groundedness, kind) -> action. Grounding-strictness is dial-able by editing the
# table; the fabrication invariant below is NOT in the table and cannot be dialed.
PolicyTable = Dict[Tuple[SurfaceTier, Groundedness, CheckKind], Action]


def default_policy() -> PolicyTable:
    t: PolicyTable = {}
    for kind in ("deterministic", "llm_judge"):
        # compliance = corpus-only. non-in_corpus is withheld; a judge suspicion HOLDS for review.
        t[("compliance", "in_corpus", kind)] = "keep"
        t[("compliance", "true_uncited", kind)] = "drop" if kind == "deterministic" else "hold"
        t[("compliance", "false", kind)] = "drop" if kind == "deterministic" else "hold"
        t[("compliance", "abstain", kind)] = "hold"
        # marketing = keep sound general knowledge; drop only PROVEN fabrication; flag judge suspicion.
        t[("marketing", "in_corpus", kind)] = "keep"
        t[("marketing", "true_uncited", kind)] = "keep"
        t[("marketing", "false", kind)] = "drop" if kind == "deterministic" else "flag"
        t[("marketing", "abstain", kind)] = "flag"
    return t


DEFAULT_POLICY = default_policy()


def surface_policy(f: Finding, policy: Optional[PolicyTable] = None) -> Action:
    """Resolve a finding to an action. IMMOVABLE INVARIANT first: a deterministic `false` is a proven
    fabrication and ALWAYS drops — no policy table entry can override it (the line between creative
    and lying)."""
    if f.kind == "deterministic" and f.groundedness == "false":
        return "drop"
    table = policy if policy is not None else DEFAULT_POLICY
    return table.get((f.span.surface, f.groundedness, f.kind), "keep")


def compose_decision(findings: List[Finding], policy: Optional[PolicyTable] = None):
    """Compose ALL findings on a span into one decision — most-restrictive wins (the metric lives on
    the composed decision, never per-check). Returns (action, driver)."""
    if not findings:
        return "keep", None
    best = None
    for f in findings:
        a = surface_policy(f, policy)
        if best is None or _ACTION_RANK[a] > _ACTION_RANK[best[0]]:
            best = (a, f)
    return best


def is_published(action: Action) -> bool:
    """keep/flag/downgrade ship (flag ships with a note); hold/drop do not."""
    return action in ("keep", "flag", "downgrade")
