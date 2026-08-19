"""fides.studio — grounded content generation. Deterministic assets are grounded BY CONSTRUCTION
(built from verified facts); an LLM-drafted asset has fabricated numbers dropped before it ships."""
import unittest
from fides import ContentStudio, Gate, NumericCheck
from fides.numeric import ledger

FACTS = {f["id"]: f for f in [
    ledger.materialize_fact({"id": "ret", "value": "12.4%", "subject": "Apex", "metric": "net return", "period": "FY2024", "locatorText": "Apex returned 12.4% net in FY2024."}),
    ledger.materialize_fact({"id": "aum", "value": "$1.2B", "subject": "Apex", "metric": "AUM", "period": "FY2024", "locatorText": "AUM reached $1.2B."}),
    ledger.materialize_fact({"id": "exp", "value": "65 bps", "subject": "Apex", "metric": "expense ratio", "locatorText": "Expense ratio is 65 bps."}),
]}


class Studio(unittest.TestCase):
    def setUp(self):
        self.studio = ContentStudio(Gate(checks=[NumericCheck()]))

    def test_brainstorms_all_formats_grounded_by_construction(self):
        assets = self.studio.run(FACTS, "Apex FY2024", formats=("post", "image", "video"))
        self.assertEqual({a.format for a in assets}, {"post", "image", "video"})
        for a in assets:
            self.assertTrue(a.shippable, a.format)            # every number is a real fact → all verify
            self.assertEqual(a.grounding, 1.0)

    def test_infographic_spec_stats_from_headline_facts(self):
        img = next(a for a in self.studio.run(FACTS, "Apex", formats=("image",)) if a.format == "image")
        self.assertEqual(img.spec["kind"], "infographic")
        labels = [s["label"] for s in img.spec["stats"]]
        self.assertIn("net return", labels)
        self.assertIn("AUM", labels)

    def test_video_spec_is_a_storyboard(self):
        vid = self.studio.run(FACTS, "Apex", formats=("video",))[0]
        self.assertEqual(vid.spec["kind"], "storyboard")
        self.assertEqual(vid.spec["scenes"][0]["visual"], "title")
        self.assertTrue(any(s["visual"] == "stat" for s in vid.spec["scenes"]))

    def test_audit_covers_every_figure(self):
        img = self.studio.run(FACTS, "Apex", formats=("image",))[0]
        self.assertEqual(img.audit["summary"]["verified"], img.audit["summary"]["total"])
        self.assertGreater(img.audit["summary"]["total"], 0)

    def test_llm_drafted_fabrication_is_dropped_not_shipped(self):
        # an injected post composer that fabricates a peer stat → the gate drops it, asset not shippable
        def fab_composer(idea, facts):
            return {"format": "post", "spec": {"kind": "post", "text": "Peers returned 30%."},
                    "spans": [{"id": "p0", "surface": "marketing", "text": "Peers returned 30%.", "facts_by_id": facts,
                               "numeric_claims": [{"emitted": "30%", "binding": {"kind": "unbound"}, "context": {"surface": "marketing"}}]}]}
        asset = self.studio.run(FACTS, "Apex", formats=("post",), post_composer=fab_composer)[0]
        self.assertFalse(asset.shippable)                    # fabricated number → not shippable
        self.assertIn("p0", asset.withheld)
        self.assertLess(asset.grounding, 1.0)

    def test_run_ranks_shippable_first(self):
        # one clean image (shippable) + one fabricated post (not) → shippable ranks first
        def fab_composer(idea, facts):
            return {"format": "post", "spec": {"kind": "post", "text": "made up 99%"}, "spans": [
                {"id": "x", "surface": "marketing", "text": "made up 99%", "facts_by_id": facts,
                 "numeric_claims": [{"emitted": "99%", "binding": {"kind": "unbound"}, "context": {"surface": "marketing"}}]}]}
        assets = self.studio.run(FACTS, "Apex", formats=("post", "image"), post_composer=fab_composer)
        self.assertTrue(assets[0].shippable)                 # the grounded image sorts to the top
        self.assertFalse(assets[-1].shippable)


if __name__ == "__main__":
    unittest.main()
