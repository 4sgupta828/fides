"""Anti-slop, done the panel's way: quality TRIPWIRES, not a fabrication verdict. Slop/usefulness is
NOT a groundedness axis — forcing it into drop-Findings would let the gate reach into style (a bug).
Instead these are cheap, deterministic signals you WATCH (never optimize): if a repair/generation
loop lowers fabrication-escape while grounded-info density drops AND hedge-rate rises, the model is
Goodharting toward vague, extractive, evasive output — worse than the fabrication you removed.
"""
from __future__ import annotations
import re
from typing import List

# a small CLOSED hedge lexicon (structural, not semantic — Rule 18 stays intact)
HEDGE_LEXICON = (
    "may", "might", "could", "reportedly", "arguably", "possibly", "perhaps", "seemingly",
    "some experts", "some say", "many believe", "it seems", "it appears", "is thought to",
    "is believed to", "allegedly", "presumably", "roughly", "sort of", "kind of",
)
_VALUE_RE = re.compile(r"(?:\$\s?\d[\d,]*(?:\.\d+)?\s?(?:[kmbt]n?|million|billion|trillion)?)|(?:\b\d[\d,]*(?:\.\d+)?\s?%)|(?:\b\d[\d,]*(?:\.\d+)?\s?bps\b)|(?:\b\d+(?:\.\d+)?x\b)", re.I)
_SENT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"\b\w+\b")


def quality_signals(text: str) -> dict:
    words = _WORD_RE.findall(text)
    wc = len(words)
    sentences = [s for s in _SENT_RE.split(text.strip()) if s.strip()]
    sc = len(sentences) or 1
    value_tokens = _VALUE_RE.findall(text)
    low = text.lower()
    hedged = sum(1 for s in sentences if any(h in s.lower() for h in HEDGE_LEXICON))
    return {
        "word_count": wc,
        "sentence_count": len(sentences),
        "value_token_count": len(value_tokens),
        # concrete verifiable claims per 100 words — falls when the model gets evasive/extractive
        "value_density_per_100w": (len(value_tokens) / wc * 100) if wc else 0.0,
        "hedge_sentence_rate": hedged / sc,
    }


def goodhart_tripwire(before: dict, after: dict, escape_improved: bool) -> dict:
    """The paired tripwire: fabrication went down BUT the text got vaguer (less concrete info) AND
    more hedged. That combination means the loop is dodging the gate, not improving faithfulness."""
    density_dropped = after["value_density_per_100w"] < before["value_density_per_100w"]
    hedge_rose = after["hedge_sentence_rate"] > before["hedge_sentence_rate"]
    triggered = bool(escape_improved and density_dropped and hedge_rose)
    return {
        "triggered": triggered,
        "escape_improved": escape_improved,
        "density_dropped": density_dropped,
        "hedge_rose": hedge_rose,
        "reason": ("escape improved but content got vaguer and more hedged — Goodhart risk"
                   if triggered else "no Goodhart pattern"),
    }
