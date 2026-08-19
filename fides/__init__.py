"""fides — a domain-agnostic faithfulness engine: verify AI-generated content against its
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
from .semantic.congruence import CongruenceCheck, CongruenceJudge, abstaining_congruence_judge
from .quality import quality_signals, goodhart_tripwire, HEDGE_LEXICON, leaked_values, value_present_in_prose
from .text import QuoteCheck, verify_span, verify_span_any, normalize_for_span
from .semantic.robust import JudgeCache, make_cached_judge, with_retry, make_chunked_batch_judge, make_multi_lens_judge
from .evidence import OriginScopedEvidence
from .authority import all_proposal_grade
from .slop import assess_slop, slop_score, slop_signals, flag_slop_sentences, SLOP_PHRASES
from .numeric.audit import build_audit_report, render_audit_markdown
from .harness import run_gate_eval, format_gate_eval, wilson, gold_should_publish
from .gate import Gate, GateReport, SpanDecision, format_gate_report
from .studio import ContentStudio, GroundedAsset, Idea, infographic_draft, video_draft, post_draft_deterministic, select_headline_facts
from .render import render_asset, infographic_svg, storyboard_html
from .generate import GroundedGenerator, GenResult, GenStep
from .semantic_eval import run_entailment_eval, format_entailment_eval

__version__ = "0.1.0"

__all__ = [
    "Finding", "ContentSpan", "Action", "Groundedness", "Dimension", "CheckKind", "SurfaceTier",
    "PolicyTable", "DEFAULT_POLICY", "default_policy", "surface_policy", "compose_decision", "is_published",
    "UnitVocab", "GateManifest", "DEFAULT_VOCAB", "DEFAULT_MANIFEST", "INDIA_TECH_VOCAB",
    "Check", "NumericCheck", "EntailmentCheck", "EntailmentJudge", "abstaining_judge",
    "CongruenceCheck", "CongruenceJudge", "abstaining_congruence_judge",
    "quality_signals", "goodhart_tripwire", "HEDGE_LEXICON", "leaked_values", "value_present_in_prose",
    "QuoteCheck", "verify_span", "verify_span_any", "normalize_for_span",
    "JudgeCache", "make_cached_judge", "with_retry", "make_chunked_batch_judge", "make_multi_lens_judge",
    "OriginScopedEvidence", "all_proposal_grade",
    "assess_slop", "slop_score", "slop_signals", "flag_slop_sentences", "SLOP_PHRASES",
    "build_audit_report", "render_audit_markdown",
    "run_gate_eval", "format_gate_eval", "wilson", "gold_should_publish",
    "Gate", "GateReport", "SpanDecision", "format_gate_report",
    "ContentStudio", "GroundedAsset", "Idea", "infographic_draft", "video_draft", "post_draft_deterministic", "select_headline_facts",
    "render_asset", "infographic_svg", "storyboard_html",
    "GroundedGenerator", "GenResult", "GenStep",
    "run_entailment_eval", "format_entailment_eval", "__version__",
]
