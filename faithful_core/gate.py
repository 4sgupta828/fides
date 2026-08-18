"""The Gate — the single publishing verdict that Noesis/Eigen lack (their checks are flag-gated and
diffused across the loop). Runs the registry of enabled Checks over each span, composes ONE decision
per span (most-restrictive across all findings, all dimensions), and returns a unified GateReport:
what ships, what's withheld and why, plus the quality tripwire. One call, one verdict, one audit.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from .finding import Finding, compose_decision, is_published, Action
from .manifest import GateManifest, DEFAULT_MANIFEST
from .quality import quality_signals


@dataclass
class SpanDecision:
    id: str
    surface: str
    action: Action
    published: bool
    driver_dimension: Optional[str]
    driver_reason: str
    findings: List[Finding]


@dataclass
class GateReport:
    decisions: List[SpanDecision]
    summary: dict
    quality: dict = field(default_factory=dict)


class Gate:
    """A registry of checks + a manifest. `checks` may mix deterministic (numeric) and llm_judge
    (entailment/congruence) — the Gate routes each span's inputs to the checks that apply."""

    def __init__(self, checks: list, manifest: GateManifest = DEFAULT_MANIFEST):
        self.checks = checks
        self.manifest = manifest

    def _run_check(self, chk, span: dict, surface: str) -> List[Finding]:
        if getattr(chk, "dimension", "") == "numeric":
            claims = span.get("numeric_claims", [])
            if not claims:
                return []
            evidence = {"facts_by_id": span.get("facts_by_id", {}), "surface": surface,
                        "rounding": span.get("rounding", True)}
            return chk.run(claims, evidence, self.manifest)
        # semantic checks operate on the span's text + its cited evidence
        text = span.get("text")
        if not text:
            return []
        claims = [{"text": text, "evidence_texts": span.get("evidence_texts", []),
                   "source_locators": span.get("source_locators", [])}]
        return chk.run(claims, {"surface": surface}, self.manifest)

    def run(self, spans: List[dict]) -> GateReport:
        decisions: List[SpanDecision] = []
        by_action = {}
        for span in spans:
            surface = span.get("surface", "compliance")
            findings: List[Finding] = []
            for chk in self.checks:
                if getattr(chk, "dimension", None) and chk.dimension not in self.manifest.enabled_dimensions:
                    # a check may emit multiple dimensions; run it unless ALL its dims are disabled
                    pass
                findings.extend(self._run_check(chk, span, surface))
            action, driver = compose_decision(findings, self.manifest.policy)
            by_action[action] = by_action.get(action, 0) + 1
            decisions.append(SpanDecision(
                id=span.get("id", "?"), surface=surface, action=action, published=is_published(action),
                driver_dimension=(driver.dimension if driver else None),
                driver_reason=(driver.reason if driver else ""), findings=findings,
            ))
        published = sum(1 for d in decisions if d.published)
        # quality tripwire over the full published text (anti-slop, watched not optimized)
        pub_text = " ".join(s.get("text", "") for s, d in zip(spans, decisions) if d.published and s.get("text"))
        return GateReport(
            decisions=decisions,
            summary={"total": len(decisions), "published": published,
                     "withheld": len(decisions) - published, "by_action": by_action},
            quality=quality_signals(pub_text) if pub_text else {},
        )


def format_gate_report(r: GateReport) -> str:
    s = r.summary
    L = ["Gate verdict — %d/%d spans published, %d withheld  %s" %
         (s["published"], s["total"], s["withheld"], dict(s["by_action"]))]
    for d in r.decisions:
        mark = "✓" if d.published else "✗"
        why = "" if d.published else "  (%s: %s)" % (d.driver_dimension or "?", d.driver_reason)
        L.append("  %s [%s] %s%s" % (mark, d.action, d.id, why))
    return "\n".join(L)
