"""fides.studio — a GROUNDED content layer on top of the verifier. Brainstorm → compose → GROUND →
rank candidate assets (posts / infographic images / videos) from a customer's typed data. Every
number in every asset is a NumericClaim gated by the fides ledger, so assets are grounded BY
CONSTRUCTION (an infographic built from verified facts can't show a number that isn't in the data)
and an LLM-drafted asset has its fabricated numbers dropped/repaired before it ships.

Design (panel): generation is a LAYER, not the core. The ideator (brainstorm) and post composer are
INJECTED callables (an LLM in production; deterministic fallbacks here). The heavy RENDERERS
(spec→PNG via canvas, storyboard→mp4 via ffmpeg) are adapters the consumer supplies — studio produces
the VERIFIED SPEC; turning it into pixels is out of the zero-dep core.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .gate import Gate
from .manifest import GateManifest, DEFAULT_MANIFEST
from .numeric.audit import build_audit_report

Format = str  # 'post' | 'image' | 'video'


@dataclass
class Idea:
    id: str
    format: Format
    angle: str
    rationale: str = ""


@dataclass
class GroundedAsset:
    id: str
    format: Format
    idea: Idea
    spec: dict                       # format-specific presentation (title, stats, scenes, text)
    grounding: float                 # fraction of verifiable spans that passed the gate (1.0 = fully grounded)
    shippable: bool                  # every claim verified → safe to render/publish
    audit: dict                      # per-figure source documentation
    withheld: List[str] = field(default_factory=list)  # span ids the gate dropped/held


# ---- deterministic, grounded-BY-CONSTRUCTION builders (no LLM) -----------------------------------
def select_headline_facts(facts_by_id: dict, k: int = 3) -> list:
    """Pick the k most 'headline' numeric facts — highest extraction confidence, then largest
    magnitude. Deterministic; these become an infographic/video that is grounded by construction."""
    facts = list(facts_by_id.values())
    facts.sort(key=lambda f: (-f.get("confidence", 0.9), -abs(f["quantity"]["canonical"])))
    return facts[:k]


def _stat_span(sid: str, fact: dict, surface: str) -> dict:
    """One verifiable unit: the emitted number IS the source fact → verifies trivially (grounded by
    construction). The Gate confirms it and the audit records the locator."""
    return {"id": sid, "surface": surface,
            "text": "%s: %s" % (fact["entity"]["metric"], fact["quantity"]["raw"]),
            "facts_by_id": {fact["id"]: fact},
            "numeric_claims": [{"emitted": fact["quantity"]["raw"],
                                "binding": {"kind": "source", "factId": fact["id"]},
                                "context": {"surface": surface, "subject": fact["entity"]["subject"], "metric": fact["entity"]["metric"]}}]}


def infographic_draft(facts_by_id: dict, title: str, k: int = 3, surface: str = "marketing") -> dict:
    picks = select_headline_facts(facts_by_id, k)
    spec = {"kind": "infographic", "title": title,
            "stats": [{"value": f["quantity"]["raw"], "label": f["entity"]["metric"]} for f in picks]}
    return {"format": "image", "spec": spec, "spans": [_stat_span("stat%d" % i, f, surface) for i, f in enumerate(picks)]}


def video_draft(facts_by_id: dict, title: str, surface: str = "marketing") -> dict:
    picks = select_headline_facts(facts_by_id, 5)
    scenes = [{"visual": "title", "title": title}] + [{"visual": "stat", "value": f["quantity"]["raw"], "label": f["entity"]["metric"]} for f in picks]
    return {"format": "video", "spec": {"kind": "storyboard", "title": title, "scenes": scenes},
            "spans": [_stat_span("scene%d" % i, f, surface) for i, f in enumerate(picks)]}


def post_draft_deterministic(facts_by_id: dict, title: str, surface: str = "marketing") -> dict:
    picks = select_headline_facts(facts_by_id, 3)
    body = title + " — " + ", ".join("%s %s" % (f["entity"]["metric"], f["quantity"]["raw"]) for f in picks) + "."
    return {"format": "post", "spec": {"kind": "post", "text": body}, "spans": [_stat_span("p%d" % i, f, surface) for i, f in enumerate(picks)]}


# ---- the studio orchestrator --------------------------------------------------------------------
# injected: ideator(facts, formats, n) -> [Idea];  post_composer(idea, facts) -> a draft dict
#           ({format:'post', spec:{kind:'post', text}, spans:[gate spans]}) whose numbers the gate verifies.
Ideator = Callable[[dict, List[Format], int], List[Idea]]
PostComposer = Callable[[Idea, dict], dict]


class ContentStudio:
    def __init__(self, gate: Gate, manifest: GateManifest = DEFAULT_MANIFEST):
        self.gate = gate
        self.manifest = manifest

    def default_ideas(self, formats: List[Format]) -> List[Idea]:
        return [Idea(id="idea-%s" % f, format=f, angle="headline metrics", rationale="lead with the strongest verified figures") for f in formats]

    def compose(self, idea: Idea, facts_by_id: dict, title: str, post_composer: Optional[PostComposer] = None) -> dict:
        if idea.format == "image":
            return infographic_draft(facts_by_id, title)
        if idea.format == "video":
            return video_draft(facts_by_id, title)
        # post: use the injected LLM composer if given, else the deterministic grounded fallback
        return post_composer(idea, facts_by_id) if post_composer else post_draft_deterministic(facts_by_id, title)

    def ground(self, asset_id: str, idea: Idea, draft: dict) -> GroundedAsset:
        spans = draft.get("spans", [])
        rep = self.gate.run(spans)
        withheld = [d.id for d in rep.decisions if not d.published]
        grounding = (len(rep.decisions) - len(withheld)) / len(rep.decisions) if rep.decisions else 1.0
        # audit across every numeric claim in the asset
        claims, facts = [], {}
        for sp in spans:
            claims.extend(sp.get("numeric_claims", []))
            facts.update(sp.get("facts_by_id", {}))
        return GroundedAsset(id=asset_id, format=draft["format"], idea=idea, spec=draft["spec"],
                             grounding=grounding, shippable=(not withheld), withheld=withheld,
                             audit=build_audit_report(claims, facts) if claims else {"summary": {"total": 0}})

    def run(self, facts_by_id: dict, title: str, formats=("post", "image", "video"),
            ideator: Optional[Ideator] = None, post_composer: Optional[PostComposer] = None, n: int = 1) -> List[GroundedAsset]:
        """Brainstorm → compose → GROUND → rank. Returns grounded candidate assets, most-grounded
        first (shippable ones — fully verified — on top)."""
        ideas = ideator(facts_by_id, list(formats), n) if ideator else self.default_ideas(list(formats))
        assets = []
        for i, idea in enumerate(ideas):
            draft = self.compose(idea, facts_by_id, title, post_composer)
            assets.append(self.ground("asset-%d" % i, idea, draft))
        assets.sort(key=lambda a: (a.shippable, a.grounding), reverse=True)
        return assets
