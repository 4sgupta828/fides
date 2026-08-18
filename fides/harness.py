"""Precision/recall harness — the 'bake it' engine. A (dimension × surface-tier) matrix scored on the
COMPOSED per-span decision: minimize fabrication-ESCAPE (should-withhold that shipped → 0) subject to
maximizing genuine-RECALL, both with Wilson CIs so a tiny labeled set can't over-certify. Auto-drop
is deterministic-only; llm_judge stays flag-only until data certifies the precision bar."""
from __future__ import annotations
import math
from typing import List, Optional

from .finding import Finding, compose_decision, is_published, PolicyTable

TIERS = ("compliance", "marketing")


def gold_should_publish(truth: str, tier: str) -> bool:
    if truth == "in_corpus":
        return True
    if truth == "true_uncited":
        return tier == "marketing"
    return False  # false / abstain-as-truth never should-publish


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return {"p": 0.0, "lo": 0.0, "hi": 0.0}
    p = k / n; z2 = z * z; denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return {"p": p, "lo": max(0.0, center - half), "hi": min(1.0, center + half)}


def run_gate_eval(spans: List[dict], policy: Optional[PolicyTable] = None) -> dict:
    """`spans` = [{id, dimension, truth, findings:[Finding]}]. truth is SURFACE-INVARIANT."""
    by_dim = {}
    for s in spans:
        by_dim.setdefault(s["dimension"], []).append(s)
    cells = []
    for dim, dim_spans in by_dim.items():
        for tier in TIERS:
            should_withhold = should_publish = escapes = recall_losses = drops = drop_correct = abstains = 0
            for s in dim_spans:
                findings = [_retier(f, tier) for f in s["findings"]]
                action, _ = compose_decision(findings, policy)
                published = is_published(action)
                sp = gold_should_publish(s["truth"], tier)
                if sp:
                    should_publish += 1
                    if not published:
                        recall_losses += 1
                else:
                    should_withhold += 1
                    if published:
                        escapes += 1
                if action == "drop":
                    drops += 1
                    if not sp:
                        drop_correct += 1
                if any(f.groundedness == "abstain" for f in findings):
                    abstains += 1
            cells.append({
                "dimension": dim, "tier": tier, "n": len(dim_spans),
                "should_withhold": should_withhold, "should_publish": should_publish,
                "escapes": escapes, "escape_rate": wilson(escapes, should_withhold),
                "recall_losses": recall_losses,
                "genuine_recall": wilson(should_publish - recall_losses, should_publish),
                "drops": drops, "drop_precision": wilson(drop_correct, drops),
                "abstain_rate": abstains / len(dim_spans) if dim_spans else 0.0,
            })
    return {"cells": cells, "max_escapes": max([0] + [c["escapes"] for c in cells]),
            "total_spans": len(spans)}


def _retier(f: Finding, tier: str) -> Finding:
    from dataclasses import replace
    from .finding import ContentSpan
    return replace(f, span=ContentSpan(text=f.span.text, surface=tier, start=f.span.start, end=f.span.end))


def format_gate_eval(r: dict) -> str:
    L = ["Publishing-Gate eval — %d spans, max escapes in any cell: %d %s" %
         (r["total_spans"], r["max_escapes"], "⚠" if r["max_escapes"] else "✓")]
    L.append("  dimension × tier          escape(95%% hi)   recall(95%% lo)   drops abstain")
    for c in r["cells"]:
        esc = "%d/%d (%.0f%%)" % (c["escapes"], c["should_withhold"], c["escape_rate"]["hi"] * 100)
        rec = "%d/%d (%.0f%%)" % (c["should_publish"] - c["recall_losses"], c["should_publish"], c["genuine_recall"]["lo"] * 100)
        L.append("  %-24s %-16s %-16s %-5d %.0f%%" % (c["dimension"] + " × " + c["tier"], esc, rec, c["drops"], c["abstain_rate"] * 100))
    return "\n".join(L)
