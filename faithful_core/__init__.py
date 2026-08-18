"""faithful-core — a domain-agnostic faithfulness engine: verify AI-generated content against its
source, one tunable Check at a time. The numeric ledger is the first, deterministic Check; semantic
judges (entailment/congruence/slop) join later. A shared verdict-bus (Finding) + a golden-vector
conformance corpus + a small per-use-case manifest. NOT a heavy shared runtime — a light platform.
"""
from .finding import (
    Finding, ContentSpan, Action, Groundedness, Dimension, CheckKind, SurfaceTier,
    PolicyTable, DEFAULT_POLICY, default_policy, surface_policy, compose_decision, is_published,
)
from .manifest import (
    UnitVocab, GateManifest, DEFAULT_VOCAB, DEFAULT_MANIFEST, INDIA_TECH_VOCAB,
    DEFAULT_MAGNITUDES, DEFAULT_CURRENCIES,
)
from .check import Check
from .numeric.check import NumericCheck
from .semantic.entailment import EntailmentCheck, EntailmentJudge, abstaining_judge
from .numeric.audit import build_audit_report, render_audit_markdown
from .harness import run_gate_eval, format_gate_eval, wilson, gold_should_publish

__version__ = "0.1.0"

__all__ = [
    "Finding", "ContentSpan", "Action", "Groundedness", "Dimension", "CheckKind", "SurfaceTier",
    "PolicyTable", "DEFAULT_POLICY", "default_policy", "surface_policy", "compose_decision", "is_published",
    "UnitVocab", "GateManifest", "DEFAULT_VOCAB", "DEFAULT_MANIFEST", "INDIA_TECH_VOCAB",
    "Check", "NumericCheck", "EntailmentCheck", "EntailmentJudge", "abstaining_judge",
    "build_audit_report", "render_audit_markdown",
    "run_gate_eval", "format_gate_eval", "wilson", "gold_should_publish", "__version__",
]
