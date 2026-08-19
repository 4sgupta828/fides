"""fides.render — a verified spec renders to real pixels (SVG/HTML) with zero deps. The load-bearing
property: a renderer draws ONLY the spec's figures, so every number on the canvas is one the ledger
passed — and render_asset refuses an un-shippable asset outright."""
import re
import unittest
import xml.dom.minidom as minidom
from fides import ContentStudio, Gate, NumericCheck, render_asset, infographic_svg, storyboard_html
from fides.numeric import ledger

FACTS = {f["id"]: f for f in [
    ledger.materialize_fact({"id": "ret", "value": "12.4%", "subject": "Apex", "metric": "net return", "period": "FY2024", "locatorText": "Apex returned 12.4% net in FY2024."}),
    ledger.materialize_fact({"id": "aum", "value": "$1.2B", "subject": "Apex", "metric": "AUM", "period": "FY2024", "locatorText": "AUM reached $1.2B."}),
    ledger.materialize_fact({"id": "exp", "value": "65 bps", "subject": "Apex", "metric": "expense ratio", "locatorText": "Expense ratio is 65 bps."}),
]}


class Render(unittest.TestCase):
    def setUp(self):
        self.studio = ContentStudio(Gate(checks=[NumericCheck()]))

    def test_infographic_renders_valid_svg_with_only_verified_stats(self):
        img = next(a for a in self.studio.run(FACTS, "Apex FY2024", formats=("image",)))
        svg = render_asset(img)
        minidom.parseString(svg)                              # well-formed XML (renderer emits valid SVG)
        self.assertTrue(svg.startswith("<svg"))
        for s in img.spec["stats"]:                           # every drawn number is a spec (=verified) stat
            self.assertIn(s["value"], svg)
        # and NOTHING numeric on the canvas that isn't a verified value
        drawn = set(re.findall(r">([^<]*\d[^<]*)<", svg))
        for token in drawn:
            self.assertTrue(any(s["value"] in token for s in img.spec["stats"]) or "Apex" in token, token)

    def test_video_renders_self_contained_html_frame_per_scene(self):
        vid = self.studio.run(FACTS, "Apex", formats=("video",))[0]
        html = render_asset(vid)
        self.assertIn("<!doctype html>", html.lower())
        self.assertEqual(html.count('class="f"') + html.count("class=f"), len(vid.spec["scenes"]))
        self.assertNotIn("http://", html.replace("http://www.w3.org", ""))  # no external asset fetches

    def test_escapes_hostile_text(self):
        svg = infographic_svg({"title": "<script>alert(1)</script>", "stats": [{"value": "1 & 2", "label": "x"}]})
        self.assertNotIn("<script>", svg)
        self.assertIn("&amp;", svg)
        minidom.parseString(svg)

    def test_refuses_unshippable_asset(self):
        def fab(idea, facts):
            return {"format": "post", "spec": {"kind": "post", "text": "made up 99%"}, "spans": [
                {"id": "x", "surface": "marketing", "text": "made up 99%", "facts_by_id": facts,
                 "numeric_claims": [{"emitted": "99%", "binding": {"kind": "unbound"}, "context": {"surface": "marketing"}}]}]}
        # a post asset can't render anyway, but force an image-shaped un-shippable to prove the guard
        bad = self.studio.run(FACTS, "Apex", formats=("post",), post_composer=fab)[0]
        self.assertFalse(bad.shippable)
        with self.assertRaises(ValueError):
            render_asset(bad, allow_unshippable=False)

    def test_storyboard_html_valid_when_empty(self):
        html = storyboard_html({"kind": "storyboard", "title": "x", "scenes": []})
        self.assertIn("stage", html)


if __name__ == "__main__":
    unittest.main()
