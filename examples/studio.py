"""fides.studio — brainstorm grounded posts / infographics / videos from a customer's data. Every
number is verified against the source by the fides ledger, so assets are grounded by construction
(no slop, no fabricated stats). Run: python3 examples/studio.py  (no key needed.)"""
import os
from fides import ContentStudio, Gate, NumericCheck, render_audit_markdown, render_asset
from fides.numeric import ledger

# Customer data → typed Fact cells (what an extractor would produce from a fund factsheet).
FACTS = {f["id"]: f for f in [
    ledger.materialize_fact({"id": "ret", "value": "12.4%", "subject": "Apex Growth", "metric": "net return", "period": "FY2024", "locatorText": "Apex Growth returned 12.4% net of fees in FY2024."}),
    ledger.materialize_fact({"id": "aum", "value": "$1.2B", "subject": "Apex Growth", "metric": "AUM", "period": "FY2024", "locatorText": "AUM reached $1.2B by year-end 2024."}),
    ledger.materialize_fact({"id": "exp", "value": "65 bps", "subject": "Apex Growth", "metric": "expense ratio", "locatorText": "The fund's expense ratio is 65 bps."}),
    ledger.materialize_fact({"id": "bmk", "value": "9.8%", "subject": "benchmark", "metric": "return", "period": "FY2024", "locatorText": "The benchmark returned 9.8%."}),
]}

studio = ContentStudio(Gate(checks=[NumericCheck()]))
assets = studio.run(FACTS, "Apex Growth — FY2024", formats=("post", "image", "video"))

print("=== Brainstormed, GROUNDED candidate assets (every number verified against the data) ===\n")
for a in assets:
    tag = "SHIPPABLE" if a.shippable else "NEEDS REVIEW (%d withheld)" % len(a.withheld)
    print("[%s]  grounding=%.0f%%  %s" % (a.format.upper(), a.grounding * 100, tag))
    if a.format == "image":
        print("   infographic '%s': %s" % (a.spec["title"], " | ".join("%s %s" % (s["label"], s["value"]) for s in a.spec["stats"])))
    elif a.format == "video":
        print("   storyboard: " + " -> ".join(sc.get("title") or ("%s %s" % (sc["label"], sc["value"])) for sc in a.spec["scenes"]))
    else:
        print("   post: " + a.spec["text"])
    print()

# Render the grounded specs to REAL, openable files (zero deps: SVG is text, video is a self-contained
# HTML player). The renderer draws only the verified spec, so grounding survives to pixels.
out = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(out, exist_ok=True)
for a in assets:
    if a.format == "image":
        open(os.path.join(out, "infographic.svg"), "w").write(render_asset(a))
    elif a.format == "video":
        open(os.path.join(out, "storyboard.html"), "w").write(render_asset(a))
print("--- rendered grounded pixels ---")
print("   %s/infographic.svg   (open in any browser)" % out)
print("   %s/storyboard.html    (plays the verified stats as timed frames)\n" % out)

# The audit that ships with the infographic — its "source documentation for figures".
img = next(a for a in assets if a.format == "image")
print("--- audit for the infographic (source documentation) ---")
print(render_audit_markdown(img.audit, title=img.spec["title"], stamped_at="2026-08-19"))

# And the anti-slop guarantee: an LLM composer that fabricates a stat has it DROPPED before ship.
print("\n=== A fabricated draft is caught, not shipped ===")
def fab_composer(idea, facts):
    return {"format": "post", "spec": {"kind": "post", "text": "Apex is the #1 fund with 40% returns!"},
            "spans": [{"id": "p0", "surface": "marketing", "text": "Apex is the #1 fund with 40% returns!", "facts_by_id": facts,
                       "numeric_claims": [{"emitted": "40%", "binding": {"kind": "unbound"}, "context": {"surface": "marketing"}}]}]}
bad = studio.run(FACTS, "Apex", formats=("post",), post_composer=fab_composer)[0]
print(f"  draft: 'Apex is the #1 fund with 40% returns!'  ->  shippable={bad.shippable}, withheld={bad.withheld} (fabricated 40% dropped)")
