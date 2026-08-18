"""Deterministic TEXT grounding — the no-fabrication span gate (LLM-free), absorbed from factra."""
from .span import normalize_for_span, verify_span, verify_span_any
from .quote_check import QuoteCheck
