"""Anti-slop — a SEPARATE quality track, never the fabrication gate. Panel discipline: slop is a
USEFULNESS axis, not a truth axis; a sloppy sentence is not a lie, and the faithfulness verifier
must never reach into style. So slop is measured here as an advisory score + per-sentence flags that
feed the GENERATION repair loop (rewrite the filler concrete) — it never drops content as a
fabrication, and a de-slopped rewrite must still pass the fabrication gate.

Deterministic signals (structural, Rule-18-safe): AI-cliché/filler phrases, empty (no-concrete-
content) sentences, hedge rate, low grounded-info density. A novel-slop LLM judge is optional and
injected (adapters/openai_judge.py:make_openai_slop_judge)."""
from __future__ import annotations
import re

from .quality import quality_signals, HEDGE_LEXICON

# Curated AI/LLM tells + generic filler. A SIGNAL, not a ban: some words are legitimate in context,
# so this drives soft scoring + targeted rewrite, never a hard fabrication drop.
SLOP_PHRASES = (
    "delve into", "dive into", "in today's", "fast-paced world", "ever-evolving", "ever-changing",
    "it's important to note", "it is important to note", "it's worth noting", "it is worth noting",
    "when it comes to", "a testament to", "plays a crucial role", "plays a vital role",
    "plays a significant role", "plays a key role", "the world of", "the realm of", "in the realm of",
    "navigate the", "navigating the", "tapestry", "unlock the", "unleash", "harness the power",
    "game-changer", "game changer", "cutting-edge", "state-of-the-art", "paradigm shift",
    "landscape of", "a myriad of", "cannot be overstated", "look no further", "embark on",
    "elevate your", "to the next level", "in this article", "in this blog", "let's explore",
    "the bottom line", "first and foremost", "needless to say", "it goes without saying",
    "at the end of the day", "in conclusion", "in summary", "rich tapestry", "underscores the importance",
)

_SENT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z']+")


def _is_concrete(sentence: str) -> bool:
    """A sentence carries substance if it has a number OR a mid-sentence proper noun (a specific
    entity) — throat-clearing like 'It is important to consider the implications' has neither."""
    if re.search(r"\d", sentence):
        return True
    words = _WORD_RE.findall(sentence)
    return any(w[0].isupper() for w in words[1:])  # exclude the sentence-initial capital


def slop_signals(text: str) -> dict:
    q = quality_signals(text)
    sentences = [s for s in _SENT_RE.split(text.strip()) if s.strip()]
    sc = len(sentences) or 1
    cliche_sentences = sum(1 for s in sentences if any(p in s.lower() for p in SLOP_PHRASES))
    empty = sum(1 for s in sentences if not _is_concrete(s))
    return {**q, "cliche_hits": sum(text.lower().count(p) for p in SLOP_PHRASES),
            "cliche_sentence_rate": cliche_sentences / sc, "empty_sentence_rate": empty / sc}


def slop_score(text: str) -> float:
    """0..1, higher = more slop. Deterministic, soft, monotone: clichés + empty sentences + hedging
    push it up; concrete grounded info pulls it down."""
    s = slop_signals(text)
    if s["word_count"] == 0:
        return 0.0
    score = (0.45 * min(1.0, s["cliche_sentence_rate"])
             + 0.30 * s["empty_sentence_rate"]
             + 0.15 * min(1.0, s["hedge_sentence_rate"])
             + 0.10 * (1.0 - min(1.0, s["value_density_per_100w"] / 5.0)))
    return round(min(1.0, score), 3)


def flag_slop_sentences(text: str) -> list:
    """Per-sentence flags with reasons — the targeted-repair signal for the generation loop."""
    out = []
    for s in (x.strip() for x in _SENT_RE.split(text.strip()) if x.strip()):
        low = s.lower()
        reasons = []
        hits = [p for p in SLOP_PHRASES if p in low]
        if hits:
            reasons.append("cliché/filler: " + ", ".join(hits[:3]))
        if not _is_concrete(s):
            reasons.append("no concrete/verifiable content")
        if any(h in low for h in HEDGE_LEXICON):
            reasons.append("hedged")
        if reasons:
            out.append({"sentence": s, "reasons": reasons})
    return out


def assess_slop(text: str, threshold: float = 0.5) -> dict:
    """Advisory slop report — a QUALITY signal, separate from the faithfulness verdict."""
    score = slop_score(text)
    return {"score": score, "is_slop": score >= threshold, "flags": flag_slop_sentences(text)}
