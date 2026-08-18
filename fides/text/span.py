"""Three-tier fuzzy span verification — a deterministic, LLM-free no-fabrication gate. Absorbed from
factra's production matcher (domain/span_verification.py + verify.py:_norm_ws), whose scars we keep:
sha256/exact-only was "brittle to whitespace normalization bumps", so we normalize typography +
whitespace, then fall back to windowed difflib, then to a longest-contiguous rebind. Passage capped
to bound the O(n²) fuzzy path. Pure stdlib (difflib)."""
from __future__ import annotations
import difflib
import re
import unicodedata

_MAX_PASSAGE = 500_000  # bound the fuzzy cost (factra: 500KB cap)
_MIN_SPAN = 12          # a very short span matches too much → fail closed


def normalize_for_span(s: str) -> str:
    """NFKC + fold smart quotes/dashes/ellipsis + collapse whitespace + lowercase. Absorbs the
    typographic drift a model silently introduces into a quote (curly quotes, en/em dashes)."""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[‘’‛′]", "'", s)      # ' ' ‛ ′
    s = re.sub(r"[“”‟″]", '"', s)      # " " ‟ ″
    s = re.sub(r"[‐‑‒–—―]", "-", s)  # hyphen/dashes
    s = s.replace("…", "...")
    return re.sub(r"\s+", " ", s).strip().lower()


def verify_span(passage: str, span: str, threshold: float = 0.95, rebind: float = 0.70) -> dict:
    """Tier 1 exact substring → Tier 2 windowed difflib ratio ≥ threshold → Tier 3 longest contiguous
    match ≥ rebind fraction of the span. Returns {verified, method}."""
    p = normalize_for_span(passage)[:_MAX_PASSAGE]
    s = normalize_for_span(span)
    if len(s) < _MIN_SPAN:
        return {"verified": False, "method": "too_short"}
    if s in p:
        return {"verified": True, "method": "exact"}
    # Tier 3 (cheap, do first): longest contiguous block covers ≥ rebind of the span.
    sm = difflib.SequenceMatcher(None, s, p, autojunk=False)
    m = sm.find_longest_match(0, len(s), 0, len(p))
    if m.size >= rebind * len(s):
        return {"verified": True, "method": "rebind"}
    # Tier 2: windowed ratio — slide a span-sized window over the passage.
    w = max(len(s), int(len(s) * 1.2))
    step = max(1, len(s) // 4)
    for i in range(0, max(1, len(p) - w + 1), step):
        if difflib.SequenceMatcher(None, s, p[i:i + w], autojunk=False).ratio() >= threshold:
            return {"verified": True, "method": "fuzzy"}
    return {"verified": False, "method": "absent"}


def verify_span_any(passages, span: str, **kw) -> dict:
    """Span must be present in at least one CITED passage — never the corpus at large (that both
    false-passes and reopens the cross-tenant hole; factra verify.py:66-67)."""
    worst = "absent"
    for p in passages:
        r = verify_span(p, span, **kw)
        if r["verified"]:
            return r
        if r["method"] == "too_short":
            worst = "too_short"
    return {"verified": False, "method": worst}
